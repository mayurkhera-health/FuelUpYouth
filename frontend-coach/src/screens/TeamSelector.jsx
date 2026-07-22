import React from 'react'

const T = {
  bg:        '#123826',
  neon:      '#31E65A',
  primary:   '#173226',
  muted:     '#6D7A72',
  surface:   '#FFFFFF',
  border:    '#DDE5E0',
  attention: '#F59E0B',
  attnBg:    '#FFF7E6',
  attn:      '#B86600',
  success:   '#1E9E57',
  successBg: '#EAF7EF',
}

// ── helpers (no business logic changed) ──────────────────────────────────────

function logPct(t) {
  const above = t.current_week?.players_above_threshold ?? 0
  const total = t.roster_count ?? 1
  return Math.round((above / total) * 100)
}

function trendGlyph(cur, prior) {
  if (!cur || !prior) return null
  const diff = cur.players_above_threshold - prior.players_above_threshold
  if (diff > 0) return { glyph: '▲', color: T.success,   label: `+${diff}` }
  if (diff < 0) return { glyph: '▼', color: T.attention, label: `${diff}` }
  return               { glyph: '▬', color: T.muted,     label: '0' }
}

function fmtDate(d) {
  if (!d) return null
  const iso = d.includes('T') ? d : d.replace(' ', 'T')
  const dt = new Date(iso)
  if (isNaN(dt)) return null
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function barColor(pct, threshold) {
  if (pct >= threshold)        return T.neon
  if (pct >= threshold * 0.6) return T.attention
  return '#e91e63'
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

// ── StatusPill ────────────────────────────────────────────────────────────────

function StatusPill({ good, attention, noData }) {
  if (noData) {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        background: '#f5f5f5', color: T.muted,
        fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 20,
        border: `1px solid ${T.border}`,
      }}>
        <span>● No data yet</span>
      </span>
    )
  }
  if (good) {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        background: T.successBg, color: T.success,
        fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 20,
        border: '1px solid #c5e8d2',
      }}>
        ● On track
      </span>
    )
  }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: T.attnBg, color: T.attention,
      fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 20,
      border: '1px solid #fde5a0',
    }}>
      ● Needs attention
    </span>
  )
}

// ── ProgressBar ───────────────────────────────────────────────────────────────

function ProgressBar({ value, max, threshold }) {
  const filled = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const good   = filled >= threshold
  return (
    <div style={{ height: 8, background: T.border, borderRadius: 4, overflow: 'hidden', marginTop: 10 }}>
      <div style={{
        height: '100%',
        width: `${filled}%`,
        background: good ? T.neon : T.attention,
        borderRadius: 4,
        transition: 'width .4s ease',
      }} />
    </div>
  )
}

// ── MetricCard ────────────────────────────────────────────────────────────────

function MetricCard({ label, value, sub, icon, variant = 'default' }) {
  const styles = {
    default:   { numColor: T.primary,   bg: T.surface,   border: T.border,    subColor: T.muted },
    success:   { numColor: T.success,   bg: T.successBg, border: '#c5e8d2',   subColor: T.muted },
    attention: { numColor: T.attention, bg: T.attnBg,    border: '#fde5a0',   subColor: T.attention },
  }
  const v = styles[variant] || styles.default

  return (
    <div style={{
      background: v.bg,
      border: `1px solid ${v.border}`,
      borderRadius: 16,
      padding: '16px 20px',
      minHeight: 118,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      boxShadow: '0 1px 4px rgba(0,0,0,.05)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Ghost watermark */}
      <div style={{
        position: 'absolute', right: 10, bottom: 4,
        fontSize: 80, fontWeight: 800, lineHeight: 1,
        color: v.numColor, opacity: 0.07,
        userSelect: 'none', pointerEvents: 'none',
      }}>{icon}</div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ fontSize: 34, fontWeight: 700, color: v.numColor, lineHeight: 1 }}>
          {value}
        </div>
      </div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 600, color: T.primary, marginBottom: 2 }}>{label}</div>
        <div style={{ fontSize: 12, color: v.subColor, fontWeight: variant === 'attention' ? 600 : 400 }}>
          {sub}
        </div>
      </div>
    </div>
  )
}

