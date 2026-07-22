import React from 'react'

const s = {
  wrap:    { padding: '36px 40px', maxWidth: 680 },
  header:  { marginBottom: 28 },
  title:   { fontWeight: 700, fontSize: 24, color: '#111', marginBottom: 4 },
  meta:    { fontSize: 13, color: '#888', display: 'flex', gap: 20, marginTop: 6 },

  row: (needsAttention) => ({
    background: '#fff',
    borderRadius: 12,
    padding: '18px 20px',
    marginBottom: 10,
    cursor: 'pointer',
    border: '1px solid #e5e5e5',
    boxShadow: '0 1px 3px rgba(0,0,0,.05)',
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    borderLeft: needsAttention ? '4px solid #e67e22' : '4px solid transparent',
    transition: 'box-shadow .1s',
    minHeight: 44,
  }),

  left:      { flex: '0 0 auto', minWidth: 160 },
  teamName:  { fontWeight: 700, fontSize: 17, color: '#111' },
  flagLabel: { fontSize: 11, fontWeight: 600, color: '#e67e22',
               textTransform: 'uppercase', letterSpacing: '.04em', marginTop: 2 },

  stats:   { flex: 1, display: 'flex', gap: 28, alignItems: 'center',
             marginLeft: 24, flexWrap: 'wrap' },
  stat:    { display: 'flex', flexDirection: 'column', gap: 2 },
  statVal: { fontWeight: 700, fontSize: 18, color: '#1a7a4a' },
  statLbl: { fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: '.04em' },

  trend:   (glyph) => ({
    fontSize: 18,
    color: glyph === '▲' ? '#1a7a4a' : glyph === '▼' ? '#c0392b' : '#aaa',
    marginLeft: 'auto',
    marginRight: 8,
    fontWeight: 700,
  }),
  chevron: { color: '#ddd', fontSize: 20, flexShrink: 0 },
}

function trendGlyph(cur, prior) {
  if (!cur || !prior) return '▬'
  const diff = cur.players_above_threshold - prior.players_above_threshold
  if (diff > 0) return '▲'
  if (diff < 0) return '▼'
  return '▬'
}

function fmtDate(d) {
  if (!d) return null
  return new Date(d + (d.includes('T') ? '' : 'T00:00:00Z'))
    .toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function TeamSelector({ teamsData, onSelect }) {
  const { generated_at, season, teams = [] } = teamsData || {}

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={s.title}>Your Teams</div>
        <div style={s.meta}>
          {season && <span>{season}</span>}
          {generated_at && <span>Snapshot: {fmtDate(generated_at)}</span>}
        </div>
      </div>

      {teams.map((t, i) => {
        const glyph = trendGlyph(t.current_week, t.prior_week)
        const above = t.current_week?.players_above_threshold ?? '—'
        const total = t.roster_count ?? t.joined_count ?? '—'

        return (
          <div
            key={t.id}
            style={s.row(t.needs_attention)}
            onClick={() => onSelect(t)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && onSelect(t)}
          >
            <div style={s.left}>
              <div style={s.teamName}>{t.name}</div>
              {t.needs_attention && (
                <div style={s.flagLabel}>Needs attention</div>
              )}
            </div>

            <div style={s.stats}>
              <div style={s.stat}>
                <span style={s.statVal}>{t.joined_count}/{total}</span>
                <span style={s.statLbl}>Joined</span>
              </div>
              <div style={s.stat}>
                <span style={s.statVal}>{above}/{total}</span>
                <span style={s.statLbl}>Above {t.threshold_pct}%</span>
              </div>
            </div>

            <span style={s.trend(glyph)}>{glyph}</span>
            <span style={s.chevron}>›</span>
          </div>
        )
      })}
    </div>
  )
}
