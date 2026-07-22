import React, { useEffect, useState } from 'react'
import { fetchEngagement } from '../api.js'

const T = {
  primary:    '#17231D',
  darkGreen:  '#123D2F',
  brandGreen: '#1E5A45',
  lime:       '#CBEA58',
  muted:      '#65716B',
  surface:    '#FFFFFF',
  border:     '#DCE4DE',
  successBg:  '#EAF2EC',
  successBdr: '#BFD9C6',
  attn:       '#B86600',
  attnBg:     '#FFF4DD',
}

function ProgressBar({ value, max, threshold }) {
  const filled = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const good   = filled >= threshold
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 13, color: T.muted, fontWeight: 500 }}>
          Logged this week
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: good ? T.brandGreen : T.attn }}>
          {value} / {max} athletes
        </span>
      </div>
      <div style={{ height: 8, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${filled}%`,
          background: good ? T.brandGreen : T.attn,
          borderRadius: 4, transition: 'width .5s ease',
        }} />
      </div>
      <div style={{ fontSize: 12, color: T.muted, marginTop: 5 }}>
        Target: ≥{threshold}% of windows logged
      </div>
    </div>
  )
}

function fmtSnap(d) {
  if (!d) return null
  const iso = d.includes('T') ? d : d.replace(' ', 'T')
  const dt = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  if (isNaN(dt)) return null
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function TeamOverview({ team, onViewRoster, onSwitchTeam }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true); setData(null)
    fetchEngagement(team.id)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [team.id])

  const cur   = data?.current_week
  const prior = data?.prior_week
  const trendDiff = cur && prior
    ? cur.players_above_threshold - prior.players_above_threshold
    : null

  const good = cur
    ? (cur.players_above_threshold / (cur.roster_count || 1)) * 100 >= (cur.threshold_pct ?? team.threshold_pct ?? 70)
    : null

  return (
    <div style={{ minHeight: '100vh', background: '#F7F5ED' }}>
      <div style={{ padding: '32px 40px', maxWidth: 720, margin: '0 auto' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
          <button
            onClick={onSwitchTeam}
            aria-label="Back to dashboard"
            style={{
              background: 'none', border: 'none', fontSize: 26, cursor: 'pointer',
              color: T.muted, padding: '6px 6px 6px 0', lineHeight: 1,
              minWidth: 44, minHeight: 44, display: 'flex', alignItems: 'center',
            }}
          >‹</button>
          <h1 style={{ fontWeight: 700, fontSize: 32, color: T.primary, margin: 0, lineHeight: 1.1 }}>
            {team.name}
          </h1>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{
            background: T.surface, borderRadius: 16, padding: 28,
            border: `1px solid ${T.border}`,
            boxShadow: '0 4px 16px rgba(23,35,29,.05)',
          }}>
            <div className="shimmer" style={{ height: 14, width: '40%', marginBottom: 18, borderRadius: 4 }} />
            <div className="shimmer" style={{ height: 48, width: '30%', marginBottom: 16, borderRadius: 6 }} />
            <div className="shimmer" style={{ height: 8, width: '100%', borderRadius: 4 }} />
          </div>
        )}

        {/* No data */}
        {!loading && !cur && (
          <div style={{
            background: T.surface, borderRadius: 16, padding: 28,
            border: `1px solid ${T.border}`,
            boxShadow: '0 4px 16px rgba(23,35,29,.05)',
          }}>
            <div style={{ color: T.muted, fontSize: 15 }}>No engagement data yet.</div>
            <div style={{ color: T.muted, fontSize: 13, marginTop: 6, lineHeight: 1.5 }}>
              Snapshots generate nightly once athletes begin logging.
            </div>
          </div>
        )}

        {/* Engagement card */}
        {!loading && cur && (
          <div style={{
            background: T.surface, borderRadius: 16, padding: '24px 28px',
            border: `1px solid ${T.border}`,
            boxShadow: '0 4px 16px rgba(23,35,29,.05)',
            marginBottom: 16,
          }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 12 }}>
              This week
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontSize: 56, fontWeight: 800, color: good ? T.brandGreen : T.attn, lineHeight: 1 }}>
                {cur.players_above_threshold}
              </span>
              <span style={{ fontSize: 24, color: T.muted, fontWeight: 400 }}>/ {cur.roster_count}</span>
            </div>

            <ProgressBar
              value={cur.players_above_threshold}
              max={cur.roster_count}
              threshold={cur.threshold_pct ?? team.threshold_pct ?? 70}
            />

            {trendDiff !== null && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, marginTop: 14,
                padding: '10px 14px', borderRadius: 10,
                background: trendDiff > 0 ? T.successBg : trendDiff < 0 ? T.attnBg : '#f5f5f5',
                border: `1px solid ${trendDiff > 0 ? T.successBdr : trendDiff < 0 ? '#F5CB6B' : T.border}`,
              }}>
                <span style={{ fontSize: 14, color: trendDiff > 0 ? T.brandGreen : trendDiff < 0 ? T.attn : T.muted }}>
                  {trendDiff > 0 ? '▲' : trendDiff < 0 ? '▼' : '▬'}
                </span>
                <span style={{ fontSize: 13, fontWeight: 600, color: trendDiff > 0 ? T.brandGreen : trendDiff < 0 ? T.attn : T.muted }}>
                  {trendDiff > 0
                    ? `${trendDiff} more than last week`
                    : trendDiff < 0
                      ? `${Math.abs(trendDiff)} fewer than last week`
                      : 'Same as last week'}
                </span>
              </div>
            )}

            {data.last_updated && (
              <div style={{ fontSize: 11, color: T.muted, marginTop: 12 }}>
                Snapshot: {fmtSnap(data.last_updated)}
              </div>
            )}
          </div>
        )}

        <button
          onClick={onViewRoster}
          style={{
            width: '100%', padding: '15px 0',
            background: T.darkGreen, color: T.lime,
            border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 700,
            cursor: 'pointer', letterSpacing: '.02em',
            boxShadow: '0 4px 16px rgba(18, 61, 47, 0.2)',
          }}
        >
          View Full Roster →
        </button>

      </div>
    </div>
  )
}
