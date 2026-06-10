import { useState, useEffect, useCallback } from "react";
import Greeting from "../components/today/Greeting";
import CountdownHero from "../components/today/CountdownHero";
import NextMealsStrip from "../components/today/NextMealsStrip";
import FuelScoreCard from "../components/today/FuelScoreCard";
import StreakCard from "../components/today/StreakCard";
import WeekBarChart from "../components/today/WeekBarChart";
import TomorrowAlert from "../components/today/TomorrowAlert";
import NutrientsReportCard from "../components/today/NutrientsReportCard";
import HydrationTracker from "../components/today/HydrationTracker";

const API = import.meta.env.VITE_API_URL ?? "";

function SectionLabel({ children }) {
  return <div style={sl.label}>{children}</div>;
}
const sl = {
  label: { fontSize: "14px", fontFamily: "'DM Sans', sans-serif", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "#4a6358", marginBottom: "8px", marginTop: "20px" },
};

export default function Today({ athlete, onNavigate }) {
  const [summary, setSummary]   = useState(null);
  const [weekly, setWeekly]     = useState(null);
  const [protocol, setProtocol] = useState(null);
  const [waterCups, setWaterCups] = useState(0);
  const [loading, setLoading]   = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, weekRes, planRes] = await Promise.all([
        fetch(`${API}/api/athletes/${athlete.id}/daily-summary`),
        fetch(`${API}/api/athletes/${athlete.id}/weekly-summary`),
        fetch(`${API}/api/nutrition/timing/${athlete.id}`),
      ]);
      if (sumRes.ok) {
        const d = await sumRes.json();
        setSummary(d);
        setWaterCups(d.water_cups ?? 0);
      }
      if (weekRes.ok) setWeekly(await weekRes.json());
      if (planRes.ok) {
        const p = await planRes.json();
        setProtocol(p.protocol || []);
      }
    } catch (_) {}
    finally { setLoading(false); }
  }, [athlete.id]);

  useEffect(() => { load(); }, [load]);

  // Refresh on tab focus
  useEffect(() => {
    const onVisible = () => { if (!document.hidden) load(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load]);

  async function handleWaterUpdate(cups) {
    setWaterCups(cups); // optimistic
    try {
      await fetch(`${API}/api/water-log/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: athlete.id, cups }),
      });
    } catch (_) {}
  }

  async function handleMealLogged() {
    const res = await fetch(`${API}/api/athletes/${athlete.id}/daily-summary`);
    if (res.ok) {
      const d = await res.json();
      setSummary(d);
      setWaterCups(d.water_cups ?? waterCups);
    }
  }

  if (loading) return (
    <div style={s.loadWrap}>
      <div style={s.spinner} />
      <div style={s.loadText}>Loading today's briefing…</div>
    </div>
  );

  const events      = summary?.events ?? [];
  const eventType   = summary?.event_type ?? "rest";
  const targets     = summary?.targets ?? {};
  const tl          = summary?.traffic_light ?? {};
  const fuelScore   = tl.daily_fuel_score ?? null;
  const targetCups  = Math.round((targets.hydration_oz_min ?? 64) / 8);

  return (
    <div style={s.page}>

      <Greeting
        firstName={summary?.athlete?.first_name ?? athlete.first_name}
        events={events}
        eventType={eventType}
      />

      {/* ── Zone 1: Countdown ── */}
      <SectionLabel>Today</SectionLabel>
      <CountdownHero
        events={events}
        fuelScore={fuelScore}
        urgentAction={summary?.urgent_action}
        eventType={eventType}
      />
      <NextMealsStrip
        protocol={protocol}
        mealLogs={summary?.meal_logs ?? []}
      />

      {/* ── Zone 2: Momentum ── */}
      <SectionLabel>Momentum</SectionLabel>
      <div style={s.twoCol}>
        <FuelScoreCard score={fuelScore} />
        <StreakCard streak={summary?.streak} />
      </div>
      <WeekBarChart week={weekly?.week ?? []} avgScore={weekly?.avg_score} />

      {/* ── Zone 3: Report Card ── */}
      <SectionLabel>Report Card</SectionLabel>
      <TomorrowAlert
        tomorrowEvent={summary?.tomorrow_event}
        onNavigate={onNavigate}
      />
      <NutrientsReportCard
        letterGrade={summary?.letter_grade}
        positiveRows={summary?.positive_rows ?? []}
        gapRows={summary?.gap_rows ?? []}
      />
      <HydrationTracker
        cups={waterCups}
        targetCups={targetCups}
        athleteId={athlete.id}
        onUpdate={handleWaterUpdate}
      />

      {/* Log a meal */}
      <div style={s.logWrap}>
        <button style={s.logBtn} onClick={() => onNavigate("nutrition")}>
          📸 Log a meal
        </button>
      </div>

      <p style={s.disclaimer}>
        FuelUp provides educational food guidance — not medical nutrition therapy.
      </p>
    </div>
  );
}

const s = {
  page:        { fontFamily: "'Nunito', 'DM Sans', sans-serif", paddingBottom: "8px" },
  loadWrap:    { display: "flex", flexDirection: "column", alignItems: "center", gap: "14px", padding: "60px 0" },
  spinner:     { width: "30px", height: "30px", border: "3px solid #dce8e0", borderTopColor: "#2d6a4f", borderRadius: "50%", animation: "spin 0.7s linear infinite" },
  loadText:    { fontSize: "16px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif" },
  twoCol:      { display: "flex", gap: "8px" },
  logWrap:     { padding: "10px 0 0" },
  logBtn:      { width: "100%", padding: "13px", background: "rgba(45,106,79,0.07)", border: "1.5px dashed rgba(45,106,79,0.3)", borderRadius: "10px", color: "#2d6a4f", fontSize: "15px", fontWeight: "700", fontFamily: "'Nunito', sans-serif", letterSpacing: "-0.01em", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" },
  disclaimer:  { textAlign: "center", fontSize: "13px", color: "#8aa898", lineHeight: 1.6, marginTop: "16px" },
};
