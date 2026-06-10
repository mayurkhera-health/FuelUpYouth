import { useEffect, useState } from "react";

const scoreColor = s => s >= 75 ? "#2d6a4f" : s >= 50 ? "#d97706" : "#dc2626";
const scoreStatus = s => s >= 90 ? "Elite fueling today" : s >= 75 ? "Game ready" : s >= 50 ? "Getting game-ready" : "Needs fuel";

export default function FuelScoreCard({ score, scoreYesterday }) {
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (score == null) return;
    let v = 0;
    const step = () => {
      v = Math.min(score, v + 2);
      setDisplayed(v);
      if (v < score) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [score]);

  const color = score != null ? scoreColor(score) : "#8aa898";
  const trend = score != null && scoreYesterday != null
    ? score - scoreYesterday
    : null;

  return (
    <div style={s.card}>
      <div style={s.topRow}>
        <span style={s.label}>Fuel score</span>
        {trend != null && (
          <span style={{ fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", color: trend > 0 ? "#2d6a4f" : trend < 0 ? "#dc2626" : "#8aa898" }}>
            {trend > 0 ? `↑ +${trend}` : trend < 0 ? `↓ ${trend}` : "→ stable"}
          </span>
        )}
      </div>

      <div style={s.numRow}>
        <span style={{ ...s.num, color }}>{score != null ? displayed : "—"}</span>
        <span style={s.denom}>{score != null ? " / 100" : ""}</span>
      </div>

      <div style={{ ...s.status, color }}>{score != null ? scoreStatus(score) : "Log meals to see score"}</div>

      <div style={s.track}>
        <div style={{ ...s.fill, width: `${Math.min(100, displayed)}%`, background: color }} />
      </div>
    </div>
  );
}

const s = {
  card:   { flex: 1, background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "12px", padding: "14px" },
  topRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" },
  label:  { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#4a6358" },
  numRow: { display: "flex", alignItems: "baseline", gap: "2px", marginBottom: "4px" },
  num:    { fontSize: "44px", fontWeight: "800", fontFamily: "'Nunito', sans-serif", letterSpacing: "-0.05em", lineHeight: 1, transition: "color 0.3s" },
  denom:  { fontSize: "17px", color: "#1b3a2a", fontFamily: "'DM Sans', sans-serif", fontWeight: "600" },
  status: { fontSize: "15px", fontFamily: "'DM Sans', sans-serif", fontWeight: "600", marginBottom: "10px" },
  track:  { height: "2px", background: "#dce8e0", borderRadius: "2px", overflow: "hidden" },
  fill:   { height: "100%", borderRadius: "2px", transition: "width 0.6s ease" },
};
