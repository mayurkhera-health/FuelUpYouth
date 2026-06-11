const NUTRIENTS = [
  { key: "iron_mg",    label: "🩸 Iron" },
  { key: "calcium_mg", label: "🦴 Calcium" },
  { key: "carbs_g",    label: "⚡ Carbs" },
  { key: "protein_g",  label: "💪 Protein" },
  { key: "calories",   label: "🔥 Calories" },
  { key: "water_oz",   label: "💧 Water" },
];

const EVENT_ABBR = {
  game: "GAM", tournament: "TOUR", practice: "PRA",
  strength: "STR", training: "TRN", rest: "RES",
};

const EVENT_COLOR = {
  game: "#c05a4a", tournament: "#7e6ab5", practice: "#c8903a",
  strength: "#1d4ed8", training: "#1d4ed8", rest: "#2d6a4f",
};

function Dot({ pct, isToday }) {
  const todayStyle = isToday
    ? { outline: "2px solid #2d6a4f", outlineOffset: "1px" }
    : {};
  const base = {
    width: "28px", height: "26px", borderRadius: "5px",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: "11px", fontWeight: "700", margin: "0 auto",
    fontFamily: "'Nunito', sans-serif",
    ...todayStyle,
  };
  if (pct === null || pct === undefined) {
    return <div style={{ ...base, background: "#f4f8f5", color: "#c8d8d0" }}>—</div>;
  }
  const scheme =
    pct >= 80
      ? { bg: "rgba(45,106,79,.15)", color: "#2d6a4f" }
      : pct >= 50
      ? { bg: "rgba(217,119,6,.12)", color: "#b45309" }
      : { bg: "rgba(217,119,6,.12)", color: "#b45309" };
  return (
    <div style={{ ...base, background: scheme.bg, color: scheme.color }}>
      {pct >= 80 ? "✓" : pct}
    </div>
  );
}

export default function WeeklyHeatmap({ days = [], heatmap = {} }) {
  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.eyebrow}>Weekly nutrient heatmap</span>
        <span style={s.right}>color = % of target</span>
      </div>

      <div style={s.grid}>
        {/* Day header row */}
        <div style={s.row}>
          <div style={s.labelCell} />
          {days.map((day) => (
            <div key={day.date} style={s.headerCell}>
              <span
                style={{ ...s.dayAbbr, color: day.is_today ? "#2d6a4f" : "#4a6358" }}
              >
                {day.day_abbr}
              </span>
              {day.event_type && (
                <span
                  style={{
                    ...s.eventBadge,
                    color: EVENT_COLOR[day.event_type] ?? "#4a6358",
                  }}
                >
                  {EVENT_ABBR[day.event_type] ??
                    day.event_type.slice(0, 3).toUpperCase()}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Nutrient rows */}
        {NUTRIENTS.map(({ key, label }) => (
          <div key={key} style={s.row}>
            <div style={s.labelCell}>{label}</div>
            {days.map((day, i) => (
              <Dot key={day.date} pct={heatmap[key]?.[i] ?? null} isToday={day.is_today} />
            ))}
          </div>
        ))}

        {/* Fuel score row */}
        <div
          style={{
            ...s.row,
            borderTop: "1px solid #dce8e0",
            marginTop: "4px",
            paddingTop: "6px",
          }}
        >
          <div
            style={{
              ...s.labelCell,
              fontSize: "10px",
              textTransform: "uppercase",
              letterSpacing: ".06em",
              color: "#8aa898",
              fontWeight: "600",
            }}
          >
            Fuel Score
          </div>
          {days.map((day) => {
            const sc = day.score;
            const color =
              sc == null
                ? "#c8d8d0"
                : sc >= 75
                ? "#2d6a4f"
                : sc >= 50
                ? "#b45309"
                : "#b45309";
            return (
              <div
                key={day.date}
                style={{
                  width: "28px", height: "26px", borderRadius: "5px",
                  margin: "0 auto", background: "#f4f8f5", color,
                  fontWeight: day.is_today ? "800" : "700",
                  fontSize: day.is_today ? "13px" : "11px",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: "'Nunito', sans-serif",
                  ...(day.is_today
                    ? { outline: "2px solid #2d6a4f", outlineOffset: "1px" }
                    : {}),
                }}
              >
                {sc ?? "—"}
              </div>
            );
          })}
        </div>
      </div>

      <div style={s.legend}>
        <span style={{ ...s.legendDot, background: "rgba(45,106,79,.15)", color: "#2d6a4f" }}>✓</span>
        {" "}≥80%{"  "}
        <span style={{ ...s.legendDot, background: "rgba(217,119,6,.12)", color: "#b45309", marginLeft: "8px" }}>65</span>
        {" "}50–79%{"  "}
        <span style={{ ...s.legendDot, background: "rgba(217,119,6,.12)", color: "#b45309", marginLeft: "8px" }}>35</span>
        {" "}&lt;50%{"  "}
        <span style={{ ...s.legendDot, background: "#f4f8f5", color: "#c8d8d0", marginLeft: "8px" }}>—</span>
        {" "}Not logged
      </div>
    </div>
  );
}

const s = {
  card: {
    background: "#fff",
    borderRadius: "14px",
    border: "1px solid #dce8e0",
    overflow: "hidden",
  },
  header: {
    padding: "11px 14px 10px",
    borderBottom: "1px solid #dce8e0",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  eyebrow: {
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: ".1em",
    color: "#2d6a4f",
    fontWeight: "600",
  },
  right: { fontSize: "10px", color: "#8aa898" },
  grid: { padding: "10px 8px 10px" },
  row: {
    display: "grid",
    gridTemplateColumns: "72px repeat(7, 1fr)",
    gap: "3px",
    marginBottom: "3px",
    alignItems: "center",
  },
  labelCell: { fontSize: "12px", color: "#4a6358", fontWeight: "500" },
  headerCell: { display: "flex", flexDirection: "column", alignItems: "center", gap: "1px" },
  dayAbbr: { fontSize: "11px", fontWeight: "700" },
  eventBadge: { fontSize: "9px", fontWeight: "600", letterSpacing: ".04em" },
  legend: {
    borderTop: "1px solid #dce8e0",
    padding: "8px 12px",
    fontSize: "11px",
    color: "#8aa898",
    display: "flex",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "3px",
  },
  legendDot: {
    width: "20px", height: "18px", borderRadius: "4px",
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    fontSize: "10px", fontWeight: "700",
  },
};
