import { useEffect, useState } from "react";
import { getToken, clearToken, adminFetch } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import AdminLogin from "./AdminLogin";
import AdminUsersSplit from "./AdminUsersSplit";
import AdminAnalytics from "./AdminAnalytics";
import AdminHealth from "./AdminHealth";
import AdminOverview from "./AdminOverview";

// Overall health strip — one fetch per admin page load, no polling.
function HealthStrip({ onOpen }) {
  const [snap, setSnap] = useState(null);
  useEffect(() => {
    let alive = true;
    adminFetch("/health")
      .then((s) => { if (alive) setSnap(s); })
      .catch(() => {}); // strip is best-effort; never block the page
    return () => { alive = false; };
  }, []);
  if (!snap) return null;
  // Founder view: red = something's actually wrong; pending checks never alarm.
  const redCount = snap.checks.filter((c) => c.status === "red").length;
  const meta = redCount > 0
    ? { color: C.danger, bg: C.dangerBg, border: C.dangerBorder, label: `${redCount} ${redCount === 1 ? "issue needs" : "issues need"} attention` }
    : { color: C.brandMid, bg: C.brandGhost, border: C.brandLight, label: "All systems healthy" };
  return (
    <button onClick={onOpen} style={{
      display: "flex", gap: 8, alignItems: "center", width: "100%", cursor: "pointer",
      font: `700 13px ${FONT_DISPLAY}`, color: meta.color, background: meta.bg,
      border: `1px solid ${meta.border}`, borderRadius: 10, padding: "8px 14px", marginBottom: 16,
    }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: meta.color }} />
      System health: {meta.label}
      <span style={{ marginLeft: "auto", color: C.text3, fontWeight: 600 }}>View →</span>
    </button>
  );
}

export default function AdminApp() {
  const [authed, setAuthed] = useState(!!getToken());
  // Default landing = the plain-language Overview (the hourly reporter's screen).
  const [section, setSection] = useState("overview"); // "overview" | "users" | "analytics" | "health"

  // Called by child fetches when a 401 (AuthError) bubbles up.
  function onLoggedOut() {
    clearToken();
    setAuthed(false);
  }

  if (!authed) return <AdminLogin onAuth={() => setAuthed(true)} />;

  const navItem = (key, label) => {
    const active = section === key;
    return (
      <button
        key={key}
        onClick={() => setSection(key)}
        style={{
          display: "block", width: "100%", textAlign: "left", cursor: "pointer",
          font: `${active ? 700 : 600} 14px ${FONT_DISPLAY}`, padding: "11px 14px 11px 16px",
          borderRadius: 10, marginBottom: 4,
          border: "none", borderLeft: `4px solid ${active ? C.sidebarActiveBar : "transparent"}`,
          background: active ? C.sidebarActiveBg : "transparent",
          color: active ? C.sidebarText : C.sidebarInactive,
        }}
      >{label}</button>
    );
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", font: `400 14px ${FONT_DISPLAY}` }}>
      <aside style={{
        width: 240, background: C.sidebarBg, padding: "22px 12px",
        flexShrink: 0, display: "flex", flexDirection: "column",
      }}>
        <div style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.sidebarText, padding: "0 12px 22px" }}>
          FuelUp Admin
        </div>
        {navItem("overview", "Overview")}
        {navItem("users", "Users")}
        {navItem("analytics", "Analytics")}
        {navItem("health", "System Health")}
        <div style={{ flex: 1 }} />
        <button onClick={onLoggedOut} style={{
          font: `600 13px ${FONT_DISPLAY}`, color: C.sidebarInactive, background: "transparent",
          border: `1px solid rgba(255,255,255,0.2)`, borderRadius: 8, padding: "9px 12px", cursor: "pointer",
        }}>Log out</button>
      </aside>

      <main style={{ flex: 1, padding: "28px 32px", maxWidth: 1100, margin: "0 auto", width: "100%" }}>
        {/* Health strip is redundant on Overview (its own health line) and Health. */}
        {section !== "health" && section !== "overview" && (
          <HealthStrip onOpen={() => setSection("health")} />
        )}
        {section === "overview" && <AdminOverview onLoggedOut={onLoggedOut} />}
        {section === "users" && <AdminUsersSplit onLoggedOut={onLoggedOut} />}
        {section === "analytics" && <AdminAnalytics onLoggedOut={onLoggedOut} />}
        {section === "health" && <AdminHealth onLoggedOut={onLoggedOut} />}
      </main>
    </div>
  );
}
