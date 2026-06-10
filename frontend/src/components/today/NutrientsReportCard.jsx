const GRADE_COLOR = {
  "A": "#2d6a4f", "B+": "#2d6a4f", "B": "#52b788",
  "B-": "#d97706", "C+": "#d97706", "C": "#d97706",
  "D": "#dc2626", "F": "#dc2626",
};

const gapAccent = pct => pct < 40 ? "#dc2626" : pct < 75 ? "#d97706" : "#2d6a4f";

export default function NutrientsReportCard({ letterGrade, positiveRows = [], gapRows = [] }) {
  const gradeColor = GRADE_COLOR[letterGrade] || "#8aa898";

  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.headerLabel}>Today's nutrients</span>
        <span style={{ ...s.grade, color: gradeColor }}>{letterGrade || "—"}</span>
      </div>

      {positiveRows.length > 0 && (
        <div style={s.section}>
          {positiveRows.map((row, i) => (
            <div key={i} style={s.posRow}>
              <div style={s.checkBox}><span style={{ fontSize: "13px" }}>✓</span></div>
              <div style={s.posText}>{row.icon} {row.text}</div>
              <div style={s.posPct}>{row.pct}</div>
            </div>
          ))}
        </div>
      )}

      {gapRows.length > 0 && (
        <div style={{ borderTop: positiveRows.length > 0 ? "1px solid #dce8e0" : "none" }}>
          {gapRows.map((row, i) => {
            const accent = gapAccent(row.pct);
            return (
              <div key={i} style={s.gapRow}>
                <div style={{ ...s.gapAccentBar, background: accent }} />
                <div style={s.gapIcon}>{row.icon}</div>
                <div style={s.gapBody}>
                  <div style={s.gapName}>{row.name}</div>
                  <div style={s.gapDetail}>{row.detail}</div>
                </div>
                <div style={s.gapRight}>
                  <div style={{ ...s.gapPct, color: accent }}>{row.pct}%</div>
                  <div style={s.gapTarget}>{row.target}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {positiveRows.length === 0 && gapRows.length === 0 && (
        <div style={s.empty}>Log meals to see your nutrient breakdown.</div>
      )}
    </div>
  );
}

const s = {
  card:        { background: "#ffffff", border: "1.5px solid #dce8e0", borderRadius: "12px", overflow: "hidden", marginTop: "8px" },
  header:      { padding: "12px 14px 10px", borderBottom: "1px solid #dce8e0", display: "flex", justifyContent: "space-between", alignItems: "center" },
  headerLabel: { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#4a6358" },
  grade:       { fontSize: "16px", fontWeight: "800", fontFamily: "'Nunito', sans-serif" },
  section:     {},
  posRow:      { display: "flex", alignItems: "center", gap: "10px", padding: "9px 14px" },
  checkBox:    { width: "20px", height: "20px", borderRadius: "5px", background: "rgba(82,183,136,0.12)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "#2d6a4f" },
  posText:     { flex: 1, fontSize: "14px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "#1b3a2a" },
  posPct:      { fontSize: "14px", fontWeight: "700", fontFamily: "'Nunito', sans-serif", color: "#2d6a4f", flexShrink: 0 },
  gapRow:      { display: "flex", alignItems: "flex-start", gap: "8px", padding: "9px 14px 9px 0" },
  gapAccentBar:{ width: "2px", borderRadius: "2px", alignSelf: "stretch", flexShrink: 0, marginLeft: "4px" },
  gapIcon:     { fontSize: "18px", flexShrink: 0, marginTop: "1px" },
  gapBody:     { flex: 1, minWidth: 0 },
  gapName:     { fontSize: "14px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", color: "#1b3a2a", marginBottom: "2px" },
  gapDetail:   { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "#4a6358", lineHeight: 1.5 },
  gapRight:    { flexShrink: 0, textAlign: "right" },
  gapPct:      { fontSize: "16px", fontWeight: "800", fontFamily: "'Nunito', sans-serif", letterSpacing: "-0.02em" },
  gapTarget:   { fontSize: "11px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "#4a6358" },
  empty:       { padding: "14px", fontSize: "14px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif", textAlign: "center" },
};
