import React from 'react'

const T = {
  emerald: '#0f2a1f',
  neon:    '#3dfc3d',
  orange:  '#ff9800',
  red:     '#e91e63',
  border:  '#dadad8',
}

// ── helpers ───────────────────────────────────────────────────────────────────

function logPct(team) {
  const above = team.current_week?.players_above_threshold ?? 0
  const total = team.roster_count ?? 1
  return Math.round((above / total) * 100)
}

function priorPct(team) {
  const above = team.prior_week?.players_above_threshold ?? 0
  const total = team.roster_count ?? 1
  return Math.round((above / total) * 100)
}

function barColor(pct, threshold) {
  if (pct >= threshold) return T.neon
  if (pct >= threshold * 0.6) return T.orange
  return T.red
}

function trendLabel(cur, prior) {
  const diff = cur - prior
  if (diff > 0) return { text: `▲ +${diff}%`, color: '#1a7a4a' }
  if (diff < 0) return { text: `▼ ${diff}%`,  color: T.orange }
  return           { text: `▬ 0%`,            color: '#aaa' }
}

// ── shared card shell ─────────────────────────────────────────────────────────

function Card({ title, subtitle, children, style }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 16, padding: '24px 28px',
      border: `1px solid ${T.border}`,
      boxShadow: '0 2px 10px rgba(0,0,0,.07)',
      ...style,
    }}>
      {title && (
        <div style={{ marginBottom: subtitle ? 2 : 18 }}>
          <div style={{ fontWeight: 700, fontSize: 17, color: T.emerald }}>{title}</div>
          {subtitle && <div style={{ fontSize: 13, color: '#aaa', marginTop: 2, marginBottom: 18 }}>{subtitle}</div>}
        </div>
      )}
      {children}
    </div>
  )
}

// ── Section 1: Summary stat tiles ─────────────────────────────────────────────

function SummaryTiles({ teams }) {
  const totalAthletes = teams.reduce((s, t) => s + (t.roster_count ?? 0), 0)
  const totalJoined   = teams.reduce((s, t) => s + (t.joined_count ?? 0), 0)
  const totalLogged   = teams.reduce((s, t) => s + (t.current_week?.players_above_threshold ?? 0), 0)
  const attnCount     = teams.filter(t => t.needs_attention).length

  const tiles = [
    { label: 'Total Athletes',        value: totalAthletes, color: T.emerald, icon: '◉' },
    { label: 'App Joined',            value: totalJoined,   color: '#1a7a4a',  icon: '✓' },
    { label: 'Logged This Week',      value: totalLogged,   color: T.emerald,  icon: '▤' },
    { label: 'Teams Need Attention',  value: attnCount,     color: attnCount > 0 ? T.orange : '#1a7a4a', icon: '⚑' },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
      {tiles.map(t => (
        <div key={t.label} style={{
          background: '#fff', borderRadius: 14, padding: '20px 22px',
          border: `1px solid ${T.border}`,
          boxShadow: '0 1px 6px rgba(0,0,0,.05)',
        }}>
          <div style={{ fontSize: 22, color: t.color, marginBottom: 8 }}>{t.icon}</div>
          <div style={{ fontSize: 34, fontWeight: 800, color: t.color, lineHeight: 1 }}>{t.value}</div>
          <div style={{ fontSize: 13, color: '#888', fontWeight: 600, marginTop: 6 }}>{t.label}</div>
        </div>
      ))}
    </div>
  )
}

// ── Section 2: Horizontal bar chart ──────────────────────────────────────────

