import React, { useMemo } from 'react'
import { AlertCircle } from 'lucide-react'
import { useVoicePipeline, PIPELINE_STATES } from './hooks/useVoicePipeline'
import { CitizenPanel } from './components/CitizenPanel'
import { AgentDashboard } from './components/AgentDashboard'

export default function App() {
  const pipeline = useVoicePipeline()

  const lastAiTurn = useMemo(() => {
    const aiTurns = pipeline.turns.filter(t => t?.speaker === 'ai')
    return aiTurns[aiTurns.length - 1] || null
  }, [pipeline.turns])

  return (
    <div className="min-h-screen bg-[#0f1117] text-white">
      {/* Top bar */}
      <header className="border-b border-slate-800 px-6 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-karnataka-red" />
          <div className="w-3 h-3 rounded-full bg-karnataka-yellow" />
          <div className="w-3 h-3 rounded-full bg-karnataka-blue" />
        </div>
        <h1 className="text-sm font-semibold tracking-wide text-slate-200">
          Samvaad-Setu &nbsp;|&nbsp; ಸಂವಾದ ಸೇತು &nbsp;|&nbsp; Karnataka 1092
        </h1>
        {pipeline.isMockMode && (
          <span className="ml-auto text-xs text-yellow-400 border border-yellow-700 bg-yellow-900/30 px-2 py-0.5 rounded-full">
            ⚡ Running in mock mode — add API keys in .env to enable real pipeline
          </span>
        )}
      </header>

      {/* Error banner */}
      {pipeline.error && (
        <div className="mx-6 mt-4 flex items-center gap-3 bg-red-900/40 border border-red-700 rounded-xl p-3 text-sm text-red-300">
          <AlertCircle size={16} className="flex-shrink-0" />
          {pipeline.error}
        </div>
      )}

      {/* Split layout */}
      <div className="flex gap-0 h-[calc(100vh-57px)]">
        {/* LEFT — Citizen voice interface */}
        <aside className="w-80 flex-shrink-0 border-r border-slate-800 p-5 overflow-y-auto">
          <CitizenPanel
            pipelineState={pipeline.state}
            sessionId={pipeline.sessionId}
            isMockMode={pipeline.isMockMode}
            lastAiTurn={lastAiTurn}
            onStart={pipeline.startSession}
            onEnd={pipeline.endSession}
            onRecordStart={pipeline.startRecording}
            onRecordStop={pipeline.stopRecording}
            onVerify={pipeline.sendVerification}
          />
        </aside>

        {/* RIGHT — Agent dashboard */}
        <main className="flex-1 overflow-y-auto p-5">
          <AgentDashboard
            turns={pipeline.turns}
            sessionMeta={pipeline.sessionMeta}
            escalationPacket={pipeline.escalationPacket}
            lastNlu={pipeline.lastNlu}
            onAgentCorrection={(correction) => {
              const lastCitizenTurn = [...pipeline.turns].reverse().find(t => t?.speaker === 'citizen')
              if (lastCitizenTurn) {
                pipeline.sendAgentCorrection(lastCitizenTurn.turn_id, correction)
              }
            }}
          />
        </main>
      </div>
    </div>
  )
}
