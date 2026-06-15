/**
 * LogDuo — compact on-card logging entry.
 * Two equal pill buttons (Photo + Say it) side by side.
 * "or type it instead" text link below.
 * Photo disables gracefully if camera is unavailable; voice carries on.
 */
export default function LogDuo({ window: win, cameraAvailable, onPhoto, onVoice, onText }) {
  return (
    <div style={s.wrap}>
      <div style={s.row}>
        <button
          style={{
            ...s.btn,
            ...(cameraAvailable ? s.photoOn : s.photoOff),
          }}
          onClick={cameraAvailable ? onPhoto : undefined}
          disabled={!cameraAvailable}
          aria-label={cameraAvailable ? "Log with photo" : "Camera unavailable"}
        >
          <span style={s.icon}>📸</span>
          <span>{cameraAvailable ? "Photo" : "Not now"}</span>
        </button>

        <button style={{ ...s.btn, ...s.voiceBtn }} onClick={onVoice} aria-label="Log with voice">
          <span style={s.icon}>🎙️</span>
          <span>Say it</span>
        </button>
      </div>

      {!cameraAvailable && (
        <div style={s.cameraNote}>
          Camera blocked or off? Just tap Say it — or type it. Same result.
        </div>
      )}

      <button style={s.textLink} onClick={onText}>
        or type it instead
      </button>
    </div>
  );
}

const s = {
  wrap: { marginTop: "10px" },

  row: { display: "flex", gap: "8px" },

  btn: {
    flex: 1,
    display: "flex", alignItems: "center", justifyContent: "center",
    gap: "5px", padding: "8px 0",
    borderRadius: "100px", border: "none",
    fontSize: "14px", fontWeight: "700",
    fontFamily: "'Nunito', sans-serif",
    cursor: "pointer", lineHeight: 1,
  },

  photoOn:  { background: "#2d6a4f", color: "#fff" },
  photoOff: { background: "#e0e8e4", color: "#8aa898", cursor: "not-allowed" },
  voiceBtn: { background: "#4a8fc4", color: "#fff" },

  icon: { fontSize: "15px" },

  cameraNote: {
    marginTop: "8px",
    fontSize: "11px", color: "#4a6358", lineHeight: "1.4",
    background: "#fdf5e7", border: "1px solid #f4d3a0",
    borderRadius: "8px", padding: "7px 10px",
    textAlign: "center",
  },

  textLink: {
    display: "block", width: "100%", background: "none", border: "none",
    padding: "8px 0 2px", fontSize: "12px", color: "#4a6358",
    cursor: "pointer", textAlign: "center",
    fontFamily: "'DM Sans', sans-serif",
    textDecoration: "underline", textUnderlineOffset: "2px",
  },
};
