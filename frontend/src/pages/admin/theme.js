// Admin design tokens — "Forest Modern Admin". Kept as a JS object because the
// codebase styles with inline style objects. Updating values here re-skins the
// whole admin, since components reference C.* tokens.
export const C = {
  brandDeep: "#064e3b",   // primary — sidebar background
  brand: "#065f46",       // primary buttons
  brandMid: "#10b981",    // accent green (gauges, active dots)
  brandLight: "#6ee7b7",
  brandPale: "#d1fae5",   // secondary container — active/highlight backgrounds
  brandGhost: "#ecfdf5",  // very light green (healthy banner)
  warm: "#d97706",        // amber accent (warnings)
  warmLight: "#fef3c7",   // amber container ("never connected")
  text1: "#0f172a",       // headings (slate-900)
  text2: "#475569",       // body (slate-600)
  text3: "#64748b",       // muted labels (slate-500 — keeps WCAG AA on white)
  bg: "#f8f9ff",          // page background (surface)
  surface: "#ffffff",
  surface2: "#f1f5f9",    // subtle surfaces / manual-verified tag
  border: "#e2e8f0",      // outline variant
  border2: "#cbd5e1",
  danger: "#ef4444",      // error
  dangerBg: "#fef2f2",
  dangerBorder: "#fecaca",
  shadowSm: "0 1px 3px rgba(15,23,42,0.08)",
  shadowMd: "0 8px 24px rgba(15,23,42,0.10)",

  // Navigation drawer (dark).
  sidebarBg: "#064e3b",
  sidebarText: "#ffffff",
  sidebarInactive: "rgba(255,255,255,0.72)",
  sidebarActiveBg: "rgba(255,255,255,0.10)",
  sidebarActiveBar: "#6ee7b7",
};

export const FONT_DISPLAY = "'Hanken Grotesk','Nunito','DM Sans',sans-serif";
export const FONT_BODY = "'Hanken Grotesk','DM Sans',sans-serif";

// Status tags (Label SM). Keys map to the at-risk operational signals.
export const CHIP_META = {
  no_athletes: { label: "No athletes", fg: "#475569", bg: "#f1f5f9", border: "#e2e8f0" },
  never_connected: { label: "Never connected", fg: "#92400e", bg: "#fef3c7", border: "#fde68a" },
  sync_stale: { label: "Sync stale", fg: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
};
