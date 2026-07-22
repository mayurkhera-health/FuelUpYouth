import React, { useEffect, useState } from 'react'
import { fetchRoster } from '../api.js'

// Status logic unchanged — only presentation updated
// active       = logged in past 7 days
// no-activity  = joined but no recent log
// not-joined   = no roster_membership row
function mapStatus(a) {
  if (a.join_status === 'not_joined') return 'not-joined'
  if (a.logging_status === 'active') return 'active'
  return 'no-activity'
}

const T = {
  bg:        '#123826',
  primary:   '#173226',
  muted:     '#6D7A72',
  surface:   '#FFFFFF',
  border:    '#DDE5E0',
  neon:      '#31E65A',
  success:   '#1E9E57',
  successBg: '#EAF7EF',
  attn:      '#B86600',
  attnBg:    '#FFF4DD',
}

const STATUS_CONFIG = {
  active: {
    label: 'Active this week',
    color: T.success,
    bg:    T.successBg,
    border: '#c5e8d2',
    icon: '●',
  },
  'no-activity': {
    label: 'No recent activity',
    color: T.attn,
    bg:    T.attnBg,
    border: '#fde5a0',
    icon: '○',
  },
  'not-joined': {
    label: 'Not in app',
    color: T.muted,
    bg:    '#F5F5F5',
    border: T.border,
    icon: '○',
  },
}

function makeInitials(firstName) {
  if (!firstName) return '?'
  const words = firstName.trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[words.length - 1][0]).toUpperCase()
}

function demoLine(a) {
  const parts = []
  if (a.age) parts.push(`${a.age} yrs`)
  if (a.gender) parts.push(a.gender.charAt(0).toUpperCase() + a.gender.slice(1).toLowerCase())
  if (a.position) parts.push(a.position)
  return parts.join(' · ')
}

// ── Avatar ────────────────────────────────────────────────────────────────────

function Avatar({ name }) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: 42, height: 42, borderRadius: '50%', flexShrink: 0,
        background: '#EAF7EF',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, fontWeight: 700, color: T.success,
        userSelect: 'none',
      }}
    >
      {makeInitials(name)}
    </div>
  )
}

// ── StatusPill ────────────────────────────────────────────────────────────────

function StatusPill({ statusKey }) {
  const cfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG['not-joined']
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.border}`,
      fontSize: 12, fontWeight: 600,
      padding: '5px 11px', borderRadius: 15,
      whiteSpace: 'nowrap', flexShrink: 0,
    }}>
      <span style={{ fontSize: 8, lineHeight: 1 }}>{cfg.icon}</span>
      {cfg.label}
    </span>
  )
}

// ── Shimmer row ───────────────────────────────────────────────────────────────

function ShimmerRow() {
  return (
    <div style={{
      background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`,
      padding: '16px 22px', display: 'flex', alignItems: 'center', gap: 14,
    }}>
      <div className="shimmer" style={{ width: 42, height: 42, borderRadius: '50%', flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div className="shimmer" style={{ height: 16, width: '35%', marginBottom: 8, borderRadius: 4 }} />
        <div className="shimmer" style={{ height: 12, width: '22%', borderRadius: 4 }} />
      </div>
      <div className="shimmer" style={{ height: 30, width: 130, borderRadius: 15 }} />
    </div>
  )
}

// ── RosterList ────────────────────────────────────────────────────────────────

export default function RosterList({ team, onBack, onSelectAthlete }) {
  const [roster, setRoster]   = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRoster(team.id)
      .then(d  => { setRoster(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [team.id])

  const club        = roster.find(a => a.competition_level)?.competition_level ?? null
  const activeCount = roster.filter(a => mapStatus(a) === 'active').length

  const subtitleParts = [
    club,
    `${roster.length} athlete${roster.length !== 1 ? 's' : ''}`,
    !loading && roster.length > 0 ? `${activeCount} active this week` : null,
  ].filter(Boolean)

  return (
    <div style={{
      minHeight: '100vh',
      background: T.bg,
      backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.025) 1px, transparent 1px)',
      backgroundSize: '32px 32px',
    }}>
      <div className="roster-wrap">

        {/* Header */}
        <header style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              onClick={onBack}
              aria-label="Back to dashboard"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'rgba(255,255,255,0.7)', fontSize: 26, lineHeight: 1,
                padding: '10px 10px 10px 0',
                minWidth: 44, minHeight: 44,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
                flexShrink: 0,
              }}
            >‹</button>
            <h1 style={{
              fontWeight: 700, fontSize: 32, color: '#fff',
              lineHeight: 1.1, margin: 0, letterSpacing: '-.01em',
            }}>
              {team.name}
            </h1>
          </div>
          {!loading && (
            <div style={{
              fontSize: 15, color: 'rgba(255,255,255,0.5)',
              marginTop: 6, marginLeft: 2, fontWeight: 500,
            }}>
              {subtitleParts.join(' · ')}
            </div>
          )}
        </header>

        {/* Roster */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[0,1,2,3].map(i => <ShimmerRow key={i} />)}
          </div>
        )}

        {!loading && roster.length === 0 && (
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 14, textAlign: 'center', marginTop: 40 }}>
            No athletes on this roster yet.
          </p>
        )}

        {!loading && roster.length > 0 && (
          <div role="list" aria-label={`${team.name} roster`} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {roster.map(a => {
              const statusKey = mapStatus(a)
              const demo      = demoLine(a)
              const notJoined = statusKey === 'not-joined'
              return (
                <div
                  key={a.athlete_id}
                  role="listitem"
                  tabIndex={0}
                  onClick={() => onSelectAthlete?.(a)}
                  onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && onSelectAthlete?.(a)}
                  style={{
                    background: T.surface,
                    borderRadius: 14,
                    border: `${notJoined ? '1.5px dashed' : '1px solid'} ${notJoined ? '#c8d4cc' : T.border}`,
                    padding: '16px 22px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 14,
                    opacity: notJoined ? 0.75 : 1,
                    cursor: 'pointer',
                    transition: 'box-shadow 140ms ease-out, border-color 140ms ease-out',
                    outline: 'none',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,.10)'
                    e.currentTarget.style.borderColor = '#bdd4c4'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.boxShadow = ''
                    e.currentTarget.style.borderColor = notJoined ? '#c8d4cc' : T.border
                  }}
                  onFocus={e => { e.currentTarget.style.outline = `2px solid ${T.neon}`; e.currentTarget.style.outlineOffset = '2px' }}
                  onBlur={e => { e.currentTarget.style.outline = '' }}
                >
                  {/* Left: avatar + info */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0 }}>
                    <Avatar name={a.first_name} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{
                        fontWeight: 700, fontSize: 17, color: T.primary,
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      }}>
                        {a.first_name}
                      </div>
                      {demo && (
                        <div style={{ fontSize: 13, color: T.muted, marginTop: 2 }}>
                          {demo}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right: status pill + chevron */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                    <StatusPill statusKey={statusKey} />
                    <span style={{ fontSize: 18, color: T.muted, lineHeight: 1 }}>›</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Disclaimer */}
        {!loading && roster.length > 0 && (
          <p style={{
            fontSize: 12, color: 'rgba(255,255,255,0.28)',
            marginTop: 20, fontStyle: 'italic', lineHeight: 1.5,
          }}>
            Activity status reflects app usage only, not verified nutrition intake.
          </p>
        )}

      </div>
    </div>
  )
}
