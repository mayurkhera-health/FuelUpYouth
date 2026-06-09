import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000";
const TODAY = new Date().toISOString().split("T")[0];

const DAY_TYPE = {
  game:       { label: "Game Day",       emoji: "⚽", color: "#dc2626", bg: "#fef2f2", border: "#fecaca" },
  tournament: { label: "Tournament Day", emoji: "🏆", color: "#9333ea", bg: "#faf5ff", border: "#d8b4fe" },
  practice:   { label: "Practice Day",   emoji: "🏃", color: "#d97706", bg: "#fffbeb", border: "#fde68a" },
  rest:       { label: "Rest Day",       emoji: "😴", color: "#0f4c35", bg: "#f0fdf4", border: "#bbf7d0" },
};

const SCORE_COLOR = (score) => {
  if (score >= 90) return "#0f4c35";
  if (score >= 75) return "#d97706";
  if (score >= 50) return "#ea580c";
  return "#dc2626";
};

const SCORE_BADGE = (score) => {
  if (score >= 90) return "Elite Fueler";
  if (score >= 75) return "Game Ready";
  if (score >= 50) return "Getting There";
  return "Needs Fuel";
};

function ScoreRing({ score }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const fill = circ - (score / 100) * circ;
  const color = SCORE_COLOR(score);
  return (
    <div style={ring.wrap}>
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <circle
          cx="64" cy="64" r={r} fill="none"
          stroke={color} strokeWidth="10"
          strokeDasharray={circ} strokeDashoffset={fill}
          strokeLinecap="round"
          transform="rotate(-90 64 64)"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div style={ring.inner}>
        <div style={{ ...ring.score, color }}>{score}</div>
        <div style={ring.label}>/ 100</div>
      </div>
    </div>
  );
}
const ring = {
  wrap: { position: "relative", width: 128, height: 128, flexShrink: 0 },
  inner: { position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" },
  score: { fontSize: "30px", fontWeight: "800", lineHeight: 1 },
  label: { fontSize: "11px", color: "#9ca3af", marginTop: "2px" },
};

export default function HomeScreen({ athlete, onNavigate }) {
  const [targets, setTargets]     = useState(null);
  const [meals, setMeals]         = useState([]);
  const [nextMeal, setNextMeal]   = useState(null);
  const [todayEvent, setTodayEvent] = useState(null);
  const [fuelScore, setFuelScore] = useState(null);
  const [loading, setLoading]     = useState(true);

  const dateLabel = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });

  const fetchHome = useCallback(async () => {
    setLoading(true);
    try {
      const [tRes, mRes, evRes, timRes] = await Promise.all([
        fetch(`${API}/api/nutrition/targets/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/meals/athlete/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/events/athlete/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/nutrition/timing/${athlete.id}?date=${TODAY}`),
      ]);

      const t = tRes.ok ? await tRes.json() : null;
      const m = mRes.ok ? await mRes.json() : [];
      const ev = evRes.ok ? await evRes.json() : [];
      const tim = timRes.ok ? await timRes.json() : null;

      setTargets(t);
      setMeals(m);
      setTodayEvent(ev[0] || null);

      // Pick next upcoming meal from timing
      if (tim?.meals?.length) {
        const now = new Date();
        const upcoming = tim.meals.find(meal => {
          if (!meal.timing) return false;
          const timeStr = meal.timing.match(/\d{1,2}:\d{2}/);
          if (!timeStr) return true;
          const [h, min] = timeStr[0].split(":").map(Number);
          const mealTime = new Date();
          mealTime.setHours(h, min, 0, 0);
          return mealTime > now;
        });
        setNextMeal(upcoming || tim.meals[0]);
      }

      // Fetch fuel score only if targets exist (avoids Claude call on empty days)
      if (t) {
        const scoreRes = await fetch(`${API}/api/reports/${athlete.id}/daily?date=${TODAY}`);
        if (scoreRes.ok) {
          const scoreData = await scoreRes.json();
          if (scoreData.fuel_score !== undefined) setFuelScore(scoreData);
        }
      }
    } catch (_) {}
    finally { setLoading(false); }
  }, [athlete.id]);

  useEffect(() => { fetchHome(); }, [fetchHome]);

  const consumed = meals.reduce(
    (acc, m) => ({
      calories:  acc.calories  + (m.calories  || 0),
      protein_g: acc.protein_g + (m.protein_g || 0),
      water_oz:  acc.water_oz  + (m.water_oz  || 0),
    }),
    { calories: 0, protein_g: 0, water_oz: 0 }
  );

  const dayType = todayEvent?.event_type || targets?.event_type || "rest";
  const day = DAY_TYPE[dayType] || DAY_TYPE.rest;

  if (loading) {
    return (
      <div style={s.loadingWrap}>
        <div style={s.loadingDot} /><div style={{ ...s.loadingDot, animationDelay: "0.15s" }} /><div style={{ ...s.loadingDot, animationDelay: "0.3s" }} />
      </div>
    );
  }

  return (
    <div>
      {/* Greeting */}
      <div style={s.greeting}>
        <div style={s.greetName}>Good {getTimeOfDay()}, {athlete.first_name} 👋</div>
        <div style={s.greetDate}>{dateLabel}</div>
      </div>

      {/* Day type banner */}
      <div style={{ ...s.dayBanner, background: day.bg, border: `1.5px solid ${day.border}` }}>
        <span style={s.dayEmoji}>{day.emoji}</span>
        <span style={{ ...s.dayLabel, color: day.color }}>{day.label}</span>
        {todayEvent && <span style={s.dayEvent}> · {todayEvent.event_name}{todayEvent.start_time ? ` at ${todayEvent.start_time}` : ""}</span>}
      </div>

      {/* Fuel score + macros row */}
      {targets ? (
        <div style={s.scoreRow}>
          {fuelScore ? (
            <div style={s.scoreCard}>
              <ScoreRing score={fuelScore.fuel_score} />
              <div style={s.scoreMeta}>
                <div style={{ ...s.scoreBadge, color: SCORE_COLOR(fuelScore.fuel_score) }}>{SCORE_BADGE(fuelScore.fuel_score)}</div>
                <div style={s.scoreDesc}>Today's Fuel Score</div>
                {fuelScore.teen_message && <div style={s.scoreMsg}>{fuelScore.teen_message}</div>}
              </div>
            </div>
          ) : (
            <div style={s.scoreCard}>
              <div style={s.noScoreRing}>
                <div style={s.noScoreNum}>—</div>
                <div style={s.noScoreLabel}>Log meals to<br/>get your score</div>
              </div>
            </div>
          )}

          <div style={s.macroCards}>
            <MacroMini label="Calories" consumed={Math.round(consumed.calories)} target={targets.total_calories} unit="kcal" color="#0f4c35" />
            <MacroMini label="Protein"  consumed={Math.round(consumed.protein_g)} target={Math.round((targets.protein_g_min + targets.protein_g_max) / 2)} unit="g" color="#d97706" />
            <MacroMini label="Hydration" consumed={Math.round(consumed.water_oz)} target={targets.hydration_oz_max} unit="oz" color="#0ea5e9" />
          </div>
        </div>
      ) : (
        <div style={s.noTargets}>
          <div style={s.noTargetsIcon}>📅</div>
          <div style={s.noTargetsText}>No schedule added yet — nutrition targets are calculated based on your training day.</div>
          <button style={s.noTargetsBtn} onClick={() => onNavigate("schedule")}>Add Your Schedule →</button>
        </div>
      )}

      {/* Next meal */}
      {nextMeal && (
        <div style={s.nextMealCard}>
          <div style={s.nextMealLabel}>Next Meal</div>
          <div style={s.nextMealName}>{nextMeal.meal_name}</div>
          <div style={s.nextMealTime}>{nextMeal.timing} · {nextMeal.focus}</div>
        </div>
      )}

      {/* AI suggestions */}
      {fuelScore?.gap_fix_suggestions?.length > 0 && (
        <div style={s.suggestionsCard}>
          <div style={s.suggestionsTitle}>💡 Quick Fixes</div>
          {fuelScore.gap_fix_suggestions.slice(0, 3).map((sg, i) => (
            <div key={i} style={s.suggestion}>• {sg}</div>
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div style={s.actionsTitle}>Quick Actions</div>
      <div style={s.actions}>
        <ActionBtn icon="🍽️" label="Log a Meal"       onClick={() => onNavigate("nutrition")} />
        <ActionBtn icon="📅" label="View Schedule"     onClick={() => onNavigate("schedule")}  />
        <ActionBtn icon="🍳" label="Meal Planner"       onClick={() => onNavigate("meal-plan")} />
        <ActionBtn icon="💧" label="Hydration Plan"    onClick={() => onNavigate("hydration")} />
      </div>

      <p style={s.disclaimer}>FuelUp provides educational food guidance — not medical nutrition therapy.</p>
    </div>
  );
}

function MacroMini({ label, consumed, target, unit, color }) {
  const pct = Math.min(100, Math.round((consumed / (target || 1)) * 100));
  const over = consumed > target;
  return (
    <div style={mm.card}>
      <div style={mm.top}>
        <span style={mm.label}>{label}</span>
        <span style={{ ...mm.val, color: over ? "#dc2626" : "#111827" }}>{consumed}<span style={mm.unit}>{unit}</span></span>
      </div>
      <div style={mm.track}><div style={{ ...mm.fill, width: `${pct}%`, background: over ? "#dc2626" : color }} /></div>
      <div style={mm.target}>Target: {target}{unit}</div>
    </div>
  );
}
const mm = {
  card: { background: "#f9fafb", borderRadius: "10px", padding: "10px 12px", marginBottom: "8px" },
  top: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "6px" },
  label: { fontSize: "12px", fontWeight: "600", color: "#6b7280" },
  val: { fontSize: "16px", fontWeight: "800" },
  unit: { fontSize: "11px", fontWeight: "400", color: "#9ca3af", marginLeft: "2px" },
  track: { height: "5px", background: "#e5e7eb", borderRadius: "99px", overflow: "hidden", marginBottom: "4px" },
  fill: { height: "100%", borderRadius: "99px", transition: "width 0.5s ease" },
  target: { fontSize: "11px", color: "#9ca3af" },
};

function ActionBtn({ icon, label, onClick }) {
  return (
    <button style={ab.btn} onClick={onClick}>
      <span style={ab.icon}>{icon}</span>
      <span style={ab.label}>{label}</span>
    </button>
  );
}
const ab = {
  btn: { flex: "1 1 calc(50% - 6px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "6px", background: "#f9fafb", border: "1.5px solid #e5e7eb", borderRadius: "12px", padding: "16px 8px", cursor: "pointer" },
  icon: { fontSize: "22px" },
  label: { fontSize: "13px", fontWeight: "600", color: "#374151" },
};

function getTimeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}

const s = {
  loadingWrap: { display: "flex", gap: "8px", justifyContent: "center", padding: "60px 0" },
  loadingDot: { width: "8px", height: "8px", background: "#0f4c35", borderRadius: "50%", animation: "pulse 1s infinite" },
  greeting: { marginBottom: "16px" },
  greetName: { fontSize: "22px", fontWeight: "800", color: "#111827" },
  greetDate: { fontSize: "13px", color: "#6b7280", marginTop: "2px" },
  dayBanner: { display: "flex", alignItems: "center", gap: "8px", padding: "10px 16px", borderRadius: "10px", marginBottom: "20px" },
  dayEmoji: { fontSize: "18px" },
  dayLabel: { fontSize: "14px", fontWeight: "700" },
  dayEvent: { fontSize: "13px", color: "#6b7280" },
  scoreRow: { display: "flex", gap: "16px", marginBottom: "16px", alignItems: "flex-start" },
  scoreCard: { display: "flex", gap: "16px", alignItems: "center", flex: 1, background: "#f9fafb", border: "1.5px solid #e5e7eb", borderRadius: "14px", padding: "16px" },
  scoreMeta: { flex: 1 },
  scoreBadge: { fontSize: "16px", fontWeight: "800", marginBottom: "2px" },
  scoreDesc: { fontSize: "12px", color: "#6b7280", marginBottom: "6px" },
  scoreMsg: { fontSize: "12px", color: "#374151", lineHeight: "1.5" },
  noScoreRing: { width: 128, height: 128, background: "#e5e7eb", borderRadius: "50%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  noScoreNum: { fontSize: "28px", fontWeight: "800", color: "#9ca3af" },
  noScoreLabel: { fontSize: "10px", color: "#9ca3af", textAlign: "center", marginTop: "4px", lineHeight: 1.4 },
  macroCards: { flex: 1 },
  noTargets: { background: "#fffbeb", border: "1.5px solid #fde68a", borderRadius: "14px", padding: "24px", textAlign: "center", marginBottom: "16px" },
  noTargetsIcon: { fontSize: "32px", marginBottom: "10px" },
  noTargetsText: { fontSize: "13px", color: "#92400e", marginBottom: "14px", lineHeight: 1.5 },
  noTargetsBtn: { background: "#0f4c35", color: "#fff", border: "none", borderRadius: "8px", padding: "10px 20px", fontSize: "14px", fontWeight: "700", cursor: "pointer" },
  nextMealCard: { background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "12px", padding: "14px 16px", marginBottom: "16px" },
  nextMealLabel: { fontSize: "11px", fontWeight: "700", color: "#0f4c35", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" },
  nextMealName: { fontSize: "16px", fontWeight: "700", color: "#111827", marginBottom: "2px" },
  nextMealTime: { fontSize: "12px", color: "#6b7280" },
  suggestionsCard: { background: "#fff7ed", border: "1.5px solid #fed7aa", borderRadius: "12px", padding: "14px 16px", marginBottom: "16px" },
  suggestionsTitle: { fontSize: "13px", fontWeight: "700", color: "#92400e", marginBottom: "8px" },
  suggestion: { fontSize: "13px", color: "#374151", marginBottom: "4px" },
  actionsTitle: { fontSize: "13px", fontWeight: "700", color: "#6b7280", marginBottom: "10px", textTransform: "uppercase", letterSpacing: "0.05em" },
  actions: { display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "24px" },
  disclaimer: { textAlign: "center", fontSize: "11px", color: "#9ca3af" },
};
