/**
 * useVoicePipeline — manages WebSocket connection, MediaRecorder,
 * and the full turn lifecycle with the Samvaad-Setu backend.
 */
import { useState, useRef, useCallback, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE  = import.meta.env.VITE_WS_BASE  || 'ws://localhost:8000'

export const PIPELINE_STATES = {
  IDLE:         'idle',
  CONNECTING:   'connecting',
  READY:        'ready',
  RECORDING:    'recording',
  PROCESSING:   'processing',
  VERIFYING:    'verifying',
  ESCALATED:    'escalated',
  ERROR:        'error',
}

export function useVoicePipeline() {
  const [state, setState] = useState(PIPELINE_STATES.IDLE)
  const [sessionId, setSessionId] = useState(null)
  const [turns, setTurns] = useState([])
  const [sessionMeta, setSessionMeta] = useState(null)
  const [escalationPacket, setEscalationPacket] = useState(null)
  const [lastNlu, setLastNlu] = useState(null)
  const [error, setError] = useState(null)
  const [isMockMode, setIsMockMode] = useState(false)

  const wsRef       = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef   = useRef([])

  // ── Session init ─────────────────────────────────────────────────────────
  const startSession = useCallback(async ({ district = 'default', language = 'kn' } = {}) => {
    setState(PIPELINE_STATES.CONNECTING)
    setError(null)
    setTurns([])
    setEscalationPacket(null)

    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ district, language }),
      })
      if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`)
      const { session_id } = await res.json()
      setSessionId(session_id)

      const ws = new WebSocket(`${WS_BASE}/ws/${session_id}`)
      wsRef.current = ws

      ws.onopen = () => {
        setState(PIPELINE_STATES.READY)
        // Keepalive ping every 20s
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
          else clearInterval(pingInterval)
        }, 20000)
      }

      ws.onmessage = (event) => _handleMessage(JSON.parse(event.data))

      ws.onerror = (e) => {
        setError('WebSocket error. Is the backend running?')
        setState(PIPELINE_STATES.ERROR)
      }

      ws.onclose = () => {
        if (state !== PIPELINE_STATES.ESCALATED) setState(PIPELINE_STATES.IDLE)
      }

    } catch (e) {
      setError(e.message)
      setState(PIPELINE_STATES.ERROR)
    }
  }, [])

  // ── Message handler ───────────────────────────────────────────────────────
  const _handleMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'turn_update': {
        const { citizen_turn, ai_turn, session, nlu, mock_mode } = msg
        setIsMockMode(mock_mode || false)
        setSessionMeta(session)
        setLastNlu(nlu)
        setTurns(prev => [...prev, citizen_turn, ai_turn])
        // Play TTS audio
        _playAudio(ai_turn?.tts_audio_b64)
        setState(PIPELINE_STATES.VERIFYING)
        break
      }

      case 'verification_result': {
        const { state: vState, ai_response, tts_audio_b64, clarification_count } = msg
        setTurns(prev => [...prev, {
          speaker: 'ai',
          raw_transcript: ai_response,
          verification_state: vState,
          timestamp: new Date().toISOString(),
        }])
        _playAudio(tts_audio_b64)
        if (vState === 'correct') setState(PIPELINE_STATES.READY)
        else setState(PIPELINE_STATES.VERIFYING)
        break
      }

      case 'escalation': {
        const { packet, tts_audio_b64, escalation_message } = msg
        setEscalationPacket(packet)
        setTurns(prev => [...prev, {
          speaker: 'ai',
          raw_transcript: escalation_message,
          timestamp: new Date().toISOString(),
        }])
        _playAudio(tts_audio_b64)
        setState(PIPELINE_STATES.ESCALATED)
        break
      }

      case 'error':
        setError(msg.message)
        setState(PIPELINE_STATES.ERROR)
        break

      case 'pong':
        break
    }
  }, [])

  // ── Audio recording ───────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    if (state !== PIPELINE_STATES.READY && state !== PIPELINE_STATES.VERIFYING) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      recorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.start(100) // 100ms chunks
      setState(PIPELINE_STATES.RECORDING)
    } catch (e) {
      setError(`Microphone access denied: ${e.message}`)
      setState(PIPELINE_STATES.ERROR)
    }
  }, [state])

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current
    if (!recorder || recorder.state === 'inactive') return
    setState(PIPELINE_STATES.PROCESSING)

    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      const arrayBuffer = await blob.arrayBuffer()
      const b64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)))

      const ws = wsRef.current
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'audio',
          data: b64,
          language: sessionMeta?.detected_language || 'kn',
          district: sessionMeta?.district || 'default',
        }))
      }
      recorder.stream.getTracks().forEach(t => t.stop())
    }
    recorder.stop()
  }, [sessionMeta])

  // ── Verification response ─────────────────────────────────────────────────
  const sendVerification = useCallback((text) => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'verification', data: text }))
    }
  }, [])

  // ── Agent correction ──────────────────────────────────────────────────────
  const sendAgentCorrection = useCallback((turnId, correction, intent) => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'agent_correction',
        turn_id: turnId,
        correction,
        intent,
      }))
    }
  }, [])

  // ── TTS playback ──────────────────────────────────────────────────────────
  const _playAudio = (b64) => {
    if (!b64 || b64.length < 100) return   // skip mock/empty audio
    try {
      const bytes = atob(b64)
      const buf   = new ArrayBuffer(bytes.length)
      const view  = new Uint8Array(buf)
      for (let i = 0; i < bytes.length; i++) view[i] = bytes.charCodeAt(i)
      const blob  = new Blob([buf], { type: 'audio/wav' })
      const url   = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.play().catch(() => {})
      audio.onended = () => URL.revokeObjectURL(url)
    } catch (e) {}
  }

  // ── Cleanup ───────────────────────────────────────────────────────────────
  const endSession = useCallback(() => {
    wsRef.current?.close()
    recorderRef.current?.stream?.getTracks().forEach(t => t.stop())
    setState(PIPELINE_STATES.IDLE)
    setSessionId(null)
    setTurns([])
    setSessionMeta(null)
    setEscalationPacket(null)
  }, [])

  return {
    state, sessionId, turns, sessionMeta, escalationPacket,
    lastNlu, error, isMockMode,
    startSession, endSession,
    startRecording, stopRecording,
    sendVerification, sendAgentCorrection,
  }
}
