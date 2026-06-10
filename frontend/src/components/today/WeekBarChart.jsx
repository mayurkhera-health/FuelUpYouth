const EVENT_COLORS = {
  game:       "#c05a4a",
  tournament: "#7e6ab5",
  practice:   "#c8903a",
  training:   "#c8903a",
  strength:   "#4a8fc4",
  rest:       "#8aa898",
};

const EVENT_ABBR = {
  game: "⚽", tournament: "🏆", practice: "🏃", training: "💪", strength: "🏋️", rest: "🌿",
};

const barColor = score => score >= 75 ? "#2d6a4f" : score >= 50 ? "#d97706" : "#dc2626";

const BAR_H = 40;

export default function WeekBarChart({ week = [], avgScore }) {
  return (
    <div style={s.card}>
      <div style={s.topRow}>
        <span style={s.label}>This week</span>
        <span style={s.avg}>
          {avgScore != null ? <><strong style={{ fontFamily: "'Nunito', sans-serif", fontWeight: "800", fontSize: "17px", color: "#1b3a2a" }}>{avgScore}</strong> <span style={{ fontSize: "14px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif", fontWeight: "600" }}>avg fuel score</span></> : <span style={{ fontSize: "14px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif", fontWeight: "500" }}>no data yet</span>}
        </span>
      </div>

      <div style={s.chartWrap}>
        {week.map((day, i) => {
          const h = day.score != null ? Math.max(4, Math.round((day.score / 100) * BAR_H)) : 4;
          const color = day.score != null ? barColor(day.score) : "#dce8e0";
          return (
            <div key={i} style={s.col}>
              <div style={s.barWrap}>
                <div style={{
                  ...s.bar,
                  height: `${h}px`,
                  background: color,
                  border: day.is_today ? `1px solid rgba(45,106,79,0.4)` : "none",
                  borderBottom: "none",
                  opacity: day.date > new Date().toISOString().split("T")[0] ? 0.35 : 1,
                }} />
              </div>
              <div style={{ ...s.dayLabel, color: day.is_today ? "#2d6a4f" : "#4a6358", fontWeight: day.is_today ? "800" : "600" }}>
                {day.day_abbr}
              </div>
              <div style={s.eventDot}>
                {day.event_type && day.event_type !== "rest" ? (
                  <span style={{ fontSize: "14px" }} title={day.event_type}>{EVENT_ABBR[day.event_type] || ""}</span>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const s = {
  card:     { background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "12px", padding: "13px 14px", marginTop: "8px" },
  topRow:   { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" },
  label:    { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#4a6358" },
  avg:      {},
  chartWrap:{ display: "flex", gap: "4px", alignItems: "flex-end" },
  col:      { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" },
  barWrap:  { height: `${BAR_H}px`, display: "flex", alignItems: "flex-end", width: "100%" },
  bar:      { width: "100%", borderRadius: "3px 3px 0 0", minHeight: "4px", transition: "height 0.4s ease" },
  dayLabel: { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: "600" },
  eventDot: { height: "14px", display: "flex", alignItems: "center", fontSize: "13px" },
};
