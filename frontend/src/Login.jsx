import { useState } from "react";

const API = "http://localhost:8000";

export default function Login({ onLogin, onNewAccount }) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim()) return setError("Please enter your email address.");
    if (email.trim().toLowerCase() === "test@gmail.com") {
      onNewAccount();
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/parents/login?email=${encodeURIComponent(email.trim().toLowerCase())}`);
      if (res.status === 404) {
        setError("No account found with that email. Did you mean to create a new account?");
        return;
      }
      if (!res.ok) throw new Error("Something went wrong. Please try again.");
      const data = await res.json();
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.logo}>⚽ FuelUp</div>
          <div style={styles.subtitle}>Youth Soccer Nutrition Platform</div>
        </div>

        <h2 style={styles.title}>Welcome Back</h2>
        <p style={styles.desc}>Enter your email to access your athlete's nutrition plan.</p>

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Parent Email Address</label>
          <input
            style={styles.input}
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(""); }}
            autoFocus
          />
          {error && <p style={styles.error}>{error}</p>}
          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? "Looking up account…" : "Sign In →"}
          </button>
        </form>

        <div style={styles.divider} />

        <p style={styles.newAccount}>
          Don't have an account yet?{" "}
          <button style={styles.link} onClick={onNewAccount}>
            Create one here
          </button>
        </p>
      </div>
    </div>
  );
}

const styles = {
  wrapper: { minHeight: "100vh", background: "linear-gradient(135deg, #0f4c35 0%, #1a7a54 100%)", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", fontFamily: "'Inter', -apple-system, sans-serif" },
  card: { background: "#fff", borderRadius: "20px", padding: "40px", width: "100%", maxWidth: "480px", boxShadow: "0 24px 60px rgba(0,0,0,0.25)" },
  header: { textAlign: "center", marginBottom: "28px" },
  logo: { fontSize: "28px", fontWeight: "800", color: "#0f4c35" },
  subtitle: { fontSize: "14px", color: "#6b7280", marginTop: "4px" },
  title: { fontSize: "22px", fontWeight: "700", color: "#111827", marginBottom: "8px" },
  desc: { fontSize: "14px", color: "#6b7280", marginBottom: "24px" },
  label: { display: "block", fontSize: "13px", fontWeight: "600", color: "#374151", marginBottom: "6px" },
  input: { width: "100%", padding: "10px 14px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "15px", outline: "none", boxSizing: "border-box", marginBottom: "12px" },
  error: { color: "#dc2626", fontSize: "13px", marginBottom: "12px", marginTop: "-4px" },
  btn: { width: "100%", padding: "12px", background: "#0f4c35", color: "#fff", border: "none", borderRadius: "10px", fontSize: "16px", fontWeight: "700", cursor: "pointer", marginTop: "4px" },
  divider: { borderTop: "1px solid #e5e7eb", margin: "24px 0" },
  newAccount: { textAlign: "center", fontSize: "14px", color: "#6b7280" },
  link: { background: "none", border: "none", color: "#0f4c35", fontWeight: "600", cursor: "pointer", fontSize: "14px", textDecoration: "underline" },
};
