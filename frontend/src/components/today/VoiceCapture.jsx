import { useState, useRef, useEffect } from "react";

/**
 * VoiceCapture — records audio via MediaRecorder (browser-native).
 * Optionally captures a transcript via Web Speech API if available.
 * Fires onLogged({ method:'voice', blob, transcript }) on stop.
 * Fires onPermissionDenied() if mic access is refused.
 * Never hard-errors — falls back gracefully.
 */
export default function VoiceCapture({ window: win, onLogged, onClose, onPermissionDenied }) {
  const [phase, setPhase] = useState("starting"); // starting | recording | error
  const [transcript, setTranscript] = useState("");
  const [bars, setBars] = useState(Array(10).fill(6));

  const mediaRef      = useRef(null);
  const chunksRef     = useRef([]);
  const recognitionRef = useRef(null);

  // Auto-start on mount
  useEffect(() => {
    startRecording();
    return () => {
      mediaRef.current?.stream?.getTracks().forEach((t) => t.stop());
      try { recognitionRef.current?.stop(); } catch (_) {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Animated waveform bars while recording
  useEffect(() => {
    if (phase !== "recording") return;
    const t = setInterval(() => {
      setBars(Array(10).fill(0).map(() => Math.random() * 22 + 4));
    }, 120);
    return () => clearInterval(t);
  }, [phase]);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mediaRef.current = mr;

      // Optional Web Speech API — ignored if unavailable or erroring
      try {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
          const rec = new SpeechRec();
          rec.continuous = true;
          rec.interimResults = true;
          rec.onresult = (e) => {
            const t = Array.from(e.results).map((r) => r[0].transcript).join(" ");
            setTranscript(t);
          };
          recognitionRef.current = rec;
          rec.start();
        }
      } catch (_) {}

      mr.start();
      setPhase("recording");
    } catch (err) {
      const denied =
        err.name === "NotAllowedError" ||
        err.name === "PermissionDeniedError" ||
        err.name === "SecurityError";
      if (denied) {
        onPermissionDenied?.();
      } else {
        setPhase("error");
      }
    }
  }

  function stopRecording() {
    if (!mediaRef.current || mediaRef.current.state === "inactive") return;
    try { recognitionRef.current?.stop(); } catch (_) {}
    mediaRef.current.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      onLogged({ method: "voice", blob, transcript: transcript || null });
    };
    mediaRef.current.stop();
    mediaRef.current.stream?.getTracks().forEach((t) => t.stop());
  }

  return (
    <>
      <div style={s.backdrop} onClick={onClose} />
      <div style={s.sheet}>
        <div style={s.header}>
          <div style={s.title}>Recording…</div>
          <div style={s.subtitle}>
            Just say it — like "I had pasta with chicken and milk"
          </div>
        </div>

        <div style={s.center}>
          {phase === "recording" && (
            <>
              <div style={s.micCircle}>🎙️</div>
              <div style={s.status}>Listening…</div>
              <div style={s.wave}>
                {bars.map((h, i) => (
                  <div key={i} style={{ ...s.bar, height: `${h}px` }} />
                ))}
              </div>
              {transcript && (
                <div style={s.transcript}>"{transcript}"</div>
              )}
            </>
          )}

          {phase === "starting" && (
            <div style={s.status}>Getting mic ready…</div>
          )}

          {phase === "error" && (
            <div style={s.errorMsg}>
              Couldn't access the mic. Try a photo or type it instead.
            </div>
          )}
        </div>

        {phase === "recording" && (
          <button style={s.stopBtn} onClick={stopRecording} aria-label="Stop recording">
            <div style={s.stopSquare} />
          </button>
        )}

        <button style={s.cancel} onClick={onClose}>Cancel</button>
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
  subtitle: { fontSize: "13px", color: "#4a6358", lineHeight: "1.4" },

  center: {
    display: "flex", flexDirection: "column", alignItems: "center",
    padding: "28px 0 16px", minHeight: "140px", justifyContent: "center",
  },
  micCircle: {
    width: "88px", height: "88px", borderRadius: "50%",
    background: "rgba(74,143,196,0.12)", border: "2px solid rgba(74,143,196,0.25)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: "36px", marginBottom: "16px",
    animation: "mic-pulse 1.4s ease-in-out infinite",
  },
  status: {
    fontSize: "15px", fontWeight: "600", color: "#2d6a4f", marginBottom: "14px",
  },
  wave: {
    display: "flex", alignItems: "center", gap: "3px",
    height: "32px", marginBottom: "12px",
  },
  bar: {
    width: "3px", background: "rgba(74,143,196,0.55)",
    borderRadius: "2px", transition: "height 0.1s ease", minHeight: "4px",
  },
  transcript: {
    fontSize: "13px", color: "#4a6358", fontStyle: "italic",
    background: "#f0faf4", borderRadius: "8px", padding: "8px 12px",
    maxWidth: "280px", textAlign: "center", lineHeight: "1.4",
    marginTop: "4px",
  },
  errorMsg: {
    fontSize: "14px", color: "#c05a4a", textAlign: "center",
    padding: "0 20px", lineHeight: "1.5",
  },

  stopBtn: {
    display: "flex", alignItems: "center", justifyContent: "center",
    width: "60px", height: "60px", borderRadius: "50%",
    background: "#2d6a4f", border: "none", cursor: "pointer",
    margin: "0 auto 16px",
  },
  stopSquare: {
    width: "20px", height: "20px", background: "#fff", borderRadius: "4px",
  },

  cancel: {
    width: "100%", background: "none", border: "none",
    padding: "12px", fontSize: "15px", fontWeight: "600",
    color: "#4a6358", cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
  },
};
