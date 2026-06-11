export default function MissionItem({ item, isDone, onToggle }) {
  const state = isDone ? "done" : item.state;
  const tag   = isDone ? "DONE" : item.tag;

  const boxStyle = {
    done:     { border: "1px solid rgba(45,106,79,.3)", background: "rgba(45,106,79,.12)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "19px", color: "#2d6a4f" },
    urgent:   { border: "1.5px solid rgba(180,83,9,.5)", background: "rgba(180,83,9,.08)" },
    build:    { border: "1.5px solid rgba(180,83,9,.35)", background: "rgba(217,119,6,.08)" },
    pending:  { border: "1.5px solid #dce8e0", background: "transparent" },
  };

  const tagStyle = {
    DONE:     { background: "rgba(45,106,79,.10)",  color: "#2d6a4f" },
    NOW:      { background: "rgba(180,83,9,.12)",   color: "#b45309", animation: "fuelup-pulse 1.4s infinite" },
    BOOST:    { background: "rgba(37,99,235,.10)",  color: "#1d4ed8" },
    UPCOMING: { background: "#f4f8f5",              color: "#4a6358" },
  };

  return (
    <div style={{ ...s.row, opacity: isDone ? 0.55 : 1 }} onClick={onToggle}>
      <div style={{ ...s.checkBox, ...(boxStyle[state] || boxStyle.pending) }}>
        {state === "done" ? "✓" : null}
      </div>
      <div style={s.body}>
        <div style={{ ...s.label, ...(isDone ? s.labelDone : {}) }}>{item.label}</div>
        {item.sub && (
          <div
            style={s.sub}
            dangerouslySetInnerHTML={{ __html: item.sub }}
          />
        )}
      </div>
      <div style={s.right}>
        <span style={s.time}>{item.time}</span>
        <span style={{ ...s.tag, ...(tagStyle[tag] || tagStyle.UPCOMING) }}>{tag}</span>
      </div>
    </div>
  );
}

const s = {
  row:       { display: "flex", alignItems: "flex-start", gap: "10px", padding: "13px 14px", borderBottom: "1px solid #dce8e0", cursor: "pointer" },
  checkBox:  { width: "22px", height: "22px", borderRadius: "5px", flexShrink: 0, marginTop: "1px" },
  body:      { flex: 1 },
  label:     { fontSize: "22px", fontWeight: "600", color: "#1b3a2a", lineHeight: "1.3", marginBottom: "3px" },
  labelDone: { textDecoration: "line-through", color: "#4a6358" },
  sub:       { fontSize: "20px", color: "#4a6358", fontWeight: "400", lineHeight: "1.4" },
  right:     { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px", flexShrink: 0 },
  time:      { fontSize: "19px", color: "#4a6358", fontWeight: "400" },
  tag:       { fontSize: "18px", fontWeight: "600", letterSpacing: ".04em", padding: "3px 8px", borderRadius: "3px" },
};