// ── MetricGrid ────────────────────────────────────────────────────────────────

function MetricGrid({ teams }) {
  const totalRoster = teams.reduce((s, t) => s + (t.roster_count ?? 0), 0)
  const totalJoined = teams.reduce((s, t) => s + (t.joined_count ?? 0), 0)
  const totalLogged = teams.reduce((s, t) => s + (t.current_week?.players_above_threshold ?? 0), 0)
  const attnCount   = teams.filter(t => t.needs_attention).length
  const onTrack     = teams.filter(t => !t.needs_attention).length
  const overallPct  = totalRoster > 0 ? Math.round((totalLogged / totalRoster) * 100) : 0

  return (
    <div className="metric-grid">
      <MetricCard
        label="Rostered athletes"
        value={totalRoster}
        sub={`${totalJoined} using the app`}
        icon="◉"
        variant="default"
      />
      <MetricCard
        label="Logged this week"
        value={totalLogged}
        sub={`${overallPct}% of roster`}
        icon="☑"
        variant={totalLogged > 0 ? 'success' : 'default'}
      />
      <MetricCard
        label="On track"
        value={onTrack}
        sub={`Across ${teams.length} team${teams.length !== 1 ? 's' : ''}`}
        icon="✓"
        variant={onTrack > 0 ? 'success' : 'default'}
      />
      <MetricCard
        label="Need attention"
        value={attnCount}
        sub={attnCount > 0 ? 'Review teams →' : 'All teams on track'}
        icon="⚑"
        variant={attnCount > 0 ? 'attention' : 'default'}
      />
    </div>
  )
}

