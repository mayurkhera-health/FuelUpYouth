import React, { useState } from 'react'

const T = {
  emerald: '#0f2a1f',
  neon:    '#3dfc3d',
  orange:  '#ff9800',
  border:  '#dadad8',
}

// ── CSV export helper ─────────────────────────────────────────────────────────

function downloadCSV(filename, headers, rows) {
  const escape = v => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines  = [headers.map(escape).join(','), ...rows.map(r => r.map(escape).join(','))]
  const blob   = new Blob([lines.join('\n')], { type: 'text/csv' })
  const url    = URL.createObjectURL(blob)
  const a      = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function logPct(t) {
  const above = t.current_week?.players_above_threshold ?? 0
  const total = t.roster_count ?? 1
  return Math.round((above / total) * 100)
}

function priorPct(t) {
  const above = t.prior_week?.players_above_threshold ?? 0
  const total = t.roster_count ?? 1
  return Math.round((above / total) * 100)
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

// ── Report definitions ────────────────────────────────────────────────────────

function buildReports(teams, season) {
  const totalRoster = teams.reduce((s, t) => s + (t.roster_count ?? 0), 0)
  const totalJoined = teams.reduce((s, t) => s + (t.joined_count ?? 0), 0)
  const totalLogged = teams.reduce((s, t) => s + (t.current_week?.players_above_threshold ?? 0), 0)
  const overallPct  = totalRoster > 0 ? Math.round((totalLogged / totalRoster) * 100) : 0

  return [
    {
      id: 'weekly',
      icon: '📊',
      title: 'Weekly Engagement Summary',
      description: 'Current week logging activity for all teams — roster size, athletes in app, athletes who logged, and percentage vs. threshold.',
      badge: 'CSV',
      badgeColor: '#1a7a4a',
      download: () => downloadCSV(
        `weekly-engagement-${today()}.csv`,
        ['Team', 'Roster', 'App Joined', 'Logged This Week', 'Logging %', 'Threshold %', 'Status'],
        teams.map(t => [
          t.name,
          t.roster_count ?? 0,
          t.joined_count ?? 0,
          t.current_week?.players_above_threshold ?? 0,
          `${logPct(t)}%`,
          `${t.threshold_pct ?? 70}%`,
          t.needs_attention ? 'Needs Attention' : 'On Track',
        ])
      ),
    },
    {
      id: 'wow',
      icon: '📈',
      title: 'Week-over-Week Comparison',
      description: 'Side-by-side comparison of prior week vs. this week logging rates, showing directional change per team.',
      badge: 'CSV',
      badgeColor: '#1a7a4a',
      download: () => downloadCSV(
        `week-over-week-${today()}.csv`,
        ['Team', 'Prior Week %', 'This Week %', 'Change (pp)', 'Direction'],
        teams.map(t => {
          const cur   = logPct(t)
          const prior = t.prior_week ? priorPct(t) : null
          const diff  = prior !== null ? cur - prior : null
          return [
            t.name,
            prior !== null ? `${prior}%` : 'No data',
            `${cur}%`,
            diff !== null ? diff : 'N/A',
            diff === null ? '—' : diff > 0 ? '▲ Up' : diff < 0 ? '▼ Down' : '▬ Flat',
          ]
        })
      ),
    },
    {
      id: 'attention',
      icon: '⚑',
      title: 'Attention Alert Report',
      description: 'Teams flagged as needing attention — sorted by attention score. Use to prioritize outreach.',
      badge: 'CSV',
      badgeColor: T.orange,
      download: () => {
        const flagged = [...teams].sort((a, b) => b.attention_score - a.attention_score)
        downloadCSV(
          `attention-alerts-${today()}.csv`,
          ['Team', 'Attention Score', 'Logging %', 'Athletes Logged', 'Roster', 'Status'],
          flagged.map(t => [
            t.name,
            t.attention_score ?? 0,
            `${logPct(t)}%`,
            t.current_week?.players_above_threshold ?? 0,
            t.roster_count ?? 0,
            t.needs_attention ? 'Needs Attention' : 'On Track',
          ])
        )
      },
    },
    {
      id: 'season',
      icon: '🏆',
      title: 'Season Overview',
      description: `Aggregate season stats across all ${teams.length} teams — total athletes, app adoption, and overall engagement rate.`,
      badge: 'CSV',
      badgeColor: '#1a7a4a',
      download: () => downloadCSV(
        `season-overview-${today()}.csv`,
        ['Metric', 'Value'],
        [
          ['Season', season || 'Current'],
          ['Report Date', today()],
          ['Total Teams', teams.length],
          ['Total Athletes (Roster)', totalRoster],
          ['Athletes in App', totalJoined],
          ['App Adoption %', `${totalRoster > 0 ? Math.round((totalJoined / totalRoster) * 100) : 0}%`],
          ['Athletes Logged This Week', totalLogged],
          ['Overall Engagement %', `${overallPct}%`],
          ['Teams Needing Attention', teams.filter(t => t.needs_attention).length],
          ['Teams On Track', teams.filter(t => !t.needs_attention).length],
        ]
      ),
    },
  ]
}

// ── Report card ───────────────────────────────────────────────────────────────

function ReportCard({ report, disabled }) {
  const [clicked, setClicked] = useState(false)

  function handleDownload() {
    report.download()
    setClicked(true)
    setTimeout(() => setClicked(false), 2000)
  }

  return (
    <div style={{
      background: '#fff', borderRadius: 16, padding: '28px 28px 24px',
      border: `1px solid ${T.border}`, boxShadow: '0 2px 10px rgba(0,0,0,.06)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
        <div style={{
          fontSize: 28, width: 52, height: 52, borderRadius: 12,
          background: '#f6f8f6', display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {report.icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: T.emerald, marginBottom: 2 }}>
            {report.title}
          </div>
          <span style={{
            fontSize: 11, fontWeight: 700, color: report.badgeColor,
            textTransform: 'uppercase', letterSpacing: '.06em',
          }}>
            {report.badge}
          </span>
        </div>
      </div>

      <p style={{ fontSize: 14, color: '#666', lineHeight: 1.55, flex: 1, marginBottom: 20 }}>
        {report.description}
      </p>

      <button
        onClick={disabled ? undefined : handleDownload}
        disabled={disabled}
        style={{
          padding: '11px 0', borderRadius: 10, fontSize: 14, fontWeight: 700,
          cursor: disabled ? 'default' : 'pointer', border: 'none',
          background: disabled ? '#f0f0f0'
                    : clicked ? '#d4ffd4'
                    : T.emerald,
          color: disabled ? '#ccc' : clicked ? '#1a5c2a' : T.neon,
          transition: 'background .2s, color .2s',
        }}
      >
        {disabled ? 'No data yet' : clicked ? '✓ Downloaded' : '⬇ Download CSV'}
      </button>
    </div>
  )
}

// ── main ──────────────────────────────────────────────────────────────────────

const s = {
  wrap:   { padding: '36px 32px', maxWidth: 960, margin: '0 auto' },
  header: { marginBottom: 32 },
  title:  { fontWeight: 800, fontSize: 30, color: '#fff' },
  sub:    { fontSize: 15, color: 'rgba(255,255,255,0.5)', marginTop: 6, fontWeight: 500 },
  hint:   { fontSize: 13, color: 'rgba(255,255,255,0.35)', marginTop: 10, fontStyle: 'italic' },
  grid:   { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
}

export default function Reports({ teamsData }) {
  const teams   = teamsData?.teams ?? []
  const season  = teamsData?.season
  const reports = buildReports(teams, season)

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={s.title}>Reports</div>
        <div style={s.sub}>{season || 'Current season'} · Export data as CSV</div>
        <div style={s.hint}>Files download instantly to your device — no account needed.</div>
      </div>

      <div style={s.grid}>
        {reports.map(r => (
          <ReportCard key={r.id} report={r} disabled={teams.length === 0} />
        ))}
      </div>
    </div>
  )
}
