import { useState } from "react";
import { getToken, clearToken } from "./adminApi";
import { C, FONT_DISPLAY } from "./theme";
import AdminLogin from "./AdminLogin";
import AdminUsers from "./AdminUsers";
import AdminFamilyDetail from "./AdminFamilyDetail";
import AdminAnalytics from "./AdminAnalytics";

export default function AdminApp() {
  const [authed, setAuthed] = useState(!!getToken());
  const [section, setSection] = useState("users"); // "users" | "analytics"
  const [openParentId, setOpenParentId] = useState(null);

  // Called by child fetches when a 401 (AuthError) bubbles up.
  function onLoggedOut() {
    clearToken();
    setAuthed(false);
    setOpenParentId(null);
  }

  if (!authed) return <AdminLogin onAuth={() => setAuthed(true)} />;

  const navItem = (key, label) => (
    <button
      key={key}
      onClick={() => { setSection(key); setOpenParentId(null); }}
      style={{
        display: "block", width: "100%", textAlign: "left", cursor: "pointer",
        font: `700 14px ${FONT_DISPLAY}`, padding: "10px 14px", borderRadius: 10,
        border: "none", marginBottom: 4,
        background: section === key ? C.brandGhost : "transparent",
        color: section === key ? C.brand : C.text2,
      }}
    >{label}</button>
  );

  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", font: `400 14px ${FONT_DISPLAY}` }}>
      <aside style={{
        width: 210, borderRight: `1px solid ${C.border}`, background: C.surface,
        padding: "22px 14px", flexShrink: 0, display: "flex", flexDirection: "column",
      }}>
        <div style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text1, padding: "0 8px 20px" }}>
          FuelUp Admin
        </div>
        {navItem("users", "Users")}
        {navItem("analytics", "Analytics")}
        <div style={{ flex: 1 }} />
        <button onClick={onLoggedOut} style={{
          font: `600 13px ${FONT_DISPLAY}`, color: C.text3, background: "transparent",
          border: `1px solid ${C.border}`, borderRadius: 8, padding: "8px 12px", cursor: "pointer",
        }}>Log out</button>
      </aside>

      <main style={{ flex: 1, padding: "28px 32px", maxWidth: 1100, margin: "0 auto", width: "100%" }}>
        {section === "users" && (
          openParentId
            ? <AdminFamilyDetail
                parentId={openParentId}
                onBack={() => setOpenParentId(null)}
                onLoggedOut={onLoggedOut}
              />
            : <AdminUsers onOpenFamily={setOpenParentId} onLoggedOut={onLoggedOut} />
        )}
        {section === "analytics" && <AdminAnalytics onLoggedOut={onLoggedOut} />}
      </main>
    </div>
  );
}
