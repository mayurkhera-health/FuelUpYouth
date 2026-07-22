import React, { useEffect, useState } from 'react'
import { fetchRoster } from '../api.js'

const STATUS = {
  active:   { label: 'Logged recently',     color: '#1a7a4a', bg: '#eaf4ee' },
  inactive: { label: 'Not logged recently', color: '#b35900', bg: '#fff4e8' },
  no_data:  { label: 'No data yet',         color: '#888',    bg: '#f2f2f2' },
}

const s = {
  wrap:  { padding: '32px 40px' },
  nav:   { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 },
  back:  { background: 'none', border: 'none', fontSize: 24,
           cursor: 'pointer', color: '#1a7a4a', padding: '0 4px' },
  title: { fontWeight: 700, fontSize: 20 },
  card:  { background: '#fff', borderRadius: 12, padding: '16px 20px',
           marginBottom: 10, boxShadow: '0 1px 3px rgba(0,0,0,.06)',
           display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' },
  left:  { flex: 1 },
  name:  { fontWeight: 700, fontSize: 16, marginBottom: 4 },
  meta:  { fontSize: 13, color: '#555', display: 'flex', gap: 12, flexWrap: 'wrap',
           marginBottom: 6 },
  pill:  { fontSize: 12, color: '#888', background: '#f2f2f2',
           borderRadius: 20, padding: '2px 10px' },
  last:  { fontSize: 12, color: '#aaa', marginTop: 4 },
  badge: (st) => ({
    fontSize: 12, fontWeight: 600, padding: '4px 12px',
    borderRadius: 20, color: st.color, background: st.bg,
    whiteSpace: 'nowrap', marginTop: 2,
  }),
  empty: { color: '#999', fontSize: 14, textAlign: 'center', marginTop: 40 },
}

function fmt(gender) {
  if (!gender) return null
  return gender.charAt(0).toUpperCase() + gender.slice(1).toLowerCase()
}

function fmtDate(d) {
  if (!d) return null
  const dt = new Date(d + 'T00:00:00')
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function RosterList({ team, onBack }) {
  const [roster, setRoster] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRoster(team.id)
      .then(d => { setRoster(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [team.id])

  return (
    <div style={s.wrap}>
      <div style={s.nav}>
        <button style={s.back} onClick={onBack}>‹</button>
        <div style={s.title}>{team.name} — Roster ({roster.length})</div>
      </div>

      {loading && <p style={s.empty}>Loading…</p>}
      {!loading && roster.length === 0 && (
        <p style={s.empty}>No athletes on this roster yet.</p>
      )}

      {roster.map(a => {
        const st = STATUS[a.logging_status] ?? STATUS.no_data
        return (
          <div key={a.athlete_id} style={s.card}>
            <div style={s.left}>
              <div style={s.name}>{a.first_name}</div>
              <div style={s.meta}>
                {a.age && <span>{a.age}y old</span>}
                {a.gender && <span>{fmt(a.gender)}</span>}
                {a.position && <span style={s.pill}>{a.position}</span>}
                {a.competition_level && <span style={s.pill}>{a.competition_level}</span>}
              </div>
              {a.last_logged_at
                ? <div style={s.last}>Last logged {fmtDate(a.last_logged_at)}</div>
                : <div style={s.last}>No logging activity yet</div>
              }
            </div>
            <span style={s.badge(st)}>{st.label}</span>
          </div>
        )
      })}
    </div>
  )
}
