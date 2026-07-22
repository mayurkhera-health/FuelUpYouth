import React, { useEffect, useState } from 'react'
import { fetchRoster } from '../api.js'

// active       = logged in past 7 days
// no-activity  = joined but no recent log (covers inactive + no_data)
// not-joined   = no roster_membership row
const STATUS = {
  active:        { label: 'Logged',      color: '#1a7a4a', bg: '#eaf4ee', dashed: false },
  'no-activity': { label: 'No activity', color: '#888',    bg: '#f2f2f2', dashed: false },
  'not-joined':  { label: 'Not joined',  color: '#aaa',    bg: 'transparent', dashed: true },
}

function mapStatus(a) {
  if (a.join_status === 'not_joined') return 'not-joined'
  if (a.logging_status === 'active') return 'active'
  return 'no-activity'
}

const s = {
  wrap: { padding: '28px 40px', maxWidth: 720 },
  nav:  { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 },
  back: { background: 'none', border: 'none', fontSize: 22,
          cursor: 'pointer', color: '#1a7a4a', padding: '0 4px', lineHeight: 1 },
  title:    { fontWeight: 700, fontSize: 20, color: '#111' },
  sub:      { fontSize: 13, color: '#888', marginBottom: 24, marginLeft: 36 },
  list:     { display: 'flex', flexDirection: 'column', gap: 6 },
  row: (dashed) => ({
    background: '#fff',
    borderRadius: 8,
    border: dashed ? '1.5px dashed #ddd' : '1px solid #e8e8e8',
    padding: '0 16px',
    height: 44,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  }),
  left: { display: 'flex', alignItems: 'baseline', gap: 6, overflow: 'hidden' },
  name: { fontWeight: 600, fontSize: 15, color: '#111', whiteSpace: 'nowrap' },
  demo: { fontSize: 13, color: '#888', whiteSpace: 'nowrap' },
  pill: (st) => ({
    flexShrink: 0, fontSize: 12, fontWeight: 600,
    padding: '3px 11px', borderRadius: 20,
    color: st.color, background: st.bg,
    border: st.dashed ? '1px solid #ddd' : 'none',
    whiteSpace: 'nowrap',
  }),
  footnote: { fontSize: 12, color: '#bbb', marginTop: 20, fontStyle: 'italic' },
  empty:    { color: '#999', fontSize: 14, textAlign: 'center', marginTop: 40 },
}

function demoLine(a) {
  const parts = []
  if (a.age) parts.push(`${a.age}y`)
  if (a.gender) parts.push(a.gender.charAt(0).toUpperCase() + a.gender.slice(1).toLowerCase())
  if (a.position) parts.push(a.position)
  return parts.join(' · ')
}

export default function RosterList({ team, onBack }) {
  const [roster, setRoster] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRoster(team.id)
      .then(d => { setRoster(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [team.id])

  const club = roster.find(a => a.competition_level)?.competition_level ?? null

  return (
    <div style={s.wrap}>
      <div style={s.nav}>
        <button style={s.back} onClick={onBack}>‹</button>
        <span style={s.title}>{team.name}</span>
      </div>
      <div style={s.sub}>
        {club ? `${club} · ` : ''}{roster.length} athlete{roster.length !== 1 ? 's' : ''}
      </div>

      {loading && <p style={s.empty}>Loading…</p>}
      {!loading && roster.length === 0 && (
        <p style={s.empty}>No athletes on this roster yet.</p>
      )}

      <div style={s.list}>
        {roster.map(a => {
          const key = mapStatus(a)
          const st  = STATUS[key]
          const demo = demoLine(a)
          return (
            <div key={a.athlete_id} style={s.row(st.dashed)}>
              <div style={s.left}>
                <span style={s.name}>{a.first_name}</span>
                {demo && <span style={s.demo}>{demo}</span>}
              </div>
              <span style={s.pill(st)}>{st.label}</span>
            </div>
          )
        })}
      </div>

      {!loading && roster.length > 0 && (
        <p style={s.footnote}>
          Status reflects app activity only, not verified nutrition intake.
        </p>
      )}
    </div>
  )
}
