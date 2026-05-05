import React, { useState } from 'react'
import { Mic, MicOff, Phone, PhoneOff, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { PIPELINE_STATES } from '../hooks/useVoicePipeline'

const DISTRICTS = [
  { value: 'default',        label: 'Select District' },
  { value: 'bengaluru_urban',label: 'Bengaluru Urban' },
  { value: 'mysuru',         label: 'Mysuru' },
  { value: 'mangaluru',      label: 'Mangaluru' },
  { value: 'belagavi',       label: 'Belagavi' },
  { value: 'kalaburagi',     label: 'Kalaburagi' },
]

const LANGUAGES = [
  { value: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { value: 'hi', label: 'हिंदी (Hindi)' },
  { value: 'en', label: 'English' },
]

export function CitizenPanel({
  pipelineState,
  sessionId,
  isMockMode,
  onStart,
  onEnd,
  onRecordStart,
  onRecordStop,
  onVerify,
  lastAiTurn,
}) {
  const [district, setDistrict] = useState('bengaluru_urban')
  const [language, setLanguage] = useState('kn')

  const isIdle       = pipelineState === PIPELINE_STATES.IDLE
  const isReady      = pipelineState === PIPELINE_STATES.READY
  const isRecording  = pipelineState === PIPELINE_STATES.RECORDING
  const isProcessing = pipelineState === PIPELINE_STATES.PROCESSING
  const isVerifying  = pipelineState === PIPELINE_STATES.VERIFYING
  const isEscalated  = pipelineState === PIPELINE_STATES.ESCALATED
  const isConnecting = pipelineState === PIPELINE_STATES.CONNECTING

  const stateLabel = {
    [PIPELINE_STATES.IDLE]:       '— Not connected —',
    [PIPELINE_STATES.CONNECTING]: 'Connecting...',
    [PIPELINE_STATES.READY]:      'Ready — press to speak',
    [PIPELINE_STATES.RECORDING]:  'Recording...',
    [PIPELINE_STATES.PROCESSING]: 'Processing audio...',
    [PIPELINE_STATES.VERIFYING]:  'Awaiting confirmation',
    [PIPELINE_STATES.ESCALATED]:  'Connecting to human agent',
    [PIPELINE_STATES.ERROR]:      'Error — check backend',
  }[pipelineState] || pipelineState

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-karnataka-red flex items-center justify-center text-white font-bold text-sm">
          1092
        </div>
        <div>
          <h2 className="text-white font-semibold text-sm">ಸಂವಾದ ಸೇತು</h2>
          <p className="text-slate-400 text-xs">Karnataka Citizen Helpline</p>
        </div>
        {isMockMode && (
          <span className="ml-auto text-xs bg-yellow-800/60 text-yellow-300 px-2 py-0.5 rounded-full border border-yellow-700">
            MOCK MODE
          </span>
        )}
      </div>

      {/* Session config — only when idle */}
      {isIdle && (
        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">District</label>
            <select
              value={district}
              onChange={e => setDistrict(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              {DISTRICTS.map(d => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Language</label>
            <div className="flex gap-2">
              {LANGUAGES.map(l => (
                <button
                  key={l.value}
                  onClick={() => setLanguage(l.value)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    language === l.value
                      ? 'bg-blue-600 border-blue-500 text-white'
                      : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Session info badge */}
      {sessionId && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className={`w-2 h-2 rounded-full ${isEscalated ? 'bg-red-500' : 'bg-green-500 animate-pulse'}`} />
          Session: <span className="font-mono text-slate-400">{sessionId.slice(0, 8)}</span>
        </div>
      )}

      {/* Status label */}
      <div className="text-center">
        <p className={`text-sm font-medium ${isRecording ? 'text-red-400' : 'text-slate-400'}`}>
          {stateLabel}
        </p>
      </div>

      {/* Main mic button */}
      <div className="flex justify-center">
        {(isReady || isVerifying) && (
          <button
            onMouseDown={onRecordStart}
            onMouseUp={onRecordStop}
            onTouchStart={onRecordStart}
            onTouchEnd={onRecordStop}
            className="w-24 h-24 rounded-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 flex items-center justify-center shadow-lg shadow-blue-900/50 transition-all"
          >
            <Mic size={36} className="text-white" />
          </button>
        )}

        {isRecording && (
          <button
            onMouseUp={onRecordStop}
            onTouchEnd={onRecordStop}
            className="w-24 h-24 rounded-full bg-red-600 flex items-center justify-center shadow-lg shadow-red-900/50 animate-recording"
          >
            <Mic size={36} className="text-white" />
          </button>
        )}

        {isProcessing && (
          <div className="w-24 h-24 rounded-full bg-slate-700 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isEscalated && (
          <div className="w-24 h-24 rounded-full bg-orange-900/50 border-2 border-orange-600 flex items-center justify-center">
            <AlertCircle size={36} className="text-orange-400" />
          </div>
        )}
      </div>

      <p className="text-center text-xs text-slate-600">
        {isReady || isVerifying ? 'Hold to speak, release to send' : ''}
      </p>

      {/* AI rephrasing for verification */}
      {isVerifying && lastAiTurn && (
        <div className="bg-slate-800/70 border border-slate-700 rounded-xl p-4 space-y-3">
          <p className="text-xs text-slate-400 font-medium">AI understood:</p>
          <p className="text-sm text-white kannada-text leading-relaxed">{lastAiTurn.raw_transcript}</p>
          <div className="flex gap-2">
            <button
              onClick={() => onVerify('ಹೌದು')}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-green-700 hover:bg-green-600 text-white text-sm font-medium transition"
            >
              <CheckCircle size={16} />
              Correct
            </button>
            <button
              onClick={() => onVerify('ಇಲ್ಲ')}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-red-800 hover:bg-red-700 text-white text-sm font-medium transition"
            >
              <XCircle size={16} />
              Wrong
            </button>
          </div>
        </div>
      )}

      {/* Start / End buttons */}
      <div className="flex gap-3 mt-auto">
        {isIdle ? (
          <button
            onClick={() => onStart({ district, language })}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-green-700 hover:bg-green-600 text-white font-medium transition"
          >
            <Phone size={18} /> Start Call
          </button>
        ) : (
          <button
            onClick={onEnd}
            disabled={isConnecting}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-medium transition"
          >
            <PhoneOff size={18} /> End Call
          </button>
        )}
      </div>
    </div>
  )
}
