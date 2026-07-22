import React, { useEffect, useState } from 'react'
import { fetchRoster } from '../api.js'

const STATUS = {
  active:   { label: 'Logged recently',     color: '#1a7a4a' },
  inactive: { label: 'Not logged recently', color: '#e67e22' },
  no_data:  { label: 'No data yet',         color: '#aaa' },
}

const s = {
  wrap:  { minHeight: '100vh', background: '#f5f5f5',
           maxWidth: 480, margin: '0 auto', padding: 24 },
  nav:   { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 },
  back:  { background: 'none', border: 'none', fontSize: 24,
           cursor: 'pointer', color: '#1a7a4a', padding: '0 4px' },
  title: { fontWeight: 700, fontSize: 20 },
  card:  { background: '#fff', borderRadius: 10, padding: '14px 16px',
           marginBottom: 10, display: 'flex', justifyContent: 'space-between',
           alignItems: 'center', boxShadow: '0 1px 3px rgba(0,0,0,.05)' },
  name:  { fontWeight: 600, fontSize: 15 },
  join:  { fontSize: 12, color: '#aaa', marginTop: 2 },
  badge: { fontSize: 12, fontWeight: 600, padding: '3px 10px',
           borderRadius: 20, background: '#f0f0f0' },
  empty: { color: '#999', fontSize: 14, textAlign: 'center', marginTop: 40 },
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
        <div style={s.title}>{team.name} — Roster</div>
      </div>

      {loading && <p style={s.empty}>Loading…</p>}
      {!loading && roster.length === 0 && (
        <p style={s.empty}>No athletes on this roster yet.</p>
      )}
      {roster.map(a => {
        const st = STATUS[a.logging_status] ?? STATUS.no_data
        return (
          <div key={a.athlete_id} style={s.card}>
            <div>
              <div style={s.name}>{a.first_name}</div>
              <div style={s.join}>
                {a.join_status === 'joined' ? 'Joined' : 'Pending'}
              </div>
            </div>
            <span style={{ ...s.badge, color: st.color }}>{st.label}</span>
          </div>
        )
      })}
    </div>
  )
}
