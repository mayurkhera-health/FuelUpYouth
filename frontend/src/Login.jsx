import { useState, useEffect } from "react";

const API = import.meta.env.VITE_API_URL ?? "";

const FEATURES = [
  { icon: "🧠", title: "AI Nutrition Blueprints", desc: "Personalized plans built around each athlete's age, position, game schedule, and dietary needs." },
  { icon: "📅", title: "Game-Day Fuel Protocols", desc: "Exact meals and timing for pre-game, halftime, and recovery — never guess again." },
  { icon: "📊", title: "Live Macro Tracking", desc: "Log meals and watch real-time dials update against science-backed daily targets." },
  { icon: "💧", title: "Hydration Calculator", desc: "Sweat-rate estimates based on age, competition level, and weather conditions." },
];

const RESEND_COOLDOWN = 60; // seconds

export default function Login({ onLogin, onNewAccount }) {
  const [step, setStep]       = useState("email"); // "email" | "code"
  const [email, setEmail]     = useState("");
  const [code, setCode]       = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [cooldown, setCooldown] = useState(0);

  // Countdown timer for resend cooldown
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  async function handleRequestCode(e) {
    e.preventDefault();
    if (!email.trim()) return setError("Please enter your email address.");
    // Dev shortcut
    if (email.trim().toLowerCase() === "test@gmail.com") { onNewAccount(); return; }
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API}/api/parents/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await res.json();
      if (res.status === 404) { setError("No account found with that email. Did you mean to create a new account?"); return; }
      if (res.status === 429) { setError(data.detail); return; }
      if (!res.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
      setStep("code");
      setCooldown(RESEND_COOLDOWN);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  async function handleVerifyCode(e) {
    e.preventDefault();
    if (code.trim().length !== 6) return setError("Please enter the 6-digit code from your email.");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API}/api/parents/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Invalid code. Please try again."); return; }
      onLogin(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  async function handleResend() {
    if (cooldown > 0) return;
    setError(""); setLoading(true);
    try {
      const res = await fetch(`${API}/api/parents/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setCooldown(RESEND_COOLDOWN);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div style={s.wrapper}>

      {/* ── Left panel — hero copy ── */}
      <div style={s.hero}>
        <div style={s.wordmark}>⚽ FuelUp<span style={s.wordmarkYouth}>Youth</span></div>
        <h1 style={s.headline}>
          The complete nutrition platform for every competitive soccer athlete.
        </h1>
        <p style={s.subheadline}>
          AI-generated, RD-approved Nutrition Blueprints — personalized to every athlete's age,
          training schedule, game days, dietary needs, and performance goals.
          Built for youth soccer clubs, ages&nbsp;9–17.
        </p>
        <div style={s.features}>
          {FEATURES.map(f => (
            <div key={f.title} style={s.featureCard}>
              <div style={s.featureIcon}>{f.icon}</div>
              <div>
                <div style={s.featureTitle}>{f.title}</div>
                <div style={s.featureDesc}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel — sign-in card ── */}
      <div style={s.panel}>
        <div style={s.card}>
          <div style={s.cardLogo}>⚽ FuelUp</div>

          {step === "email" ? (
            <>
              <h2 style={s.cardTitle}>Welcome back</h2>
              <p style={s.cardDesc}>Enter your parent email and we'll send you a sign-in code.</p>

              <form onSubmit={handleRequestCode}>
                <label style={s.label}>Parent Email</label>
                <input
                  style={s.input}
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => { setEmail(e.target.value); setError(""); }}
                  autoFocus
                />
                {error && <p style={s.error}>{error}</p>}
                <button style={s.btn} type="submit" disabled={loading}>
                  {loading ? "Sending code…" : "Send Sign-In Code →"}
                </button>
              </form>

              <div style={s.divider}>
                <div style={s.dividerLine} />
                <span style={s.dividerText}>or</span>
                <div style={s.dividerLine} />
              </div>

              <button style={s.newBtn} onClick={onNewAccount}>
                Create a new account
              </button>
            </>
          ) : (
            <>
              <h2 style={s.cardTitle}>Check your email</h2>
              <p style={s.cardDesc}>
                We sent a 6-digit code to<br />
                <strong style={{ color: "#2d6a4f" }}>{email}</strong>
              </p>

              <form onSubmit={handleVerifyCode}>
                <label style={s.label}>6-Digit Code</label>
                <input
                  style={{ ...s.input, ...s.codeInput }}
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  maxLength={6}
                  value={code}
                  onChange={e => { setCode(e.target.value.replace(/\D/g, "")); setError(""); }}
                  autoFocus
                />
                {error && <p style={s.error}>{error}</p>}
                <button style={s.btn} type="submit" disabled={loading}>
                  {loading ? "Verifying…" : "Sign In →"}
                </button>
              </form>

              <div style={s.resendRow}>
                {cooldown > 0 ? (
                  <span style={s.resendCooldown}>Resend code in {cooldown}s</span>
                ) : (
                  <button style={s.resendBtn} onClick={handleResend} disabled={loading}>
                    Resend code
                  </button>
                )}
                <span style={s.resendSep}>·</span>
                <button style={s.backBtn} onClick={() => { setStep("email"); setCode(""); setError(""); }}>
                  Change email
                </button>
              </div>
            </>
          )}

          <p style={s.disclaimer}>
            FuelUp provides educational food guidance — not medical nutrition therapy.
          </p>
        </div>
      </div>

    </div>
  );
}

const s = {
  wrapper: {
    minHeight: "100vh",
    background: "linear-gradient(145deg, #1b4332 0%, #2d6a4f 50%, #3a7d60 100%)",
    display: "flex",
    alignItems: "stretch",
    fontFamily: "'Nunito', 'DM Sans', sans-serif",
  },

  // ── Hero (left) ──
  hero: {
    flex: "1 1 0",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    padding: "60px 56px",
    maxWidth: "640px",
    position: "relative",
    overflow: "hidden",
  },
  wordmark: {
    fontSize: "34px",
    fontWeight: "900",
    color: "#ffffff",
    letterSpacing: "-0.5px",
    marginBottom: "20px",
    fontFamily: "'Nunito', sans-serif",
  },
  wordmarkYouth: { color: "#95d5b2", fontWeight: "500", marginLeft: "6px" },
  headline: {
    fontSize: "clamp(24px, 3vw, 36px)",
    fontWeight: "800",
    color: "#ffffff",
    lineHeight: 1.25,
    letterSpacing: "-0.3px",
    margin: "0 0 16px",
    fontFamily: "'Nunito', sans-serif",
  },
  subheadline: {
    fontSize: "15px",
    color: "rgba(183,228,199,0.9)",
    lineHeight: 1.7,
    marginBottom: "32px",
    maxWidth: "500px",
  },
  features: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" },
  featureCard: {
    background: "rgba(255,255,255,0.08)",
    border: "1px solid rgba(255,255,255,0.13)",
    backdropFilter: "blur(4px)",
    borderRadius: "14px",
    padding: "15px",
    display: "flex",
    gap: "10px",
    alignItems: "flex-start",
  },
  featureIcon: { fontSize: "20px", flexShrink: 0, marginTop: "1px" },
  featureTitle: { fontSize: "13px", fontWeight: "700", color: "#ffffff", marginBottom: "3px", fontFamily: "'Nunito', sans-serif" },
  featureDesc: { fontSize: "11.5px", color: "rgba(183,228,199,0.85)", lineHeight: 1.5 },

  // ── Sign-in panel (right) ──
  panel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px",
    flexShrink: 0,
    width: "420px",
    background: "#f4f8f5",
  },
  card: {
    background: "#ffffff",
    borderRadius: "20px",
    padding: "36px 32px",
    width: "100%",
    boxShadow: "0 16px 48px rgba(27,67,50,0.14)",
    border: "1px solid #dce8e0",
  },
  cardLogo: {
    fontSize: "22px",
    fontWeight: "900",
    color: "#2d6a4f",
    textAlign: "center",
    marginBottom: "18px",
    fontFamily: "'Nunito', sans-serif",
  },
  cardTitle: {
    fontSize: "22px",
    fontWeight: "800",
    color: "#1b3a2a",
    margin: "0 0 6px",
    textAlign: "center",
    fontFamily: "'Nunito', sans-serif",
  },
  cardDesc: {
    fontSize: "13px",
    color: "#8aa898",
    textAlign: "center",
    lineHeight: 1.6,
    marginBottom: "22px",
  },
  label: {
    display: "block",
    fontSize: "11px",
    fontWeight: "700",
    color: "#4a6358",
    marginBottom: "6px",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    fontFamily: "'Nunito', sans-serif",
  },
  input: {
    width: "100%",
    padding: "11px 14px",
    border: "1.5px solid #dce8e0",
    borderRadius: "10px",
    fontSize: "15px",
    fontFamily: "'DM Sans', sans-serif",
    outline: "none",
    boxSizing: "border-box",
    marginBottom: "12px",
    background: "#f4f8f5",
    color: "#1b3a2a",
    transition: "border-color 0.2s, box-shadow 0.2s",
  },
  codeInput: {
    fontSize: "28px",
    fontFamily: "'Nunito', sans-serif",
    fontWeight: "800",
    letterSpacing: "10px",
    textAlign: "center",
    padding: "14px",
  },
  error: { color: "#dc2626", fontSize: "13px", marginBottom: "10px", marginTop: "-6px" },
  btn: {
    width: "100%",
    padding: "13px",
    background: "linear-gradient(135deg, #2d6a4f, #52b788)",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    fontSize: "15px",
    fontWeight: "700",
    fontFamily: "'Nunito', sans-serif",
    cursor: "pointer",
    letterSpacing: "0.01em",
    boxShadow: "0 4px 14px rgba(45,106,79,0.28)",
    transition: "opacity 0.2s",
  },

  divider: { display: "flex", alignItems: "center", margin: "18px 0", gap: "12px" },
  dividerLine: { flex: 1, height: "1px", background: "#dce8e0" },
  dividerText: { fontSize: "12px", color: "#8aa898", padding: "0 4px", flexShrink: 0 },

  newBtn: {
    width: "100%",
    padding: "12px",
    background: "transparent",
    color: "#2d6a4f",
    border: "1.5px solid #95d5b2",
    borderRadius: "10px",
    fontSize: "14px",
    fontWeight: "700",
    fontFamily: "'Nunito', sans-serif",
    cursor: "pointer",
  },

  resendRow: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "8px",
    marginTop: "14px",
  },
  resendBtn: {
    background: "none",
    border: "none",
    color: "#2d6a4f",
    fontSize: "13px",
    fontWeight: "700",
    fontFamily: "'Nunito', sans-serif",
    cursor: "pointer",
    padding: 0,
    textDecoration: "underline",
  },
  resendCooldown: {
    fontSize: "13px",
    color: "#8aa898",
    fontFamily: "'DM Sans', sans-serif",
  },
  resendSep: { color: "#dce8e0", fontSize: "14px" },
  backBtn: {
    background: "none",
    border: "none",
    color: "#8aa898",
    fontSize: "13px",
    fontFamily: "'DM Sans', sans-serif",
    cursor: "pointer",
    padding: 0,
    textDecoration: "underline",
  },

  disclaimer: {
    fontSize: "11px",
    color: "#8aa898",
    textAlign: "center",
    marginTop: "20px",
    lineHeight: 1.6,
  },
};
