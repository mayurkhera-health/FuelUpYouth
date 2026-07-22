import React from 'react'

const T = {
  emerald: '#0f2a1f',
  neon:    '#3dfc3d',
  orange:  '#ff9800',
  card:    '#ffffff',
  border:  '#dadad8',
}

// ── helpers ───────────────────────────────────────────────────────────────────

function logPct(t) {
  const above = t.current_week?.players_above_threshold ?? 0
  const total = t.roster_count ?? 1
  return Math.round((above / total) * 100)
}

function trendGlyph(cur, prior) {
  if (!cur || !prior) return null
  const diff = cur.players_above_threshold - prior.players_above_threshold
  if (diff > 0) return { glyph: '▲', color: T.neon,    label: `+${diff}` }
  if (diff < 0) return { glyph: '▼', color: T.orange,  label: `${diff}` }
  return               { glyph: '▬', color: '#aaa',    label: '0' }
}

function fmtDate(d) {
  if (!d) return null
  const iso = d.includes('T') ? d : d.replace(' ', 'T')
  const dt = new Date(iso)
  if (isNaN(dt)) return null
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function barColor(pct, threshold) {
  if (pct >= threshold)          return T.neon
  if (pct >= threshold * 0.6)   return T.orange
  return '#e91e63'
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

// ── sub-components ────────────────────────────────────────────────────────────

function ShimmerCard() {
  return (
    <div style={{ background: T.card, borderRadius: 12, padding: '20px 20px 16px',
                  border: `1px solid ${T.border}`, marginBottom: 10 }}>
      <div className="shimmer" style={{ height: 18, width: '50%', marginBottom: 10 }} />
      <div className="shimmer" style={{ height: 12, width: '30%', marginBottom: 14 }} />
      <div className="shimmer" style={{ height: 8, width: '100%' }} />
    </div>
  )
}

function CardProgressBar({ value, max, threshold }) {
  const filled = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const good   = filled >= threshold
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12, color: '#888', fontWeight: 600 }}>Logged this week</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: good ? T.emerald : T.orange }}>
          {value} / {max}
        </span>
      </div>
      <div style={{ height: 8, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${filled}%`,
          background: good ? T.neon : T.orange,
          borderRadius: 4, transition: 'width .4s ease',
        }} />
      </div>
    </div>
  )
}

function SummaryTiles({ teams }) {
  const totalRoster = teams.reduce((s, t) => s + (t.roster_count ?? 0), 0)
  const totalJoined = teams.reduce((s, t) => s + (t.joined_count ?? 0), 0)
  const totalLogged = teams.reduce((s, t) => s + (t.current_week?.players_above_threshold ?? 0), 0)
  const attnCount   = teams.filter(t => t.needs_attention).length
  const overallPct  = totalRoster > 0 ? Math.round((totalLogged / totalRoster) * 100) : 0

  const tiles = [
    { label: 'Total Athletes',   value: totalRoster, sub: `${totalJoined} in app`,      color: T.emerald },
    { label: 'Logged This Week', value: totalLogged, sub: `${overallPct}% of roster`,   color: totalLogged > 0 ? '#1a7a4a' : T.orange },
    { label: 'On Track',         value: teams.filter(t => !t.needs_attention).length,
                                 sub: `of ${teams.length} teams`,                        color: '#1a7a4a' },
    { label: 'Need Attention',   value: attnCount,   sub: attnCount > 0 ? 'Action required' : 'All clear',
                                                                                          color: attnCount > 0 ? T.orange : '#1a7a4a' },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
      {tiles.map(t => (
        <div key={t.label} style={{
          background: T.card, borderRadius: 12, padding: '14px 18px',
          border: `1px solid ${T.border}`, boxShadow: '0 1px 5px rgba(0,0,0,.04)',
        }}>
          <div style={{ fontSize: 26, fontWeight: 800, color: t.color, lineHeight: 1 }}>{t.value}</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#333', marginTop: 6 }}>{t.label}</div>
          <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>{t.sub}</div>
        </div>
      ))}
    </div>
  )
}

function EngagementChart({ teams }) {
  const threshold = teams[0]?.threshold_pct ?? 70
  return (
    <div style={{
      background: T.card, borderRadius: 14, padding: '18px 22px',
      border: `1px solid ${T.border}`, boxShadow: '0 1px 6px rgba(0,0,0,.05)',
      marginBottom: 10,
    }}>
      <div style={{ fontWeight: 700, fontSize: 15, color: T.emerald, marginBottom: 2 }}>Team Engagement</div>
      <div style={{ fontSize: 12, color: '#aaa', marginBottom: 14 }}>
        % of athletes who logged above the weekly threshold
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {teams.map(t => {
          const p   = logPct(t)
          const col = barColor(p, threshold)
          return (
            <div key={t.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: T.emerald }}>{t.name}</span>
                <span style={{ fontWeight: 700, fontSize: 13, color: col }}>
                  {p}%{' '}
                  <span style={{ color: '#aaa', fontWeight: 500 }}>
                    ({t.current_week?.players_above_threshold ?? 0}/{t.roster_count ?? 0})
                  </span>
                </span>
              </div>
              <div style={{ position: 'relative', height: 8, background: '#f0f0f0', borderRadius: 4 }}>
                <div style={{
                  position: 'absolute', left: `${threshold}%`, top: -4, bottom: -4,
                  width: 2, background: '#ccc', borderRadius: 1, zIndex: 2,
                }} />
                <div style={{
                  position: 'absolute', left: 0, top: 0, bottom: 0,
                  width: `${Math.min(p, 100)}%`,
                  background: col, borderRadius: 4, transition: 'width .5s ease',
                }} />
              </div>
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 10 }}>
        <div style={{ width: 2, height: 12, background: '#ccc', borderRadius: 1 }} />
        <span style={{ fontSize: 12, color: '#aaa' }}>Target threshold: {threshold}%</span>
      </div>
    </div>
  )
}

function WeekOverWeekTable({ teams, snap }) {
  const th = { fontSize: 11, fontWeight: 700, color: '#aaa', textTransform: 'uppercase',
               letterSpacing: '.05em', padding: '0 0 8px', textAlign: 'left' }
  const td = { padding: '10px 0', borderTop: `1px solid ${T.border}`, verticalAlign: 'middle' }
  return (
    <div style={{
      background: T.card, borderRadius: 14, padding: '18px 22px',
      border: `1px solid ${T.border}`, boxShadow: '0 1px 6px rgba(0,0,0,.05)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: T.emerald }}>Week-over-Week</div>
          <div style={{ fontSize: 12, color: '#aaa', marginTop: 2 }}>Logging rate vs. prior week</div>
        </div>
        {snap && <div style={{ fontSize: 12, color: '#ccc' }}>Snapshot: {fmtDate(snap)}</div>}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={th}>Team</th>
            <th style={{ ...th, textAlign: 'center' }}>Prior Week</th>
            <th style={{ ...th, textAlign: 'center' }}>This Week</th>
            <th style={{ ...th, textAlign: 'right' }}>Change</th>
          </tr>
        </thead>
        <tbody>
          {teams.map(t => {
            const cur   = logPct(t)
            const priorAbove = t.prior_week?.players_above_threshold ?? 0
            const priorTotal = t.roster_count ?? 1
            const prior = t.prior_week ? Math.round((priorAbove / priorTotal) * 100) : null
            const diff  = prior !== null ? cur - prior : null
            const trend = diff === null ? { text: '—', color: '#aaa' }
                        : diff > 0 ? { text: `▲ +${diff}%`, color: '#1a7a4a' }
                        : diff < 0 ? { text: `▼ ${diff}%`, color: T.orange }
                        :             { text: '▬ 0%', color: '#aaa' }
            return (
              <tr key={t.id}>
                <td style={{ ...td, fontWeight: 600, fontSize: 15, color: T.emerald }}>
                  {t.name}
                  {t.needs_attention && (
                    <span style={{ marginLeft: 8, fontSize: 11, color: T.orange, fontWeight: 700 }}>
                      ⚑
                    </span>
                  )}
                </td>
                <td style={{ ...td, textAlign: 'center', color: '#888', fontSize: 15 }}>
                  {prior !== null ? `${prior}%` : '—'}
                </td>
                <td style={{ ...td, textAlign: 'center', fontWeight: 700, fontSize: 15,
                             color: barColor(cur, t.threshold_pct ?? 70) }}>
                  {cur}%
                </td>
                <td style={{ ...td, textAlign: 'right', fontWeight: 700, fontSize: 14,
                             color: trend.color }}>
                  {trend.text}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── main ──────────────────────────────────────────────────────────────────────

const s = {
  page: {
    minHeight: '100vh',
    backgroundImage: [
      'radial-gradient(ellipse 75% 50% at 78% -5%, rgba(61,252,61,0.09) 0%, transparent 55%)',
      'radial-gradient(circle, rgba(255,255,255,0.045) 1px, transparent 1px)',
    ].join(', '),
    backgroundSize: 'auto, 30px 30px',
  },
  wrap:     { padding: '20px 32px', maxWidth: 960, margin: '0 auto' },
  header:   { marginBottom: 14 },
  hi:       { fontSize: 13, color: 'rgba(255,255,255,0.45)', fontWeight: 500, marginBottom: 2 },
  title:    { fontWeight: 800, fontSize: 28, color: '#fff', lineHeight: 1.1 },
  subtitle: { fontSize: 14, color: 'rgba(255,255,255,0.55)', marginTop: 4, fontWeight: 500 },

  sectionLabel: { fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.3)',
                  textTransform: 'uppercase', letterSpacing: '.08em',
                  marginTop: 20, marginBottom: 8 },

  card: (attention) => ({
    background: T.card, borderRadius: 12, padding: '14px 20px 12px', marginBottom: 8,
    cursor: 'pointer',
    border: `1px solid ${attention ? T.orange : 'rgba(255,255,255,0.08)'}`,
    borderLeft: `4px solid ${attention ? T.orange : T.neon}`,
    boxShadow: '0 1px 5px rgba(0,0,0,.07)',
    transition: 'box-shadow .15s',
  }),
  cardTop:   { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  teamName:  { fontWeight: 700, fontSize: 17, color: T.emerald },
  cardMeta:  { fontSize: 13, color: '#aaa', marginTop: 2, fontWeight: 600 },
  rightCol:  { display: 'flex', alignItems: 'center', gap: 8 },
  trend:     (color) => ({ fontSize: 13, fontWeight: 700, color }),
  chevron:   { color: T.border, fontSize: 18 },
  statusRow: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 },
  statusDot: (good) => ({
    width: 7, height: 7, borderRadius: '50%',
    background: good ? T.neon : T.orange, flexShrink: 0,
  }),
  statusText: (good) => ({ fontSize: 13, fontWeight: 600, color: good ? '#1a7a4a' : '#a35c00' }),
}

export default function TeamSelector({ teamsData, onSelect, loading, coachName }) {
  const { generated_at, season, teams = [] } = teamsData || {}

  return (
    <div style={s.page}>
      <div style={s.wrap}>

        {/* Greeting */}
        <div style={s.header}>
          <div style={s.hi}>{greeting()}{coachName ? `, ${coachName.split(' ')[0]}` : ''} 👋</div>
          <div style={s.title}>Dashboard</div>
          <div style={s.subtitle}>{season || 'Current season'} · Engagement overview</div>
        </div>

        {/* Summary tiles */}
        {!loading && teams.length > 0 && <SummaryTiles teams={teams} />}
        {loading && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 24 }}>
            {[0,1,2,3].map(i => (
              <div key={i} style={{ background: T.card, borderRadius: 14, padding: '20px 22px',
                                    border: `1px solid ${T.border}` }}>
                <div className="shimmer" style={{ height: 34, width: '40%', marginBottom: 10 }} />
                <div className="shimmer" style={{ height: 14, width: '70%' }} />
              </div>
            ))}
          </div>
        )}

        {/* Team cards */}
        <div style={s.sectionLabel}>Your Teams</div>
        {loading && [0, 1].map(i => <ShimmerCard key={i} />)}
        {!loading && teams.map(t => {
          const above   = t.current_week?.players_above_threshold ?? 0
          const total   = t.roster_count ?? t.joined_count ?? 0
          const fillPct = total > 0 ? Math.round((above / total) * 100) : 0
          const good    = fillPct >= (t.threshold_pct ?? 70)
          const trend   = trendGlyph(t.current_week, t.prior_week)
          return (
            <div key={t.id} style={s.card(t.needs_attention)}
                 onClick={() => onSelect(t)} role="button" tabIndex={0}
                 onKeyDown={e => e.key === 'Enter' && onSelect(t)}>
              <div style={s.cardTop}>
                <div>
                  <div style={s.teamName}>{t.name}</div>
                  <div style={s.cardMeta}>{total} athlete{total !== 1 ? 's' : ''}</div>
                </div>
                <div style={s.rightCol}>
                  {trend && <span style={s.trend(trend.color)}>{trend.glyph} {trend.label}</span>}
                  <span style={s.chevron}>›</span>
                </div>
              </div>
              <CardProgressBar value={above} max={total} threshold={t.threshold_pct ?? 70} />
              <div style={s.statusRow}>
                <div style={s.statusDot(good)} />
                <span style={s.statusText(good)}>
                  {good ? `${fillPct}% — On track`
                   : t.needs_attention ? `${fillPct}% — Needs attention`
                   : `${fillPct}% — Below target`}
                </span>
              </div>
            </div>
          )
        })}
        {!loading && teams.length === 0 && (
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 14, marginTop: 32, textAlign: 'center' }}>
            No teams assigned to your account.
          </p>
        )}

        {/* Analytics */}
        {!loading && teams.length > 0 && (
          <>
            <div style={s.sectionLabel}>Analytics</div>
            <EngagementChart teams={teams} />
            <WeekOverWeekTable teams={teams} snap={generated_at} />
          </>
        )}

      </div>
    </div>
  )
}