function EngagementBarChart({ teams }) {
  const maxPct = 100
  const threshold = teams[0]?.threshold_pct ?? 70

  return (
    <Card title="Team Engagement" subtitle="% of athletes who logged above the weekly threshold">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        {teams.map(t => {
          const pct   = logPct(t)
          const color = barColor(pct, threshold)
          const above = t.current_week?.players_above_threshold ?? 0
          const total = t.roster_count ?? 0
          return (
            <div key={t.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
                <span style={{ fontWeight: 600, fontSize: 15, color: T.emerald }}>{t.name}</span>
                <span style={{ fontWeight: 700, fontSize: 15, color }}>
                  {pct}% <span style={{ color: '#aaa', fontWeight: 500 }}>({above}/{total})</span>
                </span>
              </div>
              {/* Track */}
              <div style={{ position: 'relative', height: 14, background: '#f0f0f0', borderRadius: 7 }}>
                {/* Threshold line */}
                <div style={{
                  position: 'absolute', left: `${threshold}%`, top: -4, bottom: -4,
                  width: 2, background: '#ccc', borderRadius: 1,
                  zIndex: 2,
                }} />
                {/* Fill */}
                <div style={{
                  position: 'absolute', left: 0, top: 0, bottom: 0,
                  width: `${Math.min(pct, 100)}%`,
                  background: color, borderRadius: 7,
                  transition: 'width .5s ease',
                }} />
              </div>
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 18 }}>
        <div style={{ width: 2, height: 14, background: '#ccc', borderRadius: 1 }} />
        <span style={{ fontSize: 12, color: '#aaa' }}>Target threshold: {teams[0]?.threshold_pct ?? 70}%</span>
      </div>
    </Card>
  )
}

// ── Section 3: Week-over-week table ──────────────────────────────────────────

function WeekOverWeek({ teams }) {
  const th = { fontSize: 12, fontWeight: 700, color: '#aaa', textTransform: 'uppercase',
               letterSpacing: '.05em', padding: '0 0 12px' }
  const td = { padding: '14px 0', borderTop: `1px solid ${T.border}`, verticalAlign: 'middle' }

  return (
    <Card title="Week-over-Week Trend" subtitle="Comparing current week vs. prior week logging activity">
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ ...th, textAlign: 'left' }}>Team</th>
            <th style={{ ...th, textAlign: 'center' }}>Prior Week</th>
            <th style={{ ...th, textAlign: 'center' }}>This Week</th>
            <th style={{ ...th, textAlign: 'center' }}>Roster</th>
            <th style={{ ...th, textAlign: 'right'  }}>Change</th>
          </tr>
        </thead>
        <tbody>
          {teams.map(t => {
            const cur   = logPct(t)
            const prior = priorPct(t)
            const trend = trendLabel(cur, prior)
            const hasPrior = !!t.prior_week
            return (
              <tr key={t.id}>
                <td style={{ ...td, fontWeight: 600, fontSize: 15, color: T.emerald }}>
                  {t.name}
                  {t.needs_attention && (
                    <span style={{ marginLeft: 8, fontSize: 11, color: T.orange, fontWeight: 700 }}>
                      ⚑ Attention
                    </span>
                  )}
                </td>
                <td style={{ ...td, textAlign: 'center', color: '#888', fontSize: 15 }}>
                  {hasPrior ? `${prior}%` : '—'}
                </td>
                <td style={{ ...td, textAlign: 'center', fontWeight: 700, fontSize: 15,
                             color: barColor(cur, t.threshold_pct ?? 70) }}>
                  {cur}%
                </td>
                <td style={{ ...td, textAlign: 'center', color: '#aaa', fontSize: 14 }}>
                  {t.joined_count}/{t.roster_count}
                </td>
                <td style={{ ...td, textAlign: 'right', fontWeight: 700, fontSize: 14,
                             color: trend.color }}>
                  {hasPrior ? trend.text : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Card>
  )
}

// ── Section 4: Attention ranking ──────────────────────────────────────────────

function AttentionRanking({ teams }) {
  const sorted = [...teams].sort((a, b) => b.attention_score - a.attention_score)
  const max    = sorted[0]?.attention_score || 1

  return (
    <Card title="Attention Priority" subtitle="Teams ranked by engagement gap — higher score = more support needed">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {sorted.map((t, i) => {
          const pct = Math.max(4, Math.round((t.attention_score / max) * 100))
          const color = t.needs_attention ? T.orange : '#3dbc6a'
          return (
            <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ fontWeight: 800, fontSize: 18, color: '#ddd', width: 28, flexShrink: 0 }}>
                {i + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 15, color: T.emerald }}>{t.name}</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color }}>
                    {t.needs_attention ? '⚑ Needs attention' : '✓ On track'}
                  </span>
                </div>
                <div style={{ height: 8, background: '#f0f0f0', borderRadius: 4 }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 4 }} />
                </div>
                <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                  Score {t.attention_score} · {logPct(t)}% logged this week
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

// ── Section 5: Adoption funnel ────────────────────────────────────────────────

function AdoptionFunnel({ teams }) {
  const totalRoster  = teams.reduce((s, t) => s + (t.roster_count ?? 0), 0)
  const totalJoined  = teams.reduce((s, t) => s + (t.joined_count ?? 0), 0)
  const totalLogged  = teams.reduce((s, t) => s + (t.current_week?.players_above_threshold ?? 0), 0)

  const steps = [
    { label: 'On Roster',       value: totalRoster,  color: '#e8f5e9' , text: T.emerald },
    { label: 'App Joined',      value: totalJoined,  color: '#c8e6c9',  text: '#1a5c2a' },
    { label: 'Active This Week',value: totalLogged,  color: T.neon,     text: T.emerald },
  ]
  const max = totalRoster || 1

  return (
    <Card title="Engagement Funnel" subtitle="How athletes move from roster enrollment to active logging">
      <div style={{ display: 'flex', gap: 0, alignItems: 'flex-end', height: 140, marginBottom: 16 }}>
        {steps.map((step, i) => {
          const h = Math.max(24, Math.round((step.value / max) * 130))
          return (
            <React.Fragment key={step.label}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                <div style={{ fontWeight: 800, fontSize: 26, color: step.text === T.emerald ? T.emerald : step.text }}>
                  {step.value}
                </div>
                <div style={{
                  width: '80%', height: h, background: step.color,
                  borderRadius: '6px 6px 0 0',
                  border: `1px solid ${T.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }} />
              </div>
              {i < steps.length - 1 && (
                <div style={{ color: '#ccc', fontSize: 20, paddingBottom: 4, flexShrink: 0 }}>›</div>
              )}
            </React.Fragment>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 0 }}>
        {steps.map((step, i) => (
          <React.Fragment key={step.label}>
            <div style={{ flex: 1, textAlign: 'center', fontSize: 13, color: '#888', fontWeight: 600 }}>
              {step.label}
            </div>
            {i < steps.length - 1 && <div style={{ flexShrink: 0, width: 20 }} />}
          </React.Fragment>
        ))}
      </div>
    </Card>
  )
}

// ── Main Reports screen ───────────────────────────────────────────────────────

const s = {
  wrap:   { padding: '36px 32px', maxWidth: 960, margin: '0 auto' },
  header: { marginBottom: 32 },
  title:  { fontWeight: 800, fontSize: 30, color: '#fff' },
  sub:    { fontSize: 15, color: 'rgba(255,255,255,0.5)', marginTop: 6, fontWeight: 500 },
  grid2:  { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 },
  empty:  { color: 'rgba(255,255,255,0.4)', fontSize: 15, marginTop: 48, textAlign: 'center' },
}

export default function Reports({ teamsData }) {
  const teams = teamsData?.teams ?? []

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={s.title}>Reports</div>
        <div style={s.sub}>
          Season overview · {teamsData?.season || 'Current season'}
        </div>
      </div>

      {teams.length === 0 && (
        <p style={s.empty}>No team data available yet.</p>
      )}

      {teams.length > 0 && (
        <>
          <SummaryTiles teams={teams} />

          <div style={{ marginTop: 16 }}>
            <EngagementBarChart teams={teams} />
          </div>

          <div style={s.grid2}>
            <AttentionRanking teams={teams} />
            <AdoptionFunnel teams={teams} />
          </div>

          <div style={{ marginTop: 16, marginBottom: 32 }}>
            <WeekOverWeek teams={teams} />
          </div>
        </>
      )}
    </div>
  )
}
