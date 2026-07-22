import React, { useEffect, useState } from 'react'
import { fetchEngagement } from '../api.js'

const T = {
  emerald: '#0f2a1f',
  neon:    '#3dfc3d',
  orange:  '#ff9800',
  surface: '#faf9f7',
  card:    '#ffffff',
  border:  '#dadad8',
}

function ProgressBar({ value, max, threshold }) {
  const filled = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const good   = filled >= threshold
  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: '#888', fontWeight: 500 }}>
          Logged this week
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: good ? T.emerald : T.orange }}>
          {value} / {max} athletes
        </span>
      </div>
      <div style={{ height: 10, background: T.border, borderRadius: 5, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${filled}%`,
          background: good ? T.neon : T.orange,
          borderRadius: 5, transition: 'width .5s ease',
        }} />
      </div>
      <div style={{ fontSize: 12, color: '#aaa', marginTop: 6 }}>
        Target: ≥{threshold}% of windows logged
      </div>
    </div>
  )
}

const s = {
  wrap:  { padding: '24px 20px', maxWidth: 560, margin: '0 auto' },
  nav:   { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 },
  back:  { background: 'none', border: 'none', fontSize: 22,
           cursor: 'pointer', color: T.emerald, padding: '0 4px' },
  title: { fontWeight: 800, fontSize: 22, color: T.emerald },

  card: {
    background: T.card, borderRadius: 14, padding: 24,
    marginBottom: 14, border: `1px solid ${T.border}`,
    boxShadow: '0 1px 6px rgba(0,0,0,.05)',
  },
  cardLabel: { fontSize: 12, fontWeight: 600, color: '#aaa',
               textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 },

  bigRow:  { display: 'flex', alignItems: 'baseline', gap: 6 },
  bigNum:  { fontSize: 52, fontWeight: 800, color: T.emerald, lineHeight: 1 },
  bigDenom: { fontSize: 24, color: '#ccc', fontWeight: 400 },

  trendRow: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 14,
              padding: '10px 12px', borderRadius: 8, background: T.surface },
  trendIcon: (up) => ({ fontSize: 16, color: up == null ? '#aaa' : up ? T.neon : T.orange }),
  trendText: (up) => ({ fontSize: 13, fontWeight: 600,
    color: up == null ? '#888' : up ? '#1a7a4a' : T.orange }),

  snap:  { fontSize: 11, color: '#ccc', marginTop: 14 },
  noData: { color: '#aaa', fontSize: 14, fontStyle: 'italic' },

  rosterBtn: {
    width: '100%', padding: '15px 0',
    background: T.emerald, color: T.neon,
    border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 700,
    cursor: 'pointer', letterSpacing: '.02em',
    boxShadow: `0 2px 12px rgba(15,42,31,.2)`,
  },

  shimCard: { background: T.card, borderRadius: 14, padding: 24,
              border: `1px solid ${T.border}`, marginBottom: 14 },
}

function fmtSnap(d) {
  if (!d) return null
  const iso = d.includes('T') ? d : d.replace(' ', 'T')
  const dt = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  if (isNaN(dt)) return null
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function TeamOverview({ team, onViewRoster, onSwitchTeam }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setData(null)
    fetchEngagement(team.id)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [team.id])

  const cur   = data?.current_week
  const prior = data?.prior_week
  const trendDiff = cur && prior
    ? cur.players_above_threshold - prior.players_above_threshold
    : null

  return (
    <div style={s.wrap}>
      <div style={s.nav}>
        <button style={s.back} onClick={onSwitchTeam}>‹</button>
        <div style={s.title}>{team.name}</div>
      </div>

      {loading && (
        <div style={s.shimCard}>
          <div className="shimmer" style={{ height: 14, width: '40%', marginBottom: 16 }} />
          <div className="shimmer" style={{ height: 52, width: '30%', marginBottom: 14 }} />
          <div className="shimmer" style={{ height: 10, width: '100%' }} />
        </div>
      )}

      {!loading && !cur && (
        <div style={s.card}>
          <div style={s.noData}>No engagement data yet.</div>
          <div style={{ ...s.noData, marginTop: 8, fontSize: 13 }}>
            Snapshots generate nightly once athletes begin logging.
          </div>
        </div>
      )}

      {!loading && cur && (
        <div style={s.card}>
          <div style={s.cardLabel}>This week</div>

          <div style={s.bigRow}>
            <span style={s.bigNum}>{cur.players_above_threshold}</span>
            <span style={s.bigDenom}>/ {cur.roster_count}</span>
          </div>

          <ProgressBar
            value={cur.players_above_threshold}
            max={cur.roster_count}
            threshold={cur.threshold_pct ?? team.threshold_pct ?? 70}
          />

          {trendDiff !== null && (
            <div style={s.trendRow}>
              <span style={s.trendIcon(trendDiff > 0 ? true : trendDiff < 0 ? false : null)}>
                {trendDiff > 0 ? '▲' : trendDiff < 0 ? '▼' : '▬'}
              </span>
              <span style={s.trendText(trendDiff > 0 ? true : trendDiff < 0 ? false : null)}>
                {trendDiff > 0
                  ? `${trendDiff} more than last week`
                  : trendDiff < 0
                    ? `${Math.abs(trendDiff)} fewer than last week`
                    : 'Same as last week'}
              </span>
            </div>
          )}

          {data.last_updated && (
            <div style={s.snap}>Snapshot: {fmtSnap(data.last_updated)}</div>
          )}
        </div>
      )}

      <button style={s.rosterBtn} onClick={onViewRoster}>View Full Roster →</button>
    </div>
  )
}
