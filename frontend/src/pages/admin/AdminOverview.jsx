import { useEffect, useState } from "react";
import { adminFetch, AuthError } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import { Button, Spinner } from "./ui";

// The plain-language status page — default landing for a non-technical team
// member reporting hourly. One card, no jargon, all wording comes from the
// backend (/overview) so it lives in one place.
export default function AdminOverview({ onLoggedOut }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load(force) {
    force ? setRefreshing(true) : setLoading(true);
    setError(false);
    try {
      setData(await adminFetch(`/overview${force ? "?force=true" : ""}`));
    } catch (err) {
      if (err instanceof AuthError) return onLoggedOut();
      setError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 80 }}><Spinner size={28} /></div>
    );
  }
  if (error || !data) {
    return (
      <div style={{ textAlign: "center", padding: 60, font: `600 16px ${FONT_DISPLAY}`, color: C.text2 }}>
        Couldn’t load status — try refreshing.
        <div style={{ marginTop: 16 }}><Button onClick={() => load(false)}>Refresh</Button></div>
      </div>
    );
  }

  const time = new Date(data.as_of).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  const h = data.health;
  const healthBg = h.status === "red" ? C.dangerBg : C.brandGhost;
  const healthBorder = h.status === "red" ? C.dangerBorder : C.brandLight;

  return (
    <div style={{ maxWidth: 620, margin: "0 auto" }}>
      <div style={{
        background: C.surface, border: `1px solid ${C.border}`, borderRadius: 18,
        boxShadow: C.shadowMd, overflow: "hidden",
      }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 22px", borderBottom: `1px solid ${C.border}` }}>
          <span style={{ font: `800 20px ${FONT_DISPLAY}`, color: C.text1 }}>📋 FuelUp Status</span>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ font: `500 13px ${FONT_DISPLAY}`, color: C.text3 }}>as of {time}</span>
            <Button variant="ghost" onClick={() => load(true)} disabled={refreshing}>
              {refreshing ? "Refreshing…" : "Refresh"}
            </Button>
          </div>
        </div>

        {/* Health banner */}
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", background: healthBg, borderBottom: `1px solid ${healthBorder}`, padding: "16px 22px" }}>
          <span style={{ fontSize: 22, lineHeight: 1 }}>{h.icon}</span>
          <div>
            <div style={{ font: `800 17px ${FONT_DISPLAY}`, color: C.text1 }}>{h.headline}</div>
            <div style={{ font: `500 14px ${FONT_DISPLAY}`, color: C.text2, marginTop: 2 }}>{h.detail}</div>
          </div>
        </div>

        {/* Grouped status sections */}
        <div style={{ padding: "18px 22px", display: "flex", flexDirection: "column", gap: 22 }}>
          {data.sections.map((sec) => (
            <div key={sec.title}>
              <div style={{
                font: `800 11px ${FONT_DISPLAY}`, color: C.text3, letterSpacing: "0.07em",
                textTransform: "uppercase", marginBottom: 12,
              }}>{sec.title}</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
                {sec.lines.map((ln, i) => <Tile key={i} m={ln} />)}
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

// Donut gauge — hand-rolled SVG, colored amber when the metric is in warning.
function Gauge({ pct, warn, size = 62 }) {
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;
  const filled = circ * (Math.max(0, Math.min(100, pct)) / 100);
  const color = warn ? C.warm : C.brandMid;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={c} cy={c} r={r} fill="none" stroke={C.surface2} strokeWidth={stroke} />
      <circle cx={c} cy={c} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeDasharray={`${filled} ${circ}`} strokeLinecap="round" transform={`rotate(-90 ${c} ${c})`} />
      <text x={c} y={c} textAnchor="middle" dominantBaseline="central"
        style={{ font: `800 15px ${FONT_DISPLAY}`, fill: warn ? "#9a6a1e" : C.text1 }}>{pct}%</text>
    </svg>
  );
}

// One metric: a gauge tile when it's a ratio (has a total), else a stat tile.
function Tile({ m }) {
  const isGauge = m.total != null && m.pct != null;
  const card = {
    background: m.warn ? C.warmLight : C.surface,
    border: `1px solid ${m.warn ? "#f0d9a8" : C.border}`, borderRadius: 14,
    padding: "14px 12px", display: "flex", flexDirection: "column",
    alignItems: "center", gap: 8, textAlign: "center",
  };
  if (isGauge) {
    return (
      <div style={card}>
        <Gauge pct={m.pct} warn={m.warn} />
        <div>
          <div style={{ font: `700 13px ${FONT_DISPLAY}`, color: C.text1 }}>{m.icon} {m.label}{m.warn ? " ⚠️" : ""}</div>
          <div style={{ font: `600 12px ${FONT_DISPLAY}`, color: C.text3, marginTop: 2 }}>{m.value} of {m.total}</div>
        </div>
      </div>
    );
  }
  return (
    <div style={card}>
      <div style={{ fontSize: 22, lineHeight: 1 }}>{m.icon}</div>
      <div style={{ font: `800 30px ${FONT_DISPLAY}`, color: C.text1, lineHeight: 1 }}>{m.value}</div>
      <div style={{ font: `600 13px ${FONT_DISPLAY}`, color: C.text3 }}>{m.label}</div>
    </div>
  );
}
