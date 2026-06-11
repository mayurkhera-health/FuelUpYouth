const API = import.meta.env.VITE_API_URL ?? "";

export default function QuickRow({ waterCups, targetCups, caloriesLogged, caloriesTarget, athleteId, onWaterUpdate }) {
  const pctWater = targetCups > 0 ? Math.round((waterCups / targetCups) * 100) : 0;
  const ozLogged = (waterCups ?? 0) * 8;
  const ozTarget = (targetCups ?? 10) * 8;

  const calPct    = caloriesTarget > 0 ? Math.round((caloriesLogged / caloriesTarget) * 100) : 0;
  const calRemain = Math.max(0, Math.round((caloriesTarget ?? 0) - (caloriesLogged ?? 0)));
  const calColor  = calPct >= 80 ? "#2d6a4f" : calPct >= 60 ? "#b45309" : "#b83a3a";

  async function handleCupTap(i) {
    const newCups = i < waterCups ? i : i + 1;
    onWaterUpdate(newCups);
    try {
      await fetch(`${API}/api/water-log/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: athleteId, cups: newCups }),
      });
    } catch (_) {}
  }

  return (
    <div style={s.row}>
      {/* Hydration */}
      <div style={s.card}>
        <div style={s.label}>💧 Hydration</div>
        <div style={{ ...s.value, color: "#1a6ab8" }}>{ozLogged}oz</div>
        <div style={s.sub}>of {ozTarget}oz · {pctWater}%</div>
        <div style={s.cups}>
          {Array.from({ length: targetCups || 10 }, (_, i) => (
            <button
              key={i}
              style={{ ...s.cup, ...(i < waterCups ? s.cupFilled : s.cupEmpty) }}
              onClick={() => handleCupTap(i)}
            >
              {i < waterCups ? "💧" : "○"}
            </button>
          ))}
        </div>
      </div>

      {/* Calories */}
      <div style={s.card}>
        <div style={s.label}>🔥 Calories</div>
        <div style={{ ...s.value, color: calColor }}>{Math.round(caloriesLogged ?? 0)}</div>
        <div style={s.sub}>of {Math.round(caloriesTarget ?? 0)} · {calPct}%</div>
        <div style={s.track}><div style={{ ...s.fill, width: `${Math.min(calPct, 100)}%`, background: calColor }} /></div>
        <div style={s.note}>{calRemain} kcal remaining</div>
      </div>
    </div>
  );
}

const s = {
  row:       { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "10px" },
  card:      { background: "#fff", borderRadius: "14px", border: "1px solid #dce8e0", padding: "13px" },
  label:     { fontSize: "11px", textTransform: "uppercase", letterSpacing: ".07em", color: "#8aa898", marginBottom: "4px" },
  value:     { fontFamily: "'Nunito', sans-serif", fontSize: "24px", fontWeight: "800", letterSpacing: "-.03em", lineHeight: "1", marginBottom: "2px" },
  sub:       { fontSize: "12px", color: "#8aa898", fontWeight: "300", marginBottom: "6px" },
  cups:      { display: "flex", flexWrap: "wrap", gap: "3px", marginTop: "4px" },
  cup:       { width: "20px", height: "20px", borderRadius: "4px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", cursor: "pointer", border: "none", padding: 0 },
  cupFilled: { background: "rgba(26,106,184,.10)", border: "1px solid rgba(26,106,184,.40)" },
  cupEmpty:  { background: "transparent", border: "1px solid #dce8e0", color: "#8aa898" },
  track:     { height: "2px", background: "#f4f8f5", borderRadius: "2px", overflow: "hidden", marginTop: "2px" },
  fill:      { height: "100%", borderRadius: "2px", transition: "width 0.7s ease" },
  note:      { fontSize: "12px", color: "#8aa898", fontWeight: "300", marginTop: "6px" },
};
