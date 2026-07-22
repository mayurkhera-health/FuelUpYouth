import React from 'react'

const s = {
  wrap:  { padding: '32px 40px', maxWidth: 560 },
  title: { fontWeight: 700, fontSize: 22, color: '#1a7a4a', marginBottom: 6 },
  sub:   { color: '#888', fontSize: 14, marginBottom: 28 },
  card:  { background: '#fff', borderRadius: 10, padding: '16px 20px',
           marginBottom: 12, cursor: 'pointer', border: '1px solid #e5e5e5',
           display: 'flex', justifyContent: 'space-between', alignItems: 'center',
           boxShadow: '0 1px 3px rgba(0,0,0,.05)' },
  name:  { fontWeight: 600, fontSize: 16 },
  season:{ color: '#888', fontSize: 13, marginTop: 2 },
  arrow: { color: '#ccc', fontSize: 22 },
}

export default function TeamSelector({ teams, onSelect }) {
  return (
    <div style={s.wrap}>
      <div style={s.title}>Your Teams</div>
      <div style={s.sub}>Select a team to view engagement</div>
      {teams.map(t => (
        <div key={t.id} style={s.card} onClick={() => onSelect(t)}>
          <div>
            <div style={s.name}>{t.name}</div>
            <div style={s.season}>{t.season}</div>
          </div>
          <div style={s.arrow}>›</div>
        </div>
      ))}
    </div>
  )
}
