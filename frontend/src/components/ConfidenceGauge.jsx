import React from 'react'

const RADIUS = 52
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function getColor(score) {
  if (score >= 0.75) return '#22c55e'   // green
  if (score >= 0.50) return '#f59e0b'   // amber
  return '#ef4444'                       // red
}

export function ConfidenceGauge({ score = 1.0, label = 'Confidence', size = 140 }) {
  const clampedScore = Math.max(0, Math.min(1, score))
  const offset = CIRCUMFERENCE * (1 - clampedScore)
  const color  = getColor(clampedScore)
  const pct    = Math.round(clampedScore * 100)

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox="0 0 120 120">
        {/* Background ring */}
        <circle cx="60" cy="60" r={RADIUS} fill="none" stroke="#1e293b" strokeWidth="10" />
        {/* Score ring */}
        <circle
          cx="60" cy="60" r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 60 60)"
          className="gauge-ring"
          style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s ease' }}
        />
        {/* Score text */}
        <text x="60" y="55" textAnchor="middle" fill={color}
              fontSize="22" fontWeight="700" fontFamily="Inter">
          {pct}
        </text>
        <text x="60" y="72" textAnchor="middle" fill="#64748b"
              fontSize="10" fontFamily="Inter">
          %
        </text>
      </svg>
      <span className="text-xs text-slate-400 font-medium tracking-wide uppercase">{label}</span>
    </div>
  )
}