function LoadingMetricGrid() {
  return (
    <div className="metric-grid">
      {[0,1,2,3].map(i => (
        <div key={i} style={{
          background: T.surface, borderRadius: 16, padding: '16px 20px',
          border: `1px solid ${T.border}`, minHeight: 118,
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        }}>
          <div className="shimmer" style={{ height: 34, width: '45%', borderRadius: 6 }} />
          <div>
            <div className="shimmer" style={{ height: 15, width: '70%', borderRadius: 4, marginBottom: 6 }} />
            <div className="shimmer" style={{ height: 12, width: '50%', borderRadius: 4 }} />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── TeamSummaryCard ───────────────────────────────────────────────────────────

function cardInsight(above, total, fillPct, threshold, good) {
  if (total === 0) return 'No athletes on roster yet.'
  if (above === 0) return 'No athletes logged activity this week — consider following up.'
  if (above === total) return `All ${total} athletes logged this week. Great engagement.`
  if (good) return `${above} of ${total} athletes logged — team is on track for the ${threshold}% target.`
  const missing = total - above
  return `${missing} athlete${missing !== 1 ? 's' : ''} haven't logged yet — below the ${threshold}% target.`
}

function TeamSummaryCard({ team: t, onSelect }) {
  const above     = t.current_week?.players_above_threshold ?? 0
  const total     = t.roster_count ?? t.joined_count ?? 0
  const fillPct   = total > 0 ? Math.round((above / total) * 100) : 0
  const threshold = t.threshold_pct ?? 70
  const good      = fillPct >= threshold
  const trend     = trendGlyph(t.current_week, t.prior_week)
  const hasData   = total > 0
  const insight   = cardInsight(above, total, fillPct, threshold, good)

  return (
    <div
      className="team-card"
      onClick={() => onSelect(t)}
      role="button"
      tabIndex={0}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && onSelect(t)}
      aria-label={`${t.name}: ${good ? 'On track' : 'Needs attention'}. ${above} of ${total} athletes logged this week. Open team detail.`}
    >
      {/* Status gradient wash + rail */}
      <div style={{
        position: 'absolute', left: 0, top: 0, right: 0, bottom: 0,
        background: hasData
          ? good
            ? 'linear-gradient(to right, rgba(49,230,90,0.07) 0%, transparent 44%)'
            : 'linear-gradient(to right, rgba(245,158,11,0.09) 0%, transparent 44%)'
          : 'none',
        borderRadius: 16,
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 6,
        background: hasData ? (good ? T.neon : T.attention) : T.border,
      }} />

      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ fontWeight: 700, fontSize: 20, color: T.primary, margin: 0, lineHeight: 1.25,
                       whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {t.name}
          </h3>
          <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>
            {total} athlete{total !== 1 ? 's' : ''}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {trend && (
            <span style={{ fontSize: 12, fontWeight: 700, color: trend.color }}>
              {trend.glyph} {trend.label}
            </span>
          )}
          <StatusPill good={good} attention={t.needs_attention} noData={!hasData} />
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            fontSize: 13, fontWeight: 700, color: T.primary,
            background: T.neon, padding: '6px 13px', borderRadius: 8,
          }}>
            View team →
          </span>
        </div>
      </div>

      {/* Metrics + progress */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px 20px', fontSize: 13, color: T.muted, marginTop: 10 }}>
        <span>
          <strong style={{ color: T.primary, fontWeight: 700 }}>{above}</strong>
          {' '}of {total} logged
        </span>
        <span>
          <strong style={{ color: hasData ? (good ? T.success : T.attention) : T.muted, fontWeight: 700 }}>
            {fillPct}%
          </strong>
          {' '}participation
        </span>
      </div>
      <ProgressBar value={above} max={total} threshold={threshold} />

      {/* Insight line */}
      <div style={{
        marginTop: 9, fontSize: 12, color: good ? T.success : T.attn,
        fontWeight: 500, fontStyle: 'italic',
      }}>
        {insight}
      </div>
    </div>
  )
}

function LoadingTeamCard() {
  return (
    <div style={{
      background: T.surface, borderRadius: 16, border: `1px solid ${T.border}`,
      padding: '20px 28px 18px 34px', marginBottom: 16, position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 6, background: T.border }} />
      <div className="shimmer" style={{ height: 20, width: '40%', marginBottom: 8, borderRadius: 4 }} />
      <div className="shimmer" style={{ height: 12, width: '22%', marginBottom: 14, borderRadius: 4 }} />
      <div className="shimmer" style={{ height: 8, width: '100%', borderRadius: 4 }} />
    </div>
  )
}

// ── EngagementChart ───────────────────────────────────────────────────────────

function EngagementChart({ teams }) {
  const threshold = teams[0]?.threshold_pct ?? 70
  return (
    <div style={{
      background: T.surface, borderRadius: 16, padding: '20px 24px',
      border: `1px solid ${T.border}`, boxShadow: '0 1px 4px rgba(0,0,0,.05)',
      marginBottom: 12,
    }}>
      <div style={{ fontWeight: 700, fontSize: 15, color: T.primary, marginBottom: 2 }}>
        Team Engagement
      </div>
      <div style={{ fontSize: 12, color: T.muted, marginBottom: 16 }}>
        % of athletes who logged above the weekly threshold
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {teams.map(t => {
          const p   = logPct(t)
          const col = barColor(p, threshold)
          return (
            <div key={t.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: T.primary }}>{t.name}</span>
                <span style={{ fontWeight: 700, fontSize: 13, color: col }}>
                  {p}%{' '}
                  <span style={{ color: T.muted, fontWeight: 500 }}>
                    ({t.current_week?.players_above_threshold ?? 0}/{t.roster_count ?? 0})
                  </span>
                </span>
              </div>
              <div style={{ position: 'relative', height: 8, background: T.border, borderRadius: 4 }}>
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 12 }}>
        <div style={{ width: 2, height: 12, background: '#ccc', borderRadius: 1 }} />
        <span style={{ fontSize: 11, color: T.muted }}>Target threshold: {threshold}%</span>
      </div>
    </div>
  )
}

// ── WeekOverWeekTable ─────────────────────────────────────────────────────────

function WeekOverWeekTable({ teams, snap }) {
  const th = { fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase',
               letterSpacing: '.05em', padding: '0 0 8px', textAlign: 'left' }
  const td = { padding: '10px 0', borderTop: `1px solid ${T.border}`, verticalAlign: 'middle' }
  return (
    <div style={{
      background: T.surface, borderRadius: 16, padding: '20px 24px',
      border: `1px solid ${T.border}`, boxShadow: '0 1px 4px rgba(0,0,0,.05)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: T.primary }}>Week-over-Week</div>
          <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>Logging rate vs. prior week</div>
        </div>
        {snap && <div style={{ fontSize: 11, color: '#ccc' }}>Snapshot: {fmtDate(snap)}</div>}
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
            const cur        = logPct(t)
            const priorAbove = t.prior_week?.players_above_threshold ?? 0
            const priorTotal = t.roster_count ?? 1
            const prior      = t.prior_week ? Math.round((priorAbove / priorTotal) * 100) : null
            const diff       = prior !== null ? cur - prior : null
            const trend      = diff === null ? { text: '—', color: T.muted }
                             : diff > 0 ? { text: `▲ +${diff}%`, color: T.success }
                             : diff < 0 ? { text: `▼ ${diff}%`, color: T.attention }
                             :             { text: '▬ 0%',       color: T.muted }
            return (
              <tr key={t.id}>
                <td style={{ ...td, fontWeight: 600, fontSize: 13, color: T.primary }}>
                  {t.name}
                  {t.needs_attention && (
                    <span style={{ marginLeft: 6, fontSize: 11, color: T.attention, fontWeight: 700 }}>⚑</span>
                  )}
                </td>
                <td style={{ ...td, textAlign: 'center', color: T.muted, fontSize: 13 }}>
                  {prior !== null ? `${prior}%` : '—'}
                </td>
                <td style={{ ...td, textAlign: 'center', fontWeight: 700, fontSize: 13,
                             color: barColor(cur, t.threshold_pct ?? 70) }}>
                  {cur}%
                </td>
                <td style={{ ...td, textAlign: 'right', fontWeight: 700, fontSize: 13, color: trend.color }}>
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

const sectionHeading = {
  fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.35)',
  textTransform: 'uppercase', letterSpacing: '.08em',
  marginBottom: 14, marginTop: 0,
}

export default function TeamSelector({ teamsData, onSelect, loading, coachName }) {
  const { generated_at, season, teams = [] } = teamsData || {}

  return (
    <div style={{
      minHeight: '100vh',
      background: T.bg,
      backgroundImage: [
        'radial-gradient(ellipse 75% 50% at 78% -5%, rgba(49,230,90,0.06) 0%, transparent 55%)',
        'radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)',
      ].join(', '),
      backgroundSize: 'auto, 32px 32px',
    }}>
      <div className="dashboard-wrap">

        {/* Header — H1 for accessibility */}
        <header style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 15, color: 'rgba(255,255,255,0.5)', fontWeight: 500, marginBottom: 4 }}>
            {greeting()}{coachName ? `, ${coachName.split(' ')[0]}` : ''}
          </div>
          <h1 style={{
            fontWeight: 700, fontSize: 40, color: '#fff', lineHeight: 1.05,
            margin: 0, letterSpacing: '-.01em',
          }}>
            Dashboard
          </h1>
          <div style={{ fontSize: 15, color: 'rgba(255,255,255,0.45)', marginTop: 6, fontWeight: 500 }}>
            {season || 'Current season'} · Engagement overview
          </div>
        </header>

        {/* Metric grid */}
        {loading ? <LoadingMetricGrid /> : teams.length > 0 ? <MetricGrid teams={teams} /> : null}

        {/* Teams section — H2 for accessibility */}
        {(teams.length > 0 || loading) && (
          <section>
            <h2 style={{ ...sectionHeading, marginTop: 4 }}>Your Teams</h2>
            {loading && [0, 1].map(i => <LoadingTeamCard key={i} />)}
            {!loading && teams.map(t => (
              <TeamSummaryCard key={t.id} team={t} onSelect={onSelect} />
            ))}
          </section>
        )}

        {!loading && teams.length === 0 && (
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 14, marginTop: 48, textAlign: 'center' }}>
            No teams assigned to your account.
          </p>
        )}

        {/* Analytics */}
        {!loading && teams.length > 0 && (
          <section style={{ marginTop: 32 }}>
            <h2 style={sectionHeading}>Analytics</h2>
            <EngagementChart teams={teams} />
            <WeekOverWeekTable teams={teams} snap={generated_at} />
          </section>
        )}

      </div>
    </div>
  )
}
