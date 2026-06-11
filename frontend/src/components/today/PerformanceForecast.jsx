import { useState, useEffect } from "react";

function metricColor(pct) {
  if (pct >= 75) return "#2d6a4f";
  return "#b45309";
}

export default function PerformanceForecast({ forecast }) {
  const [animated, setAnimated] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(t);
  }, []);

  if (!forecast) return null;

  const metrics = [
    { key: "sprint_capacity",   label: "Sprint Capacity" },
    { key: "energy_reserves",   label: "Energy Reserves" },
    { key: "second_half_power", label: "Second-Half Power" },
    { key: "mental_focus",      label: "Mental Focus" },
  ];

  return (
    <div style={s.card}>
      <div style={s.headerRow}>
        <span style={s.eyebrow}>Performance forecast · Based on current fueling</span>
        <span style={s.right}>vs your baseline</span>
      </div>
      <div style={s.grid}>
        {metrics.map(({ key, label }) => {
          const pct = forecast[key] ?? 0;
          const color = metricColor(pct);
          return (
            <div key={key}>
              <div style={s.itemHeader}>
                <span style={s.name}>{label}</span>
                <span style={{ ...s.pct, color }}>{pct}%</span>
              </div>
              <div style={s.track}>
                <div style={{
                  ...s.fill,
                  width: animated ? `${pct}%` : "0%",
                  background: color,
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const s = {
  card:       { background: "#fff", borderRadius: "14px", border: "1px solid #dce8e0", padding: "13px 14px", marginTop: "10px" },
  headerRow:  { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" },
  eyebrow:    { fontSize: "12px", textTransform: "uppercase", letterSpacing: ".1em", color: "#4a6358" },
  right:      { fontSize: "12px", color: "#4a6358", fontWeight: "400" },
  grid:       { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" },
  itemHeader: { display: "flex", justifyContent: "space-between", marginBottom: "5px" },
  name:       { fontSize: "14px", color: "#1b3a2a" },
  pct:        { fontSize: "14px", fontWeight: "700" },
  track:      { height: "2px", background: "#f4f8f5", borderRadius: "2px", overflow: "hidden" },
  fill:       { height: "100%", borderRadius: "2px", transition: "width 0.7s ease" },
};
