const API = import.meta.env.VITE_API_URL ?? "";

export default function HydrationTracker({ cups, targetCups, athleteId, onUpdate }) {
  const pct = targetCups > 0 ? Math.round((cups / targetCups) * 100) : 0;
  const ozLogged = cups * 8;
  const ozTarget = targetCups * 8;

  async function handleCupTap(i) {
    // Tapping filled cup i → set cups = i (unfill from i onward)
    // Tapping empty cup i → set cups = i + 1 (fill up to and including i)
    const newCups = i < cups ? i : i + 1;
    onUpdate(newCups); // optimistic
    try {
      await fetch(`${API}/api/water-log/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: athleteId, cups: newCups }),
      });
    } catch (_) {}
  }

  const note = cups >= targetCups
    ? "✓ Hydration goal met! Keep sipping during the game."
    : `Tap each cup as you drink · ${targetCups - cups} more cup${targetCups - cups !== 1 ? "s" : ""} needed`;

  return (
    <div style={s.card}>
      <div style={s.topRow}>
        <span style={s.label}>💧 Hydration</span>
        <span style={s.stat}>
          <span style={{ fontWeight: "700", fontFamily: "'Nunito', sans-serif", fontSize: "15px", color: "#4a8fc4" }}>{ozLogged} / {ozTarget} oz · {pct}%</span>
        </span>
      </div>

      <div style={s.grid}>
        {Array.from({ length: targetCups }, (_, i) => (
          <button
            key={i}
            style={{ ...s.cup, ...(i < cups ? s.cupFilled : s.cupEmpty) }}
            onClick={() => handleCupTap(i)}
            title={i < cups ? "Click to unfill" : "Click to fill"}
          >
            {i < cups ? "💧" : "○"}
          </button>
        ))}
      </div>

      <div style={s.note}>{note}</div>
    </div>
  );
}

const s = {
  card:      { background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "12px", padding: "13px 14px", marginTop: "8px" },
  topRow:    { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" },
  label:     { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#4a6358" },
  stat:      {},
  grid:      { display: "flex", flexWrap: "wrap", gap: "5px", marginBottom: "8px" },
  cup:       { width: "28px", height: "28px", borderRadius: "6px", fontSize: "16px", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "transform 0.1s", border: "none" },
  cupFilled: { background: "rgba(74,143,196,0.1)", border: "1px solid rgba(74,143,196,0.4)" },
  cupEmpty:  { background: "transparent", border: "1px solid #dce8e0", color: "#4a6358", fontSize: "14px" },
  note:      { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "#4a6358" },
};
