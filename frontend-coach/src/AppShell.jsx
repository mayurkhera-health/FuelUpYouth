import React, { useState, useEffect } from 'react'

const T = {
  sidebar: '#082C1F',
  neon:    '#31E65A',
  muted:   'rgba(255,255,255,0.45)',
  mutedLo: 'rgba(255,255,255,0.2)',
}

const W = 240   // full sidebar
const R = 80    // icon rail

const NAV = [
  { key: 'dashboard', label: 'Dashboard', icon: '⊞' },
  { key: 'roster',    label: 'Roster',    icon: '◉',  requiresTeam: true },
  { key: 'reports',   label: 'Reports',   icon: '▤' },
]

function initials(name) {
  if (!name) return 'C'
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

function navHandler(key, callbacks) {
  if (key === 'dashboard') return callbacks.onDashboard
  if (key === 'roster')    return callbacks.onRoster
  if (key === 'reports')   return callbacks.onReports
  return null
}

// ── Sidebar (1440px+) ─────────────────────────────────────────────────────────

function Sidebar({ activeView, onDashboard, onRoster, onReports, onLogout, hasTeam, coachName }) {
  return (
    <aside className="nav-sidebar" style={{
      width: W, flexShrink: 0, background: T.sidebar,
      display: 'flex', flexDirection: 'column',
      position: 'fixed', top: 0, left: 0, bottom: 0,
      zIndex: 100, borderRight: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{
        padding: '20px 20px 18px', borderBottom: '1px solid rgba(255,255,255,0.07)',
        display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0,
      }}>
        <div style={{
          width: 32, height: 32, background: T.neon, borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, fontWeight: 800, color: T.sidebar, flexShrink: 0,
        }}>F</div>
        <div>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 16, lineHeight: 1.2 }}>FuelUp Coach</div>
          <div style={{ color: T.muted, fontSize: 11, fontWeight: 500 }}>Team Dashboard</div>
        </div>
      </div>

      <nav style={{ flex: 1, padding: '10px 0', overflowY: 'auto' }}>
        <div style={{
          fontSize: 10, fontWeight: 700, color: T.mutedLo,
          textTransform: 'uppercase', letterSpacing: '.1em', padding: '14px 20px 6px',
        }}>Navigation</div>
        <NavItems
          activeView={activeView} hasTeam={hasTeam}
          callbacks={{ onDashboard, onRoster, onReports }}
        />
      </nav>

      <div style={{ padding: '14px 16px', borderTop: '1px solid rgba(255,255,255,0.07)', flexShrink: 0 }}>
        {coachName && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 34, height: 34, borderRadius: '50%', background: 'rgba(49,230,90,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700, color: T.neon, flexShrink: 0,
            }}>
              {initials(coachName)}
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', lineHeight: 1.2 }}>{coachName}</div>
              <div style={{ fontSize: 11, color: T.muted, marginTop: 1 }}>Head Coach</div>
            </div>
          </div>
        )}
        <button onClick={onLogout} style={{
          width: '100%', padding: '8px 0', background: 'rgba(255,255,255,0.05)',
          border: '1px solid rgba(255,255,255,0.1)', color: T.muted, cursor: 'pointer',
          fontSize: 13, fontWeight: 500, borderRadius: 7,
        }}>Sign out</button>
      </div>
    </aside>
  )
}

// ── Nav items (shared between sidebar & drawer) ───────────────────────────────

function NavItems({ activeView, hasTeam, callbacks, onNav }) {
  return NAV.map(item => {
    if (item.requiresTeam && !hasTeam) return null
    const active   = activeView === item.key
    const handler  = navHandler(item.key, callbacks)
    const action   = () => { handler?.(); onNav?.() }

    return (
      <div key={item.key} style={{ position: 'relative' }}>
        {active && (
          <div style={{
            position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
            width: 3, height: 20, background: T.neon, borderRadius: '0 3px 3px 0',
          }} />
        )}
        <button
          onClick={action}
          style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 18px 10px 16px', marginInline: 8, borderRadius: 8,
            color: active ? '#fff' : T.muted,
            background: active ? 'rgba(49,230,90,0.1)' : 'none',
            border: 'none', cursor: 'pointer',
            width: 'calc(100% - 16px)', textAlign: 'left',
            fontSize: 14, fontWeight: active ? 600 : 500,
            transition: 'background .1s',
          }}
        >
          <span style={{
            fontSize: 16, width: 22, textAlign: 'center', flexShrink: 0,
            color: active ? T.neon : 'rgba(255,255,255,0.4)',
          }}>{item.icon}</span>
          {item.label}
        </button>
      </div>
    )
  })
}

// ── Icon rail (1024–1439px) ───────────────────────────────────────────────────

