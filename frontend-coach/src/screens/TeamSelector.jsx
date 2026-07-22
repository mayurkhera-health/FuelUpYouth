import React from 'react'

const T = {
  emerald: '#0f2a1f',
  neon:    '#3dfc3d',
  orange:  '#ff9800',
  surface: '#faf9f7',
  card:    '#ffffff',
  border:  '#dadad8',
}

// ── helpers ──────────────────────────────────────────────────────────────────

function pct(above, total) {
  if (!above || !total) return 0
  return Math.round((above / total) * 100)
}

function trendGlyph(cur, prior) {
  if (!cur || !prior) return null
  const diff = cur.players_above_threshold - prior.players_above_threshold
  if (diff > 0) return { glyph: '▲', color: T.neon, label: `+${diff}` }
  if (diff < 0) return { glyph: '▼', color: T.orange, label: `${diff}` }
  return { glyph: '▬', color: '#aaa', label: '0' }
}

function fmtDate(d) {
  if (!d) return null
  const iso = d.includes('T') ? d : d.replace(' ', 'T')
  const dt = new Date(iso)
  if (isNaN(dt)) return null
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// ── sub-components ────────────────────────────────────────────────────────────

function ProgressBar({ value, max, threshold }) {
  const filled = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const good   = filled >= threshold
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: '#888', fontWeight: 500 }}>Logged this week</span>
        <span style={{ fontSize: 12, fontWeight: 700,
          color: good ? T.emerald : T.orange }}>
          {value} / {max}
        </span>
      </div>
      <div style={{ height: 8, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${filled}%`,
          background: good ? T.neon : T.orange,
          borderRadius: 4,
          transition: 'width .4s ease',
        }} />
      </div>
    </div>
  )
}

function CircularGauge({ pct: value, size = 112 }) {
  const r   = 42
  const circ = 2 * Math.PI * r
  const dash = (Math.min(value, 100) / 100) * circ
  const good = value >= 70
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke={T.border} strokeWidth="9" />
      <circle cx="50" cy="50" r={r} fill="none"
        stroke={good ? T.neon : T.orange} strokeWidth="9"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        transform="rotate(-90 50 50)" />
      <text x="50" y="47" textAnchor="middle" fontSize="18" fontWeight="800"
        fill={T.emerald} fontFamily="Hanken Grotesk, sans-serif">
        {Math.round(value)}%
      </text>
      <text x="50" y="62" textAnchor="middle" fontSize="9" fill="#888"
        fontFamily="Hanken Grotesk, sans-serif">
        OVERALL
      </text>
    </svg>
  )
}

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

// ── main component ────────────────────────────────────────────────────────────

const s = {
  wrap:  { padding: '24px 20px', maxWidth: 680, margin: '0 auto' },
  header: { marginBottom: 24 },
  title:  { fontWeight: 800, fontSize: 26, color: '#fff', lineHeight: 1.1 },
  subtitle: { fontSize: 14, color: 'rgba(255,255,255,0.5)', marginTop: 6 },

  // Team card
  card: (attention) => ({
    background: T.card,
    borderRadius: 12,
    padding: '18px 20px 16px',
    marginBottom: 10,
    cursor: 'pointer',
    border: `1px solid ${attention ? T.orange : 'rgba(255,255,255,0.08)'}`,
    borderLeft: `4px solid ${attention ? T.orange : T.neon}`,
    boxShadow: '0 1px 4px rgba(0,0,0,.05)',
    transition: 'box-shadow .15s, transform .1s',
  }),
  cardTop:   { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' },
  teamName:  { fontWeight: 700, fontSize: 17, color: T.emerald },
  attnBadge: { fontSize: 11, fontWeight: 700, color: T.orange,
               textTransform: 'uppercase', letterSpacing: '.05em' },
  rightCol:  { display: 'flex', alignItems: 'center', gap: 6 },
  trend:     (color) => ({ fontSize: 13, fontWeight: 700, color }),
  chevron:   { color: T.border, fontSize: 18 },
  cardMeta:  { fontSize: 12, color: '#aaa', marginTop: 3 },

  statusRow: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 12 },
  statusDot: (good) => ({
    width: 7, height: 7, borderRadius: '50%',
    background: good ? T.neon : T.orange, flexShrink: 0,
  }),
  statusText: (good) => ({ fontSize: 12, fontWeight: 600,
    color: good ? '#1a7a4a' : '#a35c00' }),

  // Season overview
  overview: {
    background: T.emerald, borderRadius: 14, padding: '24px 20px',
    marginTop: 28, color: '#fff',
  },
  ovTitle: { fontWeight: 700, fontSize: 16, marginBottom: 4 },
  ovSub:   { fontSize: 13, color: 'rgba(255,255,255,0.55)', marginBottom: 20 },
  ovBody:  { display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' },
  ovGrid:  { flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12,
             minWidth: 160 },
  stat:    { background: 'rgba(255,255,255,0.07)', borderRadius: 10, padding: '12px 14px' },
  statVal: { fontWeight: 800, fontSize: 22, color: T.neon, lineHeight: 1 },
  statLbl: { fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 4,
             textTransform: 'uppercase', letterSpacing: '.04em' },

  snap: { fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 16 },
}

export default function TeamSelector({ teamsData, onSelect, loading }) {
  const { generated_at, season, teams = [] } = teamsData || {}

  // Aggregate stats for Season Overview
  const totalRoster  = teams.reduce((s, t) => s + (t.roster_count ?? 0), 0)
  const totalAbove   = teams.reduce((s, t) =>
    s + (t.current_week ? t.current_week.players_above_threshold : 0), 0)
  const totalJoined  = teams.reduce((s, t) => s + (t.joined_count ?? 0), 0)
  const attentionCt  = teams.filter(t => t.needs_attention).length
  const overallPct   = totalRoster > 0 ? (totalAbove / totalRoster) * 100 : 0

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={s.title}>My Teams</div>
        <div style={s.subtitle}>
          {season || 'Current season'} · Monitoring engagement trends
        </div>
      </div>

      {loading && [0, 1].map(i => <ShimmerCard key={i} />)}

      {!loading && teams.map(t => {
        const above = t.current_week ? t.current_week.players_above_threshold : 0
        const total = t.roster_count ?? t.joined_count ?? 0
        const fillPct = pct(above, total)
        const good    = fillPct >= (t.threshold_pct ?? 70)
        const trend   = trendGlyph(t.current_week, t.prior_week)

        return (
          <div
            key={t.id}
            style={s.card(t.needs_attention)}
            onClick={() => onSelect(t)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && onSelect(t)}
          >
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

            <ProgressBar value={above} max={total} threshold={t.threshold_pct ?? 70} />

            <div style={s.statusRow}>
              <div style={s.statusDot(good)} />
              <span style={s.statusText(good)}>
                {good
                  ? `${fillPct}% — On track`
                  : t.needs_attention
                    ? `${fillPct}% — Needs attention`
                    : `${fillPct}% — Below target`}
              </span>
            </div>
          </div>
        )
      })}

      {!loading && teams.length === 0 && (
        <p style={{ color: '#aaa', fontSize: 14, marginTop: 32, textAlign: 'center' }}>
          No teams assigned to your account.
        </p>
      )}

      {/* Season Overview */}
      {!loading && teams.length > 0 && (
        <div style={s.overview}>
          <div style={s.ovTitle}>Season Overview</div>
          <div style={s.ovSub}>Aggregate across all your teams</div>
          <div style={s.ovBody}>
            <CircularGauge pct={overallPct} />
            <div style={s.ovGrid}>
              <div style={s.stat}>
                <div style={s.statVal}>{totalRoster}</div>
                <div style={s.statLbl}>Total athletes</div>
              </div>
              <div style={s.stat}>
                <div style={s.statVal}>{totalAbove}</div>
                <div style={s.statLbl}>Logged this week</div>
              </div>
              <div style={s.stat}>
                <div style={s.statVal}>{attentionCt}</div>
                <div style={s.statLbl}>Need attention</div>
              </div>
              <div style={s.stat}>
                <div style={s.statVal}>{totalJoined}</div>
                <div style={s.statLbl}>App joined</div>
              </div>
            </div>
          </div>
          {generated_at && (
            <div style={s.snap}>Snapshot: {fmtDate(generated_at)}</div>
          )}
        </div>
      )}
    </div>
  )
}
