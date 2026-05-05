import React, { useEffect, useRef } from 'react'

const SPEAKER_STYLES = {
  citizen: { label: '🧑 Citizen',   bg: 'bg-blue-900/40',   border: 'border-blue-700/50',  text: 'text-blue-200' },
  ai:      { label: '🤖 Samvaad',   bg: 'bg-slate-800/60',  border: 'border-slate-600/50', text: 'text-slate-200' },
  agent:   { label: '👤 Agent',     bg: 'bg-green-900/40',  border: 'border-green-700/50', text: 'text-green-200' },
}

const VERIFICATION_BADGES = {
  correct:           { label: '✓ Confirmed',  color: 'bg-green-700 text-green-100' },
  partially_correct: { label: '~ Partial',    color: 'bg-yellow-700 text-yellow-100' },
  incorrect:         { label: '✗ Incorrect',  color: 'bg-red-700 text-red-100' },
  pending:           { label: '◌ Pending',    color: 'bg-slate-600 text-slate-300' },
}

export function TranscriptPanel({ turns = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns.length])

  if (turns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-500 text-sm gap-2">
        <span className="text-3xl">🎙️</span>
        <p>Start recording to see the transcript</p>
      </div>
    )
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
      {turns.map((turn, i) => {
        if (!turn || !turn.speaker) return null
        const style = SPEAKER_STYLES[turn.speaker] || SPEAKER_STYLES.ai
        const time  = turn.timestamp
          ? new Date(turn.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          : ''
        const badge = turn.verification_state && turn.speaker === 'citizen'
          ? VERIFICATION_BADGES[turn.verification_state]
          : null

        return (
          <div key={i} className={`rounded-xl border p-3 ${style.bg} ${style.border}`}>
            <div className="flex items-center justify-between mb-1.5">
              <span className={`text-xs font-semibold ${style.text}`}>{style.label}</span>
              <div className="flex items-center gap-2">
                {badge && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.color}`}>
                    {badge.label}
                  </span>
                )}
                {turn.asr_confidence !== undefined && (
                  <span className="text-xs text-slate-500">
                    ASR {Math.round(turn.asr_confidence * 100)}%
                  </span>
                )}
                <span className="text-xs text-slate-500">{time}</span>
              </div>
            </div>
            <p className="text-sm leading-relaxed kannada-text">
              {turn.raw_transcript || turn.ai_rephrasing || '—'}
            </p>
            {turn.intent && (
              <span className="mt-1.5 inline-block text-xs bg-slate-700 text-slate-300 rounded px-2 py-0.5">
                {turn.intent.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
