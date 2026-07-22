import React from 'react'

// Modern Forest Athletic tokens
const T = {
  emerald: '#0f2a1f',
  neon:    '#3dfc3d',
  surface: '#faf9f7',
}

const s = {
  root:   { display: 'flex', flexDirection: 'column', minHeight: '100vh' },

  topbar: {
    height: 56, background: T.emerald,
    display: 'flex', alignItems: 'center',
    padding: '0 20px', gap: 8, flexShrink: 0,
    position: 'sticky', top: 0, zIndex: 100,
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 8, flex: 1,
  },
  logoMark: {
    width: 28, height: 28, background: T.neon, borderRadius: 6,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, fontWeight: 800, color: T.emerald,
  },
  brandText: { color: '#fff', fontWeight: 700, fontSize: 18 },

  topLinks: {
    display: 'flex', alignItems: 'center', gap: 4,
  },
  topLink: (active) => ({
    color: active ? '#fff' : 'rgba(255,255,255,0.55)',
    fontWeight: active ? 600 : 400, fontSize: 14,
    background: active ? 'rgba(61,252,61,0.12)' : 'none',
    border: 'none', cursor: 'pointer',
    padding: '6px 12px', borderRadius: 6,
    transition: 'background .15s',
  }),

  welcome: {
    color: 'rgba(255,255,255,0.5)', fontSize: 13,
    marginLeft: 8, whiteSpace: 'nowrap',
  },
  logout: {
    background: 'none', border: '1px solid rgba(255,255,255,0.2)',
    color: 'rgba(255,255,255,0.6)', cursor: 'pointer',
    fontSize: 12, padding: '5px 10px', borderRadius: 6, marginLeft: 8,
    flexShrink: 0,
  },

  main: { flex: 1, background: '#1b2d22' },

  // Bottom nav (shown on mobile via CSS class)
  bottomNav: {
    position: 'fixed', bottom: 0, left: 0, right: 0,
    height: 64, background: T.emerald,
    display: 'flex', alignItems: 'center', justifyContent: 'space-around',
    zIndex: 100, borderTop: '1px solid rgba(255,255,255,0.08)',
  },
  navItem: (active) => ({
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    gap: 3, padding: '6px 20px', borderRadius: 10,
    background: active ? 'rgba(61,252,61,0.12)' : 'none',
    border: 'none', cursor: 'pointer',
    minWidth: 64,
  }),
  navIcon: (active) => ({
    fontSize: 20, lineHeight: 1,
    color: active ? T.neon : 'rgba(255,255,255,0.45)',
  }),
  navLabel: (active) => ({
    fontSize: 10, fontWeight: 600,
    color: active ? T.neon : 'rgba(255,255,255,0.45)',
    textTransform: 'uppercase', letterSpacing: '.05em',
  }),
}

export default function AppShell({ activeView, onDashboard, onRoster, onLogout, hasTeam, coachName, children }) {
  return (
    <div style={s.root}>
      <nav style={s.topbar}>
        <div style={s.logo}>
          <div style={s.logoMark}>F</div>
          <span style={s.brandText}>FuelUp Coach</span>
        </div>

        {/* Desktop nav links — hidden on mobile via CSS */}
        <div className="top-nav-links" style={s.topLinks}>
          <button style={s.topLink(activeView === 'dashboard')} onClick={onDashboard}>
            Dashboard
          </button>
          {hasTeam && (
            <button style={s.topLink(activeView === 'roster')} onClick={onRoster}>
              Roster
            </button>
          )}
        </div>

        {coachName && <span style={s.welcome}>Welcome, {coachName}</span>}
        <button style={s.logout} onClick={onLogout}>Sign out</button>
      </nav>

      <main className="main-content" style={s.main}>{children}</main>

      {/* Mobile bottom nav */}
      <nav className="bottom-nav" style={s.bottomNav}>
        <button style={s.navItem(activeView === 'dashboard')} onClick={onDashboard}>
          <span style={s.navIcon(activeView === 'dashboard')}>⊞</span>
          <span style={s.navLabel(activeView === 'dashboard')}>Teams</span>
        </button>
        {hasTeam && (
          <button style={s.navItem(activeView === 'roster')} onClick={onRoster}>
            <span style={s.navIcon(activeView === 'roster')}>👥</span>
            <span style={s.navLabel(activeView === 'roster')}>Roster</span>
          </button>
        )}
        <button style={s.navItem(false)} onClick={onLogout}>
          <span style={s.navIcon(false)}>↩</span>
          <span style={s.navLabel(false)}>Sign out</span>
        </button>
      </nav>
    </div>
  )
}
