import React, { useState } from 'react'
import { AlertTriangle, Edit3, Check, ChevronDown, ChevronUp } from 'lucide-react'
import { ConfidenceGauge } from './ConfidenceGauge'
import { SentimentTimeline } from './SentimentTimeline'
import { TranscriptPanel } from './TranscriptPanel'

const INTENT_LABELS = {
  water_supply_complaint: 'Water Supply',
  electricity_outage:     'Electricity Outage',
  road_damage:            'Road Damage',
  sanitation_garbage:     'Sanitation / Garbage',
  property_tax_query:     'Property Tax',
  birth_death_certificate:'Birth/Death Certificate',
  ration_card_issue:      'Ration Card',
  pension_scheme:         'Pension Scheme',
  police_complaint:       'Police Complaint',
  health_facility:        'Health Facility',
  land_records:           'Land Records',
  other_grievance:        'Other',
}

const ESCALATION_REASON_LABELS = {
  high_distress:         { label: 'High Distress Detected',      color: 'text-red-400',    bg: 'bg-red-900/30 border-red-700' },
  low_asr_confidence:    { label: 'Low ASR Confidence',          color: 'text-yellow-400', bg: 'bg-yellow-900/30 border-yellow-700' },
  high_intent_entropy:   { label: 'Ambiguous Request',           color: 'text-orange-400', bg: 'bg-orange-900/30 border-orange-700' },
  repeated_clarification:{ label: 'Repeated Clarification Failed',color: 'text-purple-400', bg: 'bg-purple-900/30 border-purple-700' },
  none:                  { label: 'No escalation',               color: 'text-green-400',  bg: '' },
}

export function AgentDashboard({
  turns = [],
  sessionMeta,
  escalationPacket,
  lastNlu,
  onAgentCorrection,
}) {
  const [editingInterpretation, setEditingInterpretation] = useState(false)
  const [editedText, setEditedText]  = useState('')
  const [ticketExpanded, setTicketExpanded] = useState(false)

  const confidence = sessionMeta?.composite_confidence ?? 1.0
  const timeline   = sessionMeta?.sentiment_timeline   ?? []
  const intent     = lastNlu?.intent ?? escalationPacket?.final_intent

  const reasonConfig = escalationPacket
    ? ESCALATION_REASON_LABELS[escalationPacket.reason] || ESCALATION_REASON_LABELS.none
    : null

  return (
    <div className="flex flex-col gap-5 h-full">
      {/* ── Escalation banner ─────────────────────────────────────────────── */}
      {escalationPacket && (
        <div className={`rounded-xl border p-4 ${reasonConfig.bg}`}>
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} className={`mt-0.5 flex-shrink-0 ${reasonConfig.color}`} />
            <div>
              <p className={`text-sm font-semibold ${reasonConfig.color}`}>
                Escalated — {reasonConfig.label}
              </p>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed">
                {escalationPacket.summary}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                <Badge label={`District: ${escalationPacket.district.replace('_', ' ')}`} />
                <Badge label={`Lang: ${escalationPacket.detected_language.toUpperCase()}`} />
                {intent && <Badge label={INTENT_LABELS[intent] || intent} />}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Gauges row ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-3 bg-slate-900 rounded-xl p-4 border border-slate-800">
        <ConfidenceGauge
          score={confidence}
          label="Composite"
        />
        <ConfidenceGauge
          score={lastNlu?.intent_confidence ?? 1.0}
          label="Intent"
        />
        <ConfidenceGauge
          score={sessionMeta ? 1 - Math.min(sessionMeta.clarification_count / 3, 1) : 1}
          label="Clarity"
        />
      </div>

      {/* ── AI Interpretation panel ───────────────────────────────────────── */}
      {(lastNlu || escalationPacket) && (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
              AI Interpretation
            </h3>
            {!editingInterpretation && (
              <button
                onClick={() => {
                  setEditedText(lastNlu?.structured_summary?.problem || escalationPacket?.ai_interpretation || '')
                  setEditingInterpretation(true)
                }}
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
              >
                <Edit3 size={12} /> Edit
              </button>
            )}
          </div>

          {editingInterpretation ? (
            <div className="space-y-2">
              <textarea
                value={editedText}
                onChange={e => setEditedText(e.target.value)}
                className="w-full bg-slate-800 border border-blue-500 rounded-lg p-2 text-sm text-white resize-none focus:outline-none"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    onAgentCorrection?.(editedText)
                    setEditingInterpretation(false)
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg"
                >
                  <Check size={12} /> Save & Train
                </button>
                <button
                  onClick={() => setEditingInterpretation(false)}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-slate-300 leading-relaxed">
                {lastNlu?.structured_summary?.problem || escalationPacket?.ai_interpretation || 'Awaiting input...'}
              </p>
              {intent && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Intent:</span>
                  <span className="text-xs bg-blue-900/60 text-blue-300 px-2 py-0.5 rounded border border-blue-800">
                    {INTENT_LABELS[intent] || intent}
                  </span>
                </div>
              )}
              {lastNlu?.structured_summary?.urgency_indicated && (
                <span className="inline-flex items-center gap-1 text-xs text-yellow-300 bg-yellow-900/40 border border-yellow-800 px-2 py-0.5 rounded">
                  ⚡ Urgency indicated
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Ticket draft (expandable) ─────────────────────────────────────── */}
      {escalationPacket?.ticket_draft && (
        <div className="bg-slate-900 rounded-xl border border-slate-800">
          <button
            onClick={() => setTicketExpanded(p => !p)}
            className="w-full flex items-center justify-between p-4 text-xs font-semibold text-slate-400 uppercase tracking-wide"
          >
            Ticket Draft
            {ticketExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {ticketExpanded && (
            <div className="px-4 pb-4 space-y-2 border-t border-slate-800 pt-3">
              {Object.entries(escalationPacket.ticket_draft).map(([k, v]) => (
                v && (
                  <div key={k} className="flex gap-2 text-xs">
                    <span className="text-slate-500 w-28 flex-shrink-0 capitalize">{k.replace(/_/g, ' ')}:</span>
                    <span className="text-slate-300">{typeof v === 'string' ? v : JSON.stringify(v)}</span>
                  </div>
                )
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Sentiment Timeline ─────────────────────────────────────────────── */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-3">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          Sentiment Timeline
        </h3>
        <SentimentTimeline timeline={timeline} />
      </div>

      {/* ── Transcript ────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-3 flex-1">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          Live Transcript
        </h3>
        <TranscriptPanel turns={turns} />
      </div>
    </div>
  )
}

function Badge({ label }) {
  return (
    <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
      {label}
    </span>
  )
}
