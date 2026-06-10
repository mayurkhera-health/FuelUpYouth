export default function StreakCard({ streak }) {
  const { current_streak = 0, best_streak = 0, best_streak_date, week_logged = [] } = streak || {};
  const days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

  return (
    <div style={s.card}>
      <div style={s.topRow}>
        <span style={s.label}>Logging streak</span>
        <span style={{ fontSize: "20px" }}>🔥</span>
      </div>

      <div style={s.numRow}>
        <span style={s.num}>{current_streak}</span>
        <span style={s.unit}>days</span>
      </div>

      <div style={s.best}>
        Best: {best_streak} days{best_streak_date ? ` · ${best_streak_date}` : ""}
      </div>

      <div style={s.dotsWrap}>
        {days.map((d, i) => (
          <div key={d} style={s.dotCol}>
            <div style={{ ...s.dot, background: week_logged[i] ? "#d97706" : "#dce8e0" }} />
            <div style={s.dotLabel}>{d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const s = {
  card:    { flex: 1, background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "12px", padding: "14px" },
  topRow:  { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" },
  label:   { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#4a6358" },
  numRow:  { display: "flex", alignItems: "baseline", gap: "4px", marginBottom: "4px" },
  num:     { fontSize: "44px", fontWeight: "800", fontFamily: "'Nunito', sans-serif", color: "#d97706", letterSpacing: "-0.05em", lineHeight: 1 },
  unit:    { fontSize: "17px", color: "#1b3a2a", fontFamily: "'DM Sans', sans-serif", fontWeight: "600" },
  best:    { fontSize: "14px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", marginBottom: "10px" },
  dotsWrap:{ display: "flex", gap: "3px" },
  dotCol:  { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" },
  dot:     { height: "5px", width: "100%", borderRadius: "2px" },
  dotLabel:{ fontSize: "13px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif", fontWeight: "600", textTransform: "uppercase" },
};