function IconRail({ activeView, onDashboard, onRoster, onReports, onLogout, hasTeam, coachName }) {
  return (
    <aside className="nav-icon-rail" style={{
      width: R, flexShrink: 0, background: T.sidebar,
      flexDirection: 'column', alignItems: 'center',
      position: 'fixed', top: 0, left: 0, bottom: 0,
      zIndex: 100, borderRight: '1px solid rgba(255,255,255,0.06)',
    }}>
      {/* Logo */}
      <div style={{
        padding: '16px 0', borderBottom: '1px solid rgba(255,255,255,0.07)',
        width: '100%', display: 'flex', justifyContent: 'center',
      }}>
        <div style={{
          width: 32, height: 32, background: T.neon, borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, fontWeight: 800, color: T.sidebar,
        }}>F</div>
      </div>

      {/* Nav icons */}
      <nav style={{ flex: 1, padding: '10px 0', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {NAV.map(item => {
          if (item.requiresTeam && !hasTeam) return null
          const active  = activeView === item.key
          const handler = navHandler(item.key, { onDashboard, onRoster, onReports })
          return (
            <button
              key={item.key}
              onClick={handler}
              title={item.label}
              aria-label={item.label}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                padding: '10px 0', width: 56, borderRadius: 10,
                background: active ? 'rgba(49,230,90,0.12)' : 'none',
                border: 'none', cursor: 'pointer', marginBottom: 2,
                transition: 'background .1s',
              }}
            >
              <span style={{
                fontSize: 18,
                color: active ? T.neon : 'rgba(255,255,255,0.4)',
              }}>{item.icon}</span>
              <span style={{
                fontSize: 9, fontWeight: 600, letterSpacing: '.04em',
                textTransform: 'uppercase',
                color: active ? T.neon : 'rgba(255,255,255,0.3)',
              }}>{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* Avatar */}
      <div style={{ padding: '12px 0', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
        <div style={{
          width: 34, height: 34, borderRadius: '50%', background: 'rgba(49,230,90,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, fontWeight: 700, color: T.neon, cursor: 'pointer',
        }} onClick={onLogout} title="Sign out" aria-label="Sign out">
          {initials(coachName)}
        </div>
      </div>
    </aside>
  )
}

// ── Top bar + Drawer (<1024px) ────────────────────────────────────────────────

function TopBarAndDrawer({ activeView, onDashboard, onRoster, onReports, onLogout, hasTeam, coachName }) {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  // Close drawer on Escape
  useEffect(() => {
    if (!open) return
    const handler = e => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  return (
    <>
      {/* Top bar */}
      <header className="nav-top-bar" style={{
        position: 'fixed', top: 0, left: 0, right: 0, height: 56,
        background: T.sidebar, zIndex: 100,
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        alignItems: 'center', justifyContent: 'space-between',
        padding: '0 16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28, height: 28, background: T.neon, borderRadius: 7,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, fontWeight: 800, color: T.sidebar,
          }}>F</div>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>FuelUp Coach</span>
        </div>
        <button
          onClick={() => setOpen(true)}
          aria-label="Open navigation"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#fff', fontSize: 22, lineHeight: 1, padding: 6,
          }}
        >☰</button>
      </header>

      {/* Overlay */}
      <div
        className={`nav-drawer-overlay${open ? ' open' : ''}`}
        onClick={close}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        className={`nav-drawer${open ? ' open' : ''}`}
        style={{ background: T.sidebar, display: 'flex', flexDirection: 'column' }}
        aria-label="Navigation"
      >
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 28, height: 28, background: T.neon, borderRadius: 7,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 800, color: T.sidebar,
            }}>F</div>
            <span style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>FuelUp Coach</span>
          </div>
          <button
            onClick={close}
            aria-label="Close navigation"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: T.muted, fontSize: 18, lineHeight: 1, padding: 4,
            }}
          >✕</button>
        </div>

        <nav style={{ flex: 1, padding: '10px 0', overflowY: 'auto' }}>
          <NavItems
            activeView={activeView} hasTeam={hasTeam}
            callbacks={{ onDashboard, onRoster, onReports }}
            onNav={close}
          />
        </nav>

        <div style={{ padding: '14px 16px', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
          {coachName && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <div style={{
                width: 34, height: 34, borderRadius: '50%', background: 'rgba(49,230,90,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 700, color: T.neon, flexShrink: 0,
              }}>{initials(coachName)}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', lineHeight: 1.2 }}>{coachName}</div>
                <div style={{ fontSize: 11, color: T.muted, marginTop: 1 }}>Head Coach</div>
              </div>
            </div>
          )}
          <button onClick={() => { onLogout(); close() }} style={{
            width: '100%', padding: '8px 0', background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.1)', color: T.muted, cursor: 'pointer',
            fontSize: 13, fontWeight: 500, borderRadius: 7,
          }}>Sign out</button>
        </div>
      </aside>
    </>
  )
}

// ── AppShell ──────────────────────────────────────────────────────────────────

export default function AppShell({ activeView, onDashboard, onRoster, onReports, onLogout, hasTeam, coachName, children }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>

      {/* Full sidebar — visible at 1440px+ via CSS */}
      <Sidebar
        activeView={activeView}
        onDashboard={onDashboard}
        onRoster={onRoster}
        onReports={onReports}
        onLogout={onLogout}
        hasTeam={hasTeam}
        coachName={coachName}
      />

      {/* Icon rail — visible at 1024–1439px via CSS */}
      <IconRail
        activeView={activeView}
        onDashboard={onDashboard}
        onRoster={onRoster}
        onReports={onReports}
        onLogout={onLogout}
        hasTeam={hasTeam}
        coachName={coachName}
      />

      {/* Top bar + drawer — visible <1024px via CSS */}
      <TopBarAndDrawer
        activeView={activeView}
        onDashboard={onDashboard}
        onRoster={onRoster}
        onReports={onReports}
        onLogout={onLogout}
        hasTeam={hasTeam}
        coachName={coachName}
      />

      {/* Main content */}
      <main className="main-content" style={{
        marginLeft: W,
        flex: 1,
        background: '#123826',
        minHeight: '100vh',
      }}>
        {children}
      </main>

    </div>
  )
}
