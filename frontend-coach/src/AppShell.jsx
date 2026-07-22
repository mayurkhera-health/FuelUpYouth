import React from 'react'

const T = {
  emerald:    '#0f2a1f',
  emeraldMid: '#162e20',
  neon:       '#3dfc3d',
}

const W = 240  // sidebar width

const NAV = [
  { key: 'dashboard', label: 'Dashboard', icon: '⊞' },
  { key: 'roster',    label: 'Roster',    icon: '◉',  requiresTeam: true },
  { key: 'reports',   label: 'Reports',   icon: '▤',  disabled: true },
]

const s = {
  root: { display: 'flex', minHeight: '100vh' },

  // ── Sidebar ────────────────────────────────────────────────────────────
  sidebar: {
    width: W, flexShrink: 0,
    background: T.emerald,
    display: 'flex', flexDirection: 'column',
    position: 'fixed', top: 0, left: 0, bottom: 0,
    zIndex: 100,
    borderRight: '1px solid rgba(255,255,255,0.06)',
  },

  brand: {
    padding: '20px 20px 18px',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
    display: 'flex', alignItems: 'center', gap: 10,
    flexShrink: 0,
  },
  logoMark: {
    width: 32, height: 32, background: T.neon, borderRadius: 8,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 16, fontWeight: 800, color: T.emerald, flexShrink: 0,
  },
  brandText: { color: '#fff', fontWeight: 700, fontSize: 16, lineHeight: 1.2 },
  brandSub:  { color: 'rgba(255,255,255,0.4)', fontSize: 11, fontWeight: 500 },

  navSection: { flex: 1, padding: '10px 0', overflowY: 'auto' },
  navLabel:   { fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)',
                textTransform: 'uppercase', letterSpacing: '.1em',
                padding: '14px 20px 6px' },

  navItem: (active, disabled) => ({
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '10px 18px 10px 16px',
    marginInline: 8, borderRadius: 8,
    color: disabled ? 'rgba(255,255,255,0.2)'
         : active   ? '#fff'
         :            'rgba(255,255,255,0.58)',
    background: active ? 'rgba(61,252,61,0.1)' : 'none',
    border: 'none', cursor: disabled ? 'default' : 'pointer',
    width: 'calc(100% - 16px)', textAlign: 'left',
    fontSize: 14, fontWeight: active ? 600 : 500,
    transition: 'background .1s',
  }),
  navIcon: (active, disabled) => ({
    fontSize: 16, width: 22, textAlign: 'center', flexShrink: 0,
    color: disabled ? 'rgba(255,255,255,0.15)'
         : active   ? T.neon
         :            'rgba(255,255,255,0.4)',
  }),
  activeBar: {
    position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
    width: 3, height: 20, background: T.neon, borderRadius: '0 3px 3px 0',
  },
  comingSoon: {
    marginLeft: 'auto', fontSize: 10, fontWeight: 600,
    color: 'rgba(255,255,255,0.25)', letterSpacing: '.04em',
  },

  // ── Sidebar bottom ─────────────────────────────────────────────────────
  sidebarBottom: {
    padding: '14px 16px',
    borderTop: '1px solid rgba(255,255,255,0.07)',
    flexShrink: 0,
  },
  coachRow: {
    display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10,
  },
  avatar: {
    width: 34, height: 34, borderRadius: '50%',
    background: 'rgba(61,252,61,0.15)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, fontWeight: 700, color: T.neon, flexShrink: 0,
  },
  coachName: { fontSize: 13, fontWeight: 600, color: '#fff', lineHeight: 1.2 },
  coachRole: { fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 },
  signOut: {
    width: '100%', padding: '8px 0', background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
    fontSize: 13, fontWeight: 500, borderRadius: 7,
  },

  // ── Main content ────────────────────────────────────────────────────────
  main: {
    marginLeft: W,
    flex: 1,
    background: '#1b2d22',
    minHeight: '100vh',
  },

  // ── Mobile: hide sidebar, show bottom nav ───────────────────────────────
  bottomNav: {
    position: 'fixed', bottom: 0, left: 0, right: 0,
    height: 64, background: T.emerald,
    display: 'flex', alignItems: 'center', justifyContent: 'space-around',
    zIndex: 100, borderTop: '1px solid rgba(255,255,255,0.08)',
  },
  bnItem: (active) => ({
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
    padding: '6px 20px', borderRadius: 10,
    background: active ? 'rgba(61,252,61,0.12)' : 'none',
    border: 'none', cursor: 'pointer', minWidth: 64,
  }),
  bnIcon:  (active) => ({ fontSize: 20, color: active ? T.neon : 'rgba(255,255,255,0.4)' }),
  bnLabel: (active) => ({
    fontSize: 10, fontWeight: 600,
    color: active ? T.neon : 'rgba(255,255,255,0.4)',
    textTransform: 'uppercase', letterSpacing: '.05em',
  }),
}

