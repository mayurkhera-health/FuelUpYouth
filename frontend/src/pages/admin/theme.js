// Admin design tokens — "TeamCoach aligned". Updating values here re-skins the
// whole admin, since components reference C.* tokens.
export const C = {
  // Brand
  brandDeep: "#123D2F",   // sidebar background, primary dark
  brand:     "#1E5A45",   // primary buttons, interactive elements
  brandMid:  "#CBEA58",   // performance lime — active dots, accents (use sparingly on dark)
  brandLight:"#a8d86e",   // lighter lime variant
  brandPale: "#EAF2EC",   // pale green — active/highlight backgrounds
  brandGhost:"#F0F6F1",   // very light green (healthy banner)

  // Warm accent (warnings, amber states)
  warm:      "#B86600",
  warmLight: "#FFF4DD",

  // Text (aligned with TC palette)
  text1: "#17231D",       // headings
  text2: "#65716B",       // body / secondary
  text3: "#65716B",       // muted labels

  // Surfaces
  bg:       "#F7F5ED",    // page background — warm cream
  surface:  "#FFFFFF",
  surface2: "#F0F4F0",    // subtle surfaces / tag backgrounds
  border:   "#DCE4DE",
  border2:  "#C8D5CC",

  // Semantic
  danger:       "#ef4444",
  dangerBg:     "#fef2f2",
  dangerBorder: "#fecaca",

  // Shadows
  shadowSm: "0 1px 3px rgba(18, 61, 47, 0.07)",
  shadowMd: "0 8px 24px rgba(18, 61, 47, 0.10)",

  // Navigation sidebar (dark)
  sidebarBg:       "#123D2F",
  sidebarText:     "#ffffff",
  sidebarInactive: "rgba(255,255,255,0.60)",
  sidebarActiveBg: "rgba(203,234,88,0.13)",
  sidebarActiveBar:"#CBEA58",
};

export const FONT_DISPLAY = "'Hanken Grotesk','Nunito','DM Sans',sans-serif";
export const FONT_BODY = "'Hanken Grotesk','DM Sans',sans-serif";

// Status tags (Label SM). Keys map to the at-risk operational signals.
export const CHIP_META = {
  no_athletes:     { label: "No athletes",     fg: "#65716B", bg: "#F0F4F0",  border: "#DCE4DE" },
  never_connected: { label: "Never connected", fg: "#92400e", bg: "#FFF4DD",  border: "#F5CB6B" },
  sync_stale:      { label: "Sync stale",      fg: "#b91c1c", bg: "#fef2f2",  border: "#fecaca" },
};
