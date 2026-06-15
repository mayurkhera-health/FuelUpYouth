import { useState } from "react";

/**
 * TextCapture — type-to-log sheet.
 * Submit disabled until non-trivial content (> 3 chars after trim).
 * Fires onLogged({ method:'text', text }) on submit.
 */
export default function TextCapture({ window: win, onLogged, onClose }) {
  const [text, setText] = useState("");
  const isReady = text.trim().length > 3;

  function handleSubmit() {
    if (!isReady) return;
    onLogged({ method: "text", text: text.trim() });
  }

  function handleKey(e) {
    // Ctrl/Cmd+Enter submits
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleSubmit();
  }

  return (
    <>
      <div style={s.backdrop} onClick={onClose} />
      <div style={s.sheet}>
        <div style={s.header}>
          <div style={s.title}>Type what you ate</div>
          <div style={s.subtitle}>A few words is plenty</div>
        </div>

        <div style={s.body}>
          <textarea
            style={s.input}
            placeholder="e.g. turkey sandwich, banana, water"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKey}
            rows={3}
            autoFocus
          />

          <button
            style={{
              ...s.submitBtn,
              opacity: isReady ? 1 : 0.4,
              cursor: isReady ? "pointer" : "default",
            }}
            onClick={handleSubmit}
            disabled={!isReady}
          >
            Log it ✓
          </button>

          <button style={s.cancel} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </>
  );
}

const s = {
  backdrop: {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 200,
  },
  sheet: {
    position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 201,
    background: "#fff", borderRadius: "20px 20px 0 0",
    padding: "0 16px 36px",
    boxShadow: "0 -8px 32px rgba(27,67,50,0.12)",
    fontFamily: "'DM Sans', sans-serif",
    maxWidth: "520px", margin: "0 auto",
  },
  header: {
    paddingTop: "20px", paddingBottom: "16px",
    borderBottom: "1px solid #dce8e0", textAlign: "center",
  },
  title: {
    fontFamily: "'Nunito', sans-serif", fontSize: "20px", fontWeight: "800",
    color: "#1b3a2a", marginBottom: "4px",
  },
  subtitle: { fontSize: "13px", color: "#4a6358" },

  body: {
    paddingTop: "16px",
    display: "flex", flexDirection: "column", gap: "10px",
  },
  input: {
    width: "100%", border: "1.5px solid #dce8e0", borderRadius: "12px",
    padding: "12px 14px", fontSize: "15px", color: "#1b3a2a",
    fontFamily: "'DM Sans', sans-serif", resize: "vertical",
    outline: "none", background: "#f4f8f5",
    boxSizing: "border-box", lineHeight: "1.5",
  },
  submitBtn: {
    width: "100%", background: "#2d6a4f", color: "#fff",
    border: "none", borderRadius: "12px", padding: "14px",
    fontSize: "16px", fontWeight: "700",
    fontFamily: "'Nunito', sans-serif",
  },
  cancel: {
    width: "100%", background: "none", border: "none",
    padding: "12px", fontSize: "15px", fontWeight: "600",
    color: "#4a6358", cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
  },
};
