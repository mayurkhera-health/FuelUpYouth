import React, { useEffect, useState } from 'react'
import { fetchEngagement } from '../api.js'

const s = {
  wrap:   { padding: '32px 40px', maxWidth: 560 },
  nav:    { display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 24 },
  title:  { fontWeight: 700, fontSize: 22 },
  navRight: { display: 'flex', gap: 12, alignItems: 'center' },
  navBtn: { background: 'none', border: 'none', fontSize: 13, cursor: 'pointer',
            color: '#1a7a4a', padding: '4px 0' },
  logoutBtn: { display: 'none' },
  card:   { background: '#fff', borderRadius: 12, padding: 24, marginBottom: 16,
            boxShadow: '0 1px 4px rgba(0,0,0,.06)' },
  big:    { fontSize: 42, fontWeight: 700, color: '#1a7a4a', lineHeight: 1 },
  meta:   { fontSize: 14, color: '#555', marginTop: 8 },
  trend:  { fontSize: 14, marginTop: 10 },
  stamp:  { fontSize: 11, color: '#bbb', marginTop: 8 },
  noData: { color: '#999', fontSize: 14, fontStyle: 'italic' },
  rosterBtn: { width: '100%', padding: '14px 0', background: '#1a7a4a', color: '#fff',
               border: 'none', borderRadius: 10, fontSize: 15, fontWeight: 600,
               cursor: 'pointer' },
}

function TrendLine({ cur, prior }) {
  if (!prior) return null
  const diff = cur.players_above_threshold - prior.players_above_threshold
  if (diff > 0) return <span style={{ color: '#1a7a4a' }}>▲ {diff} more than last week</span>
  if (diff < 0) return <span style={{ color: '#c0392b' }}>▼ {Math.abs(diff)} fewer than last week</span>
  return <span style={{ color: '#888' }}>— Same as last week</span>
}

export default function TeamOverview({ team, onViewRoster, onSwitchTeam, onLogout }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchEngagement(team.id)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [team.id])

  const cur = data?.current_week

  return (
    <div style={s.wrap}>
      <div style={s.nav}>
        <div style={s.title}>{team.name}</div>
        <div style={s.navRight}>
          {onSwitchTeam && (
            <button style={s.navBtn} onClick={onSwitchTeam}>All Teams</button>
          )}
          <button style={s.logoutBtn} onClick={onLogout}>Sign out</button>
        </div>
      </div>

      {loading && <p style={s.noData}>Loading…</p>}

      {!loading && !cur && (
        <div style={s.card}>
          <div style={s.noData}>No engagement data yet.</div>
          <div style={{ ...s.noData, marginTop: 8, fontSize: 13 }}>
            Snapshots generate daily once athletes begin logging.
          </div>
        </div>
      )}

      {!loading && cur && (
        <div style={s.card}>
          <div style={s.big}>
            {cur.players_above_threshold}
            <span style={{ fontSize: 22, color: '#aaa', fontWeight: 400 }}>
              {' '}/ {cur.roster_count}
            </span>
          </div>
          <div style={s.meta}>
            athletes logged ≥{cur.threshold_pct}% of applicable windows this week
          </div>
          <div style={s.trend}>
            <TrendLine cur={cur} prior={data.prior_week} />
          </div>
          {data.last_updated && (
            <div style={s.stamp}>
              Snapshot: {new Date(data.last_updated + 'Z').toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric'
              })}
            </div>
          )}
        </div>
      )}

      <button style={s.rosterBtn} onClick={onViewRoster}>View Full Roster</button>
    </div>
  )
}