function initials(name) {
  if (!name) return 'C'
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

function navAction(key, { onDashboard, onRoster }) {
  if (key === 'dashboard') return onDashboard
  if (key === 'roster')    return onRoster
  return null
}

export default function AppShell({ activeView, onDashboard, onRoster, onLogout, hasTeam, coachName, children }) {
  return (
    <div style={s.root}>

      {/* ── Desktop sidebar (hidden on mobile via CSS) ── */}
      <aside className="sidebar" style={s.sidebar}>

        <div style={s.brand}>
          <div style={s.logoMark}>F</div>
          <div>
            <div style={s.brandText}>FuelUp Coach</div>
            <div style={s.brandSub}>Team Dashboard</div>
          </div>
        </div>

        <nav style={s.navSection}>
          <div style={s.navLabel}>Navigation</div>
          {NAV.map(item => {
            if (item.requiresTeam && !hasTeam) return null
            const active   = activeView === item.key
            const disabled = !!item.disabled
            const action   = disabled ? undefined : navAction(item.key, { onDashboard, onRoster })
            return (
              <div key={item.key} style={{ position: 'relative' }}>
                {active && <div style={s.activeBar} />}
                <button
                  style={s.navItem(active, disabled)}
                  onClick={action}
                  disabled={disabled}
                >
                  <span style={s.navIcon(active, disabled)}>{item.icon}</span>
                  {item.label}
                  {disabled && <span style={s.comingSoon}>Soon</span>}
                </button>
              </div>
            )
          })}
        </nav>

        <div style={s.sidebarBottom}>
          {coachName && (
            <div style={s.coachRow}>
              <div style={s.avatar}>{initials(coachName)}</div>
              <div>
                <div style={s.coachName}>{coachName}</div>
                <div style={s.coachRole}>Head Coach</div>
              </div>
            </div>
          )}
          <button style={s.signOut} onClick={onLogout}>Sign out</button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="main-content" style={s.main}>{children}</main>

      {/* ── Mobile bottom nav ── */}
      <nav className="bottom-nav" style={s.bottomNav}>
        <button style={s.bnItem(activeView === 'dashboard')} onClick={onDashboard}>
          <span style={s.bnIcon(activeView === 'dashboard')}>⊞</span>
          <span style={s.bnLabel(activeView === 'dashboard')}>Teams</span>
        </button>
        {hasTeam && (
          <button style={s.bnItem(activeView === 'roster')} onClick={onRoster}>
            <span style={s.bnIcon(activeView === 'roster')}>◉</span>
            <span style={s.bnLabel(activeView === 'roster')}>Roster</span>
          </button>
        )}
        <button style={s.bnItem(false)} onClick={onLogout}>
          <span style={s.bnIcon(false)}>↩</span>
          <span style={s.bnLabel(false)}>Sign out</span>
        </button>
      </nav>

    </div>
  )
}
