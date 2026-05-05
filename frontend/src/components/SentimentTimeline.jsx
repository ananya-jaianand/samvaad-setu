import React from 'react'

const SENTIMENT_CONFIG = {
  distress:  { color: '#ef4444', emoji: '😰', bg: 'bg-red-900/30' },
  anger:     { color: '#f97316', emoji: '😠', bg: 'bg-orange-900/30' },
  fear:      { color: '#a855f7', emoji: '😨', bg: 'bg-purple-900/30' },
  urgency:   { color: '#f59e0b', emoji: '⚡', bg: 'bg-yellow-900/30' },
  confusion: { color: '#6b7280', emoji: '😕', bg: 'bg-slate-700/30' },
  calm:      { color: '#22c55e', emoji: '😌', bg: 'bg-green-900/30' },
}

export function SentimentTimeline({ timeline = [] }) {
  if (timeline.length === 0) {
    return (
      <div className="text-xs text-slate-500 italic text-center py-4">
        Sentiment timeline will appear here during the call.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {timeline.map((entry, i) => {
        const config = SENTIMENT_CONFIG[entry.label] || SENTIMENT_CONFIG.calm
        const barWidth = `${Math.round(entry.score * 100)}%`

        return (
          <div key={i} className={`rounded-lg p-2 ${config.bg}`}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">{config.emoji}</span>
                <span className="text-xs font-semibold capitalize" style={{ color: config.color }}>
                  {entry.label}
                </span>
              </div>
              <span className="text-xs text-slate-400">
                {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </div>
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: barWidth, backgroundColor: config.color }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
