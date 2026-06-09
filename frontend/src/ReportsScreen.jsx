import { useState } from "react";

const API = "http://localhost:8000";
const TODAY = new Date().toISOString().split("T")[0];

const SCORE_COLORS = {
  "Elite Fueler": { bg: "#f0fdf4", border: "#bbf7d0", text: "#0f4c35", bar: "#0f4c35" },
  "Game Ready":   { bg: "#fffbeb", border: "#fde68a", text: "#d97706", bar: "#d97706" },
  "Getting There":{ bg: "#fff7ed", border: "#fed7aa", text: "#ea580c", bar: "#ea580c" },
  "Needs Fuel":   { bg: "#fef2f2", border: "#fecaca", text: "#dc2626", bar: "#dc2626" },
};

function ScoreGauge({ score, badge }) {
  const c = SCORE_COLORS[badge] || SCORE_COLORS["Needs Fuel"];
  return (
    <div style={{ ...g.wrap, background: c.bg, border: `1.5px solid ${c.border}` }}>
      <div style={{ ...g.score, color: c.text }}>{score}</div>
      <div style={g.track}><div style={{ ...g.fill, width: `${score}%`, background: c.bar }} /></div>
      <div style={{ ...g.badge, color: c.text }}>{badge}</div>
    </div>
  );
}
const g = {
  wrap: { textAlign: "center", padding: "20px", borderRadius: "12px", marginBottom: "16px" },
  score: { fontSize: "52px", fontWeight: "800", lineHeight: 1 },
  track: { height: "8px", background: "#e5e7eb", borderRadius: "99px", margin: "12px 0 8px" },
  fill: { height: "100%", borderRadius: "99px", transition: "width 0.6s ease" },
  badge: { fontSize: "16px", fontWeight: "700" },
};

