import React, { useEffect, useState } from 'react'
import { fetchAthleteDetail } from '../api.js'

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

function makeInitials(name) {
  if (!name) return '?'
  const words = name.trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[words.length - 1][0]).toUpperCase()
}

function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function fmtJoined(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function daysAgo(iso) {
  if (!iso) return null
  const then = new Date(iso + 'T12:00:00')
  const now  = new Date()
  const diff = Math.floor((now - then) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return `${diff} days ago`
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon, variant = 'default' }) {
  const variants = {
    default:   { bg: T.surface,    border: T.border,    numColor: T.primary,   subColor: T.muted },
    success:   { bg: T.successBg,  border: '#c5e8d2',   numColor: T.success,   subColor: T.muted },
    attention: { bg: T.attnBg,     border: '#fde5a0',   numColor: T.attn,      subColor: T.attn  },
    dark:      { bg: '#1e4a30',    border: '#2a6040',   numColor: T.neon,      subColor: 'rgba(49,230,90,0.55)' },
  }
  const v = variants[variant] || variants.default
  return (
    <div style={{
      background: v.bg, border: `1px solid ${v.border}`, borderRadius: 16,
      padding: '20px 22px', boxShadow: '0 1px 4px rgba(0,0,0,.06)',
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ fontSize: 13, color: v.subColor, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em' }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: 40, fontWeight: 800, color: v.numColor, lineHeight: 1.1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 13, color: v.subColor, fontWeight: 500 }}>{sub}</div>
      )}
    </div>
  )
}

// ── Shimmer ───────────────────────────────────────────────────────────────────

function ShimmerCard() {
  return (
    <div style={{ background: T.surface, borderRadius: 16, border: `1px solid ${T.border}`, padding: '20px 22px' }}>
      <div className="shimmer" style={{ height: 13, width: '50%', borderRadius: 4, marginBottom: 10 }} />
      <div className="shimmer" style={{ height: 40, width: '35%', borderRadius: 6 }} />
    </div>
  )
}

// ── Activity timeline bar ─────────────────────────────────────────────────────

function ActivityBar({ days7, days30 }) {
  const pct7  = Math.min(100, Math.round((days7  / 7)  * 100))
  const pct30 = Math.min(100, Math.round((days30 / 30) * 100))
  const color7  = pct7  >= 60 ? T.success : pct7  > 0 ? T.attn : T.muted
  const color30 = pct30 >= 60 ? T.success : pct30 > 0 ? T.attn : T.muted
  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16,
      padding: '20px 22px', boxShadow: '0 1px 4px rgba(0,0,0,.06)',
    }}>
      <div style={{ fontSize: 13, color: T.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 16 }}>
        📅 Logging Activity
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {[
          { label: 'This week', days: days7,  of: 7,  pct: pct7,  color: color7 },
          { label: 'Last 30 days', days: days30, of: 30, pct: pct30, color: color30 },
        ].map(row => (
          <div key={row.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 14, color: T.primary, fontWeight: 600 }}>{row.label}</span>
              <span style={{ fontSize: 14, color: row.color, fontWeight: 700 }}>
                {row.days} / {row.of} days ({row.pct}%)
              </span>
            </div>
            <div style={{ height: 8, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${row.pct}%`,
                background: row.color, borderRadius: 4,
                transition: 'width .4s ease',
              }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function AthleteDetail({ team, athlete: athleteStub, onBack }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    fetchAthleteDetail(team.id, athleteStub.athlete_id)
      .then(d => { setDetail(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [team.id, athleteStub.athlete_id])

  const name = detail?.first_name || athleteStub.first_name || '—'
  const status = detail?.logging_status
  const good = status === 'active'

  return (
    <div style={{
      minHeight: '100vh', background: T.bg,
      backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.025) 1px, transparent 1px)',
      backgroundSize: '32px 32px',
    }}>
      <div className="roster-wrap">

        {/* Header */}
        <header style={{ marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>
            <button
              onClick={onBack}
              aria-label="Back to roster"
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
              {name}
            </h1>
          </div>

          {/* Athlete identity card */}
          {!loading && detail && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 16,
              background: 'rgba(255,255,255,0.07)', borderRadius: 14,
              border: '1px solid rgba(255,255,255,0.1)',
              padding: '16px 20px',
            }}>
              {/* Avatar */}
              <div style={{
                width: 52, height: 52, borderRadius: '50%', flexShrink: 0,
                background: good ? T.successBg : '#f5f5f5',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, fontWeight: 700, color: good ? T.success : T.muted,
                userSelect: 'none',
              }}>
                {makeInitials(name)}
              </div>
              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, color: 'rgba(255,255,255,0.75)', fontWeight: 500 }}>
                  {[detail.age && `${detail.age} yrs`, detail.gender, detail.position].filter(Boolean).join(' · ')}
                </div>
                {detail.competition_level && (
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>
                    {detail.competition_level}
                  </div>
                )}
              </div>
              {/* Status */}
              <div style={{ flexShrink: 0 }}>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  background: good ? T.successBg : (status === 'inactive' ? T.attnBg : '#f5f5f5'),
                  color: good ? T.success : (status === 'inactive' ? T.attn : T.muted),
                  border: `1px solid ${good ? '#c5e8d2' : (status === 'inactive' ? '#fde5a0' : T.border)}`,
                  fontSize: 13, fontWeight: 600, padding: '5px 12px', borderRadius: 20,
                }}>
                  {good ? '● Active this week' : status === 'inactive' ? '○ No recent activity' : '○ Not in app'}
                </span>
              </div>
            </div>
          )}
        </header>

        {/* Loading shimmer */}
        {loading && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {[0,1,2,3,4,5].map(i => <ShimmerCard key={i} />)}
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 15, textAlign: 'center', marginTop: 40 }}>
            Couldn't load athlete data.
          </p>
        )}

        {/* Stats */}
        {!loading && detail && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Streak row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <StatCard
                label="Current streak"
                value={detail.current_streak}
                sub={detail.current_streak === 1 ? 'day' : 'days in a row'}
                icon="🔥"
                variant={detail.current_streak >= 7 ? 'success' : detail.current_streak > 0 ? 'default' : 'default'}
              />
              <StatCard
                label="Best streak"
                value={detail.best_streak}
                sub={detail.best_streak === 1 ? 'day' : 'days in a row'}
                icon="⭐"
                variant={detail.best_streak >= 14 ? 'success' : 'default'}
              />
            </div>

            {/* Activity bars */}
            <ActivityBar days7={detail.days_logged_7d} days30={detail.days_logged_30d} />

            {/* Total + last logged */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <StatCard
                label="Total days logged"
                value={detail.total_days_logged}
                sub="all time"
                icon="📊"
                variant={detail.total_days_logged > 0 ? 'default' : 'default'}
              />
              <StatCard
                label="Last logged"
                value={daysAgo(detail.last_logged_at) ?? '—'}
                sub={detail.last_logged_at ? fmtDate(detail.last_logged_at) : 'No logs yet'}
                icon="🕐"
                variant={detail.last_logged_at ? (daysAgo(detail.last_logged_at) === 'Today' || daysAgo(detail.last_logged_at) === 'Yesterday' ? 'success' : 'default') : 'default'}
              />
            </div>

            {/* Joined */}
            {detail.joined_at && (
              <div style={{
                fontSize: 13, color: 'rgba(255,255,255,0.3)',
                textAlign: 'center', marginTop: 4, fontStyle: 'italic',
              }}>
                Joined FuelUp {fmtJoined(detail.joined_at)}
              </div>
            )}
          </div>
        )}

        {/* Disclaimer */}
        {!loading && detail && (
          <p style={{
            fontSize: 12, color: 'rgba(255,255,255,0.25)',
            marginTop: 20, fontStyle: 'italic', lineHeight: 1.5,
          }}>
            Metrics reflect app logging activity only — not verified nutrition intake.
          </p>
        )}

      </div>
    </div>
  )
}
