export default function WeekNav({ weekStart, weekEnd, daysLogged, isCurrentWeek, onPrev, onNext }) {
  function fmt(iso) {
    if (!iso) return "—";
    const [, m, d] = iso.split("-");
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return `${months[+m - 1]} ${+d}`;
  }
  const year = weekStart ? weekStart.slice(0, 4) : "";
  const label = `${fmt(weekStart)} – ${fmt(weekEnd)}, ${year}`;
  const sub = isCurrentWeek
    ? `Current week · ${daysLogged} day${daysLogged !== 1 ? "s" : ""} logged`
    : `Past week · ${daysLogged} day${daysLogged !== 1 ? "s" : ""} logged`;

  return (
    <div style={s.strip}>
      <div>
        <div style={s.label}>{label}</div>
        <div style={s.sub}>{sub}</div>
      </div>
      <div style={s.arrows}>
        <button style={s.arrow} onClick={onPrev} aria-label="Previous week">‹</button>
        <button
          style={{ ...s.arrow, opacity: isCurrentWeek ? 0.35 : 1 }}
          onClick={onNext}
          disabled={isCurrentWeek}
          aria-label="Next week"
        >›</button>
      </div>
    </div>
  );
}

const s = {
  strip: {
    background: "#fff",
    borderBottom: "1px solid #dce8e0",
    padding: "10px 16px 8px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  label: {
    fontSize: "14px",
    fontWeight: "700",
    color: "#1b3a2a",
    letterSpacing: "-.01em",
    fontFamily: "'Nunito', sans-serif",
  },
  sub: { fontSize: "12px", color: "#8aa898", marginTop: "1px" },
  arrows: { display: "flex", gap: "6px" },
  arrow: {
    width: "28px",
    height: "28px",
    border: "1px solid #dce8e0",
    borderRadius: "6px",
    background: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "16px",
    color: "#4a6358",
    cursor: "pointer",
  },
};
