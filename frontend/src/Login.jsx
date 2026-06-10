import { useState } from "react";

const API = import.meta.env.VITE_API_URL ?? "";

const FEATURES = [
  { icon: "🧠", title: "AI Nutrition Blueprints", desc: "Personalized plans built around each athlete's age, position, game schedule, and dietary needs." },
  { icon: "📅", title: "Game-Day Fuel Protocols", desc: "Exact meals and timing for pre-game, halftime, and recovery — never guess again." },
  { icon: "📊", title: "Live Macro Tracking", desc: "Log meals and watch real-time dials update against science-backed daily targets." },
  { icon: "💧", title: "Hydration Calculator", desc: "Sweat-rate estimates based on age, competition level, and weather conditions." },
];

export default function Login({ onLogin, onNewAccount }) {
  const [email, setEmail]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim()) return setError("Please enter your email address.");
    if (email.trim().toLowerCase() === "test@gmail.com") { onNewAccount(); return; }
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API}/api/parents/login?email=${encodeURIComponent(email.trim().toLowerCase())}`);
      if (res.status === 404) { setError("No account found with that email. Did you mean to create a new account?"); return; }
      if (!res.ok) throw new Error("Something went wrong. Please try again.");
      onLogin(await res.json());
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div style={s.wrapper}>

      {/* ── Left panel — hero copy ── */}
      <div style={s.hero}>
        {/* Badge */}
        <div style={s.badge}>RD-Approved · Ages 9–17 · Youth Soccer</div>

        {/* Wordmark */}
        <div style={s.wordmark}>⚽ FuelUp<span style={s.wordmarkYouth}>Youth</span></div>

        {/* Headline */}
        <h1 style={s.headline}>
          The complete nutrition platform for every competitive soccer athlete.
        </h1>

        {/* Sub-headline */}
        <p style={s.subheadline}>
          AI-generated, RD-approved Nutrition Blueprints — personalized to every athlete's age,
          training schedule, game days, dietary needs, and performance goals.
          Built for youth soccer clubs, ages&nbsp;9–17.
        </p>

        {/* Feature grid */}
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
          <h2 style={s.cardTitle}>Welcome back</h2>
          <p style={s.cardDesc}>Enter your parent email to access your athlete's nutrition plan.</p>

          <form onSubmit={handleSubmit}>
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
              {loading ? "Looking up account…" : "Sign In →"}
            </button>
          </form>

          <div style={s.divider}><span style={s.dividerText}>or</span></div>

          <button style={s.newBtn} onClick={onNewAccount}>
            Create a new account
          </button>

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
    background: "linear-gradient(145deg, #0a3324 0%, #0f4c35 45%, #155e42 100%)",
    display: "flex",
    alignItems: "stretch",
    fontFamily: "'Inter', -apple-system, sans-serif",
  },

  // ── Hero (left) ──
  hero: {
    flex: "1 1 0",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    padding: "60px 56px",
    maxWidth: "640px",
  },
  badge: {
    display: "inline-block",
    background: "rgba(255,255,255,0.12)",
    border: "1px solid rgba(255,255,255,0.25)",
    color: "#a7f3d0",
    fontSize: "12px",
    fontWeight: "700",
    letterSpacing: "0.07em",
    textTransform: "uppercase",
    padding: "5px 14px",
    borderRadius: "99px",
    marginBottom: "24px",
    width: "fit-content",
  },
  wordmark: {
    fontSize: "32px",
    fontWeight: "900",
    color: "#ffffff",
    letterSpacing: "-0.5px",
    marginBottom: "20px",
  },
  wordmarkYouth: {
    color: "#6ee7b7",
    fontWeight: "400",
    marginLeft: "6px",
  },
  headline: {
    fontSize: "clamp(26px, 3vw, 38px)",
    fontWeight: "800",
    color: "#ffffff",
    lineHeight: 1.2,
    letterSpacing: "-0.5px",
    margin: "0 0 18px",
  },
  subheadline: {
    fontSize: "16px",
    color: "#a7f3d0",
    lineHeight: 1.7,
    marginBottom: "36px",
    maxWidth: "520px",
  },
  features: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "14px",
    marginBottom: "36px",
  },
  featureCard: {
    background: "rgba(255,255,255,0.08)",
    border: "1px solid rgba(255,255,255,0.14)",
    borderRadius: "12px",
    padding: "16px",
    display: "flex",
    gap: "12px",
    alignItems: "flex-start",
  },
  featureIcon: { fontSize: "22px", flexShrink: 0, marginTop: "1px" },
  featureTitle: { fontSize: "13px", fontWeight: "700", color: "#ffffff", marginBottom: "4px" },
  featureDesc: { fontSize: "12px", color: "#86efac", lineHeight: 1.5 },
  scienceLine: {
    fontSize: "11px",
    color: "rgba(255,255,255,0.4)",
    letterSpacing: "0.03em",
  },

  // ── Sign-in panel (right) ──
  panel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px 40px",
    flexShrink: 0,
    width: "420px",
    background: "rgba(0,0,0,0.15)",
    backdropFilter: "blur(10px)",
  },
  card: {
    background: "#ffffff",
    borderRadius: "20px",
    padding: "36px 32px",
    width: "100%",
    boxShadow: "0 32px 72px rgba(0,0,0,0.35)",
  },
  cardLogo: {
    fontSize: "22px",
    fontWeight: "800",
    color: "#0f4c35",
    textAlign: "center",
    marginBottom: "20px",
  },
  cardTitle: {
    fontSize: "22px",
    fontWeight: "700",
    color: "#111827",
    margin: "0 0 6px",
    textAlign: "center",
  },
  cardDesc: {
    fontSize: "13px",
    color: "#6b7280",
    textAlign: "center",
    lineHeight: 1.5,
    marginBottom: "24px",
  },
  label: { display: "block", fontSize: "12px", fontWeight: "700", color: "#374151", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { width: "100%", padding: "11px 14px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "15px", outline: "none", boxSizing: "border-box", marginBottom: "12px", transition: "border-color 0.2s" },
  error: { color: "#dc2626", fontSize: "13px", marginBottom: "10px", marginTop: "-6px" },
  btn: { width: "100%", padding: "13px", background: "#0f4c35", color: "#fff", border: "none", borderRadius: "10px", fontSize: "15px", fontWeight: "700", cursor: "pointer", letterSpacing: "0.01em" },

  divider: { display: "flex", alignItems: "center", margin: "20px 0", gap: "12px" },
  dividerText: { fontSize: "12px", color: "#9ca3af", background: "#fff", padding: "0 4px", flexShrink: 0 },

  newBtn: { width: "100%", padding: "12px", background: "transparent", color: "#0f4c35", border: "1.5px solid #0f4c35", borderRadius: "10px", fontSize: "14px", fontWeight: "700", cursor: "pointer" },

  disclaimer: { fontSize: "11px", color: "#9ca3af", textAlign: "center", marginTop: "20px", lineHeight: 1.6 },
};
