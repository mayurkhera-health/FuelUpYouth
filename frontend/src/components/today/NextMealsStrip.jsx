function parseMealTime(whenStr) {
  if (!whenStr) return null;
  const m = whenStr.match(/(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})/);
  if (!m) return null;
  return new Date(`${m[1]}T${m[2]}:00`);
}

function fmt12(dt) {
  if (!dt) return "";
  return dt.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
}

function getMealStatus(whenStr, mealLogs) {
  const t = parseMealTime(whenStr);
  if (!t) return "upcoming";
  const now = new Date();
  const diffMins = (t - now) / 60000;
  if (diffMins < -120) {
    const logged = mealLogs.some(m => Math.abs(new Date(m.logged_at) - t) < 2 * 3600000);
    return logged ? "done" : "past";
  }
  if (diffMins <= 60) return "now";
  return "upcoming";
}

const STATUS_CHIP = {
  done:     { label: "Done", bg: "rgba(82,183,136,0.1)", color: "#2d6a4f", border: "rgba(82,183,136,0.2)" },
  now:      { label: "Now", bg: "rgba(217,119,6,0.12)", color: "#d97706", border: "rgba(217,119,6,0.2)", blink: true },
  past:     { label: "—", bg: "#f4f8f5", color: "#4a6358", border: "#dce8e0" },
  upcoming: { label: "—", bg: "#f4f8f5", color: "#4a6358", border: "#dce8e0" },
};

export default function NextMealsStrip({ protocol = [], mealLogs = [] }) {
  const items = protocol.filter(p => !p.when?.includes("night before")).slice(0, 7);
  if (!items.length) return null;

  return (
    <div style={s.wrap}>
      <div style={s.scroll}>
        {items.map((item, i) => {
          const t = parseMealTime(item.when);
          const status = getMealStatus(item.when, mealLogs);
          const chip = STATUS_CHIP[status];
          const isActive = status === "now";
          return (
            <div key={i} style={{ ...s.card, ...(isActive ? s.cardActive : {}) }}>
              <div style={s.time}>{fmt12(t) || item.timing}</div>
              <div style={s.mealLabel}>{item.timing}</div>
              <div style={s.what} title={item.what}>{item.what}</div>
              <div style={{
                ...s.chip,
                background: chip.bg, color: chip.color, border: `1px solid ${chip.border}`,
                animation: chip.blink ? "blink 1.4s infinite" : "none",
              }}>{chip.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const s = {
  wrap:       { margin: "10px -4px 0", overflowX: "auto", scrollbarWidth: "none" },
  scroll:     { display: "flex", gap: "8px", padding: "2px 4px 6px" },
  card:       { width: "140px", flexShrink: 0, background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "10px", padding: "11px 12px", cursor: "pointer" },
  cardActive: { border: "1.5px solid rgba(45,106,79,0.35)", background: "rgba(45,106,79,0.05)" },
  time:       { fontSize: "12px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", color: "#4a6358", marginBottom: "3px" },
  mealLabel:  { fontSize: "14px", fontWeight: "700", fontFamily: "'Nunito', sans-serif", color: "#1b3a2a", letterSpacing: "-0.01em", marginBottom: "3px", lineHeight: 1.6 },
  what:       { fontSize: "12px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "#4a6358", lineHeight: 1.6, marginBottom: "7px", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" },
  chip:       { fontSize: "11px", fontFamily: "'DM Sans', sans-serif", fontWeight: "600", letterSpacing: "0.04em", padding: "2px 6px", borderRadius: "3px", display: "inline-block" },
};
