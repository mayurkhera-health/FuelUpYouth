// Admin design tokens — mirror the app's index.css :root values so the admin
// feels like the same product. Kept as a JS object because the codebase styles
// with inline style objects (no CSS modules / Tailwind).
export const C = {
  brandDeep: "#1b4332",
  brand: "#2d6a4f",
  brandMid: "#52b788",
  brandLight: "#95d5b2",
  brandPale: "#d8f3dc",
  brandGhost: "#f0faf4",
  warm: "#e9a84c",
  warmLight: "#fdf3e0",
  text1: "#1b3a2a",
  text2: "#4a6358",
  text3: "#8aa898",
  bg: "#f4f8f5",
  surface: "#ffffff",
  surface2: "#f0f4f1",
  border: "#dce8e0",
  border2: "#c8d8d0",
  danger: "#c05a4a",
  dangerBg: "#fdf2f0",
  dangerBorder: "#f4c0b8",
  shadowSm: "0 2px 8px rgba(27,67,50,0.07)",
  shadowMd: "0 8px 24px rgba(27,67,50,0.11)",
};

export const FONT_DISPLAY = "'Nunito','DM Sans',sans-serif";
export const FONT_BODY = "'DM Sans',sans-serif";

// Chip presentation for the at-risk operational signals.
export const CHIP_META = {
  no_athletes: { label: "No athletes", fg: "#5b6b63", bg: "#eef2f0", border: "#d8e2dc" },
  never_connected: { label: "Never connected", fg: "#9a6a1e", bg: "#fdf3e0", border: "#f0d9a8" },
  sync_stale: { label: "Sync stale", fg: "#c05a4a", bg: "#fdf2f0", border: "#f4c0b8" },
};
