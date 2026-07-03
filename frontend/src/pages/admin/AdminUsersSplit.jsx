import { useEffect, useState } from "react";
import { C, FONT_DISPLAY } from "./theme";
import AdminUsers from "./AdminUsers";
import AdminFamilyDetail from "./AdminFamilyDetail";

// Split-pane (master-detail) Users view: family directory on the left, the
// selected family's detail on the right. Collapses to a single pane on narrow
// screens (list → detail with a back button).
function useNarrow(bp = 900) {
  const [narrow, setNarrow] = useState(typeof window !== "undefined" && window.innerWidth < bp);
  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < bp);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [bp]);
  return narrow;
}

export default function AdminUsersSplit({ onLoggedOut }) {
  const [selectedId, setSelectedId] = useState(null);
  const narrow = useNarrow();

  const master = <AdminUsers selectedId={selectedId} onSelect={setSelectedId} onLoggedOut={onLoggedOut} />;
  const detail = selectedId
    ? <AdminFamilyDetail parentId={selectedId} onBack={() => setSelectedId(null)} onLoggedOut={onLoggedOut} hideBack={!narrow} />
    : <EmptyDetail />;

  if (narrow) {
    return <div>{selectedId ? detail : master}</div>;
  }

  return (
    <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
      <div style={{ width: 400, flexShrink: 0 }}>{master}</div>
      <div style={{ flex: 1, minWidth: 0 }}>{detail}</div>
    </div>
  );
}

function EmptyDetail() {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      textAlign: "center", minHeight: 420, background: C.surface, border: `1px solid ${C.border}`,
      borderRadius: 18, color: C.text3, padding: 40,
    }}>
      <div style={{ fontSize: 42, marginBottom: 12 }}>👥</div>
      <div style={{ font: `800 18px ${FONT_DISPLAY}`, color: C.text2 }}>Select a family</div>
      <div style={{ font: `400 14px ${FONT_DISPLAY}`, marginTop: 6, maxWidth: 320 }}>
        Pick someone from the list to see their profile, athletes, and activity.
      </div>
    </div>
  );
}