export default function ReportsScreen({ athlete }) {
  const [daily, setDaily]       = useState(null);
  const [weekly, setWeekly]     = useState(null);
  const [tourney, setTourney]   = useState(null);
  const [loading, setLoading]   = useState({});
  const [error, setError]       = useState({});
  const [tourneyDate, setTourneyDate] = useState("");

  async function load(key, url, setter) {
    setLoading(l => ({ ...l, [key]: true }));
    setError(e => ({ ...e, [key]: "" }));
    try {
      const res = await fetch(url);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Failed to load.");
      }
      setter(await res.json());
    } catch (e) {
      setError(err => ({ ...err, [key]: e.message }));
    } finally {
      setLoading(l => ({ ...l, [key]: false }));
    }
  }

  return (
    <div>
      <h2 style={s.title}>Reports</h2>

      {/* Daily Fuel Score */}
      <div style={s.section}>
        <div style={s.sectionHeader}>
          <div>
            <div style={s.sectionTitle}>Daily Fuel Score</div>
            <div style={s.sectionDesc}>AI-powered score of today's nutrition vs. targets.</div>
          </div>
          <button style={s.runBtn} onClick={() => load("daily", `${API}/api/reports/${athlete.id}/daily?date=${TODAY}`, setDaily)} disabled={loading.daily}>
            {loading.daily ? "Analyzing…" : daily ? "Refresh" : "Run"}
          </button>
        </div>
        {error.daily && <p style={s.error}>{error.daily}</p>}
        {daily && (
          <>
            <ScoreGauge score={daily.fuel_score} badge={daily.badge} />
            <p style={s.message}>{daily.teen_message}</p>
            {daily.gap_fix_suggestions?.length > 0 && (
              <div style={s.list}>
                <div style={s.listTitle}>Suggestions</div>
                {daily.gap_fix_suggestions.map((sg, i) => <div key={i} style={s.listItem}>• {sg}</div>)}
              </div>
            )}
            {daily.traffic_lights?.length > 0 && (
              <div style={s.trafficRow}>
                {daily.traffic_lights.map((t, i) => (
                  <div key={i} style={s.trafficItem}>
                    <span>{t.light === "green" ? "🟢" : t.light === "yellow" ? "🟡" : "🔴"}</span>
                    <span style={s.trafficLabel}>{t.nutrient}</span>
                  </div>
                ))}
              </div>
            )}
            {daily.lea_alert && <div style={s.alert}>⚠️ Low Energy Availability Risk — {daily.lea_alert}</div>}
            {daily.iron_alert && <div style={s.alert}>⚠️ Iron Alert — {daily.iron_alert}</div>}
          </>
        )}
      </div>

      {/* Weekly Report */}
      <div style={s.section}>
        <div style={s.sectionHeader}>
          <div>
            <div style={s.sectionTitle}>Weekly Parent Report</div>
            <div style={s.sectionDesc}>7-day nutrition summary with AI insights.</div>
          </div>
          <button style={s.runBtn} onClick={() => load("weekly", `${API}/api/reports/${athlete.id}/weekly`, setWeekly)} disabled={loading.weekly}>
            {loading.weekly ? "Generating…" : weekly ? "Refresh" : "Run"}
          </button>
        </div>
        {error.weekly && <p style={s.error}>{error.weekly}</p>}
        {weekly && (
          <div style={s.weeklyCard}>
            {weekly.summary && <p style={s.weeklyText}>{weekly.summary}</p>}
            {weekly.strengths?.length > 0 && (
              <div style={s.list}>
                <div style={s.listTitle}>Strengths</div>
                {weekly.strengths.map((x, i) => <div key={i} style={s.listItem}>✅ {x}</div>)}
              </div>
            )}
            {weekly.areas_to_improve?.length > 0 && (
              <div style={s.list}>
                <div style={s.listTitle}>Areas to Improve</div>
                {weekly.areas_to_improve.map((x, i) => <div key={i} style={s.listItem}>📌 {x}</div>)}
              </div>
            )}
            {weekly.week_start && (
              <p style={s.weekLabel}>{weekly.week_start} → {weekly.week_end}</p>
            )}
          </div>
        )}
      </div>

      {/* Tournament Readiness */}
      <div style={s.section}>
        <div style={s.sectionHeader}>
          <div>
            <div style={s.sectionTitle}>Tournament Readiness</div>
            <div style={s.sectionDesc}>Carb-loading protocol + readiness check.</div>
          </div>
          <button
            style={s.runBtn}
            onClick={() => load("tourney", `${API}/api/reports/${athlete.id}/tournament-readiness${tourneyDate ? `?tournament_date=${tourneyDate}` : ""}`, setTourney)}
            disabled={loading.tourney}
          >
            {loading.tourney ? "Loading…" : tourney ? "Refresh" : "Run"}
          </button>
        </div>
        <div style={s.dateRow}>
          <label style={s.dateLabel}>Tournament Date (optional)</label>
          <input style={s.dateInput} type="date" value={tourneyDate} onChange={e => setTourneyDate(e.target.value)} />
        </div>
        {error.tourney && <p style={s.error}>{error.tourney}</p>}
        {tourney && (
          <div style={s.tourneyCard}>
            <div style={s.tourneyRow}>
              <span style={s.tourneyLabel}>Tournament Date</span>
              <span style={s.tourneyVal}>{tourney.tournament_date}</span>
            </div>
            <div style={s.tourneyRow}>
              <span style={s.tourneyLabel}>Avg Daily Calories (14d)</span>
              <span style={s.tourneyVal}>{tourney.avg_daily_calories_last_14_days} kcal</span>
            </div>
            {tourney.carb_loading_protocol && (
              <div style={{ marginTop: "16px" }}>
                <div style={s.listTitle}>Carb-Loading Protocol</div>
                {Object.entries(tourney.carb_loading_protocol).map(([day, plan]) => (
                  <div key={day} style={s.carbRow}>
                    <span style={s.carbDay}>{day.replace(/_/g, " ")}</span>
                    <span style={s.carbPlan}>{plan}</span>
                  </div>
                ))}
              </div>
            )}
            <p style={s.disclaimer}>{tourney.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
}

const s = {
  title: { fontSize: "18px", fontWeight: "700", color: "#111827", margin: "0 0 20px" },
  section: { border: "1.5px solid #e5e7eb", borderRadius: "12px", padding: "18px 20px", marginBottom: "16px" },
  sectionHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "14px" },
  sectionTitle: { fontSize: "15px", fontWeight: "700", color: "#111827" },
  sectionDesc: { fontSize: "12px", color: "#6b7280", marginTop: "2px" },
  runBtn: { background: "#0f4c35", color: "#fff", border: "none", borderRadius: "8px", padding: "7px 16px", fontSize: "13px", fontWeight: "600", cursor: "pointer", whiteSpace: "nowrap" },
  error: { color: "#dc2626", fontSize: "13px", marginBottom: "8px" },
  message: { fontSize: "14px", color: "#374151", marginBottom: "12px" },
  list: { marginBottom: "12px" },
  listTitle: { fontSize: "11px", fontWeight: "700", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" },
  listItem: { fontSize: "13px", color: "#374151", marginBottom: "4px" },
  trafficRow: { display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "12px" },
  trafficItem: { display: "flex", alignItems: "center", gap: "6px" },
  trafficLabel: { fontSize: "13px", color: "#374151", fontWeight: "600" },
  alert: { background: "#fffbeb", border: "1.5px solid #fde68a", borderRadius: "8px", padding: "10px 14px", fontSize: "13px", color: "#92400e", marginBottom: "8px" },
  weeklyCard: { background: "#f9fafb", borderRadius: "8px", padding: "14px" },
  weeklyText: { fontSize: "14px", color: "#374151", marginBottom: "12px" },
  weekLabel: { fontSize: "11px", color: "#9ca3af", marginTop: "8px" },
  dateRow: { marginBottom: "12px" },
  dateLabel: { display: "block", fontSize: "12px", fontWeight: "600", color: "#6b7280", marginBottom: "4px" },
  dateInput: { padding: "7px 10px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "13px", outline: "none" },
  tourneyCard: { background: "#f9fafb", borderRadius: "8px", padding: "14px" },
  tourneyRow: { display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "8px" },
  tourneyLabel: { color: "#6b7280", fontWeight: "600" },
  tourneyVal: { color: "#111827", fontWeight: "700" },
  carbRow: { marginBottom: "8px" },
  carbDay: { display: "block", fontSize: "11px", fontWeight: "700", color: "#0f4c35", textTransform: "uppercase", letterSpacing: "0.04em" },
  carbPlan: { fontSize: "13px", color: "#374151" },
  disclaimer: { fontSize: "11px", color: "#9ca3af", marginTop: "12px" },
};
