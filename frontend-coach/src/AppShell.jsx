import React from 'react'

const s = {
  root:   { display: 'flex', flexDirection: 'column', minHeight: '100vh' },
  topbar: {
    height: 52, background: '#0f2d1a', display: 'flex', alignItems: 'center',
    padding: '0 32px', gap: 8, flexShrink: 0,
  },
  brand:  { color: '#fff', fontWeight: 700, fontSize: 16, marginRight: 20 },
  link:   (active) => ({
    color: active ? '#fff' : 'rgba(255,255,255,0.6)',
    fontWeight: active ? 600 : 400, fontSize: 14,
    background: 'none', border: 'none', cursor: 'pointer',
    padding: '4px 10px',
    borderBottom: active ? '2px solid #4dbb7a' : '2px solid transparent',
  }),
  welcome: {
    marginLeft: 'auto', color: 'rgba(255,255,255,0.55)', fontSize: 13,
  },
  logout: {
    marginLeft: 16, color: 'rgba(255,255,255,0.4)', background: 'none',
    border: 'none', cursor: 'pointer', fontSize: 13,
  },
  main:   { flex: 1, background: '#f5f5f5' },
}

export default function AppShell({ activeView, onDashboard, onRoster, onLogout, hasTeam, coachName, children }) {
  return (
    <div style={s.root}>
      <nav style={s.topbar}>
        <span style={s.brand}>FuelUp Coach</span>
        <button style={s.link(activeView === 'dashboard')} onClick={onDashboard}>Dashboard</button>
        {hasTeam && (
          <button style={s.link(activeView === 'roster')} onClick={onRoster}>Roster</button>
        )}
        {coachName && <span style={s.welcome}>Welcome, {coachName}</span>}
        <button style={s.logout} onClick={onLogout}>Log out</button>
      </nav>
      <main style={s.main}>{children}</main>
    </div>
  )
}
