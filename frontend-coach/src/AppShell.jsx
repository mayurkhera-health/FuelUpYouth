import React from 'react'

const SIDEBAR_W = 220

const s = {
  root:    { display: 'flex', minHeight: '100vh' },
  sidebar: {
    width: SIDEBAR_W, minWidth: SIDEBAR_W,
    background: '#0f2d1a', display: 'flex', flexDirection: 'column',
    padding: '28px 0',
  },
  brand:   { color: '#fff', fontWeight: 700, fontSize: 17, padding: '0 24px', marginBottom: 32 },
  nav:     { flex: 1, display: 'flex', flexDirection: 'column', gap: 4, padding: '0 12px' },
  link:    (active) => ({
    display: 'block', padding: '10px 16px', borderRadius: 8, cursor: 'pointer',
    fontWeight: active ? 600 : 400, fontSize: 15,
    color: active ? '#fff' : 'rgba(255,255,255,0.65)',
    background: active ? '#1a7a4a' : 'none',
    border: 'none', textAlign: 'left', width: '100%',
  }),
  foot:    { padding: '0 12px' },
  logout:  {
    display: 'block', padding: '10px 16px', borderRadius: 8, cursor: 'pointer',
    fontSize: 14, color: 'rgba(255,255,255,0.5)', background: 'none',
    border: 'none', textAlign: 'left', width: '100%',
  },
  main:    { flex: 1, background: '#f5f5f5', minHeight: '100vh', overflow: 'auto' },
}

export default function AppShell({ activeView, onDashboard, onRoster, onLogout, hasTeam, children }) {
  return (
    <div style={s.root}>
      <aside style={s.sidebar}>
        <div style={s.brand}>FuelUp Coach</div>
        <nav style={s.nav}>
          <button style={s.link(activeView === 'dashboard')} onClick={onDashboard}>
            Dashboard
          </button>
          {hasTeam && (
            <button style={s.link(activeView === 'roster')} onClick={onRoster}>
              Roster
            </button>
          )}
        </nav>
        <div style={s.foot}>
          <button style={s.logout} onClick={onLogout}>Log out</button>
        </div>
      </aside>
      <main style={s.main}>{children}</main>
    </div>
  )
}
