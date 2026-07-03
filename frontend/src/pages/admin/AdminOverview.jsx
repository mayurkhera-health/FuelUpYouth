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
  const [copied, setCopied] = useState(false);

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

  function copyReport() {
    if (!data) return;
    const stamp = new Date(data.as_of).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
    const text = `FuelUp Status — ${stamp}\n${data.report_body}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
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
        <div style={{ padding: "18px 22px", display: "flex", flexDirection: "column", gap: 20 }}>
          {data.sections.map((sec) => (
            <div key={sec.title}>
              <div style={{
                font: `800 11px ${FONT_DISPLAY}`, color: C.text3, letterSpacing: "0.07em",
                textTransform: "uppercase", marginBottom: 10,
              }}>{sec.title}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
                {sec.lines.map((ln, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <span style={{ fontSize: 19, width: 26, textAlign: "center" }}>{ln.icon}</span>
                    <span style={{ font: `700 16px ${FONT_DISPLAY}`, color: ln.warn ? "#9a6a1e" : C.text1 }}>
                      {ln.text}{ln.warn ? " ⚠️" : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Copy report — subtle outline button, no heavy bar */}
        <div style={{ padding: "14px 22px", borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: "center" }}>
          <Button variant="ghost" onClick={copyReport}>
            {copied ? "Copied ✓ — paste into your message" : "Copy report for founder"}
          </Button>
        </div>
      </div>
    </div>
  );
}
