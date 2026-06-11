import { useState, useEffect, useCallback } from "react";
import BroadcastCard       from "../components/today/BroadcastCard";
import PerformanceForecast from "../components/today/PerformanceForecast";
import DailyMission        from "../components/today/DailyMission";
import ScienceEdge         from "../components/today/ScienceEdge";
import QuickRow            from "../components/today/QuickRow";
import Toast, { useToast } from "../components/today/Toast";

const API = import.meta.env.VITE_API_URL ?? "";

export default function Today({ athlete, onNavigate }) {
  const [summary, setSummary]     = useState(null);
  const [loading, setLoading]     = useState(true);
  const [waterCups, setWaterCups] = useState(0);
  const { message: toastMsg, showToast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/athletes/${athlete.id}/daily-summary`);
      if (res.ok) {
        const d = await res.json();
        setSummary(d);
        setWaterCups(d.water_cups ?? 0);
      }
    } catch (e) { void e; }
    finally { setLoading(false); }
  }, [athlete.id]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const onVisible = () => { if (!document.hidden) load(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load]);

  async function handleWaterUpdate(cups) {
    setWaterCups(cups);
    try {
      await fetch(`${API}/api/water-log/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: athlete.id, cups }),
      });
    } catch (e) { void e; }
  }

  if (loading) return (
    <div style={s.loadWrap}>
      <div style={s.spinner} />
      <div style={s.loadText}>Loading today's briefing…</div>
    </div>
  );

  const events       = summary?.events ?? [];
  const eventType    = summary?.event_type ?? "rest";
  const tl           = summary?.traffic_light ?? {};
  const fuelScore    = tl.daily_fuel_score ?? 0;
  const targets      = summary?.targets ?? {};
  const targetCups   = Math.round((targets.hydration_oz_min ?? 64) / 8);
  const missionItems = summary?.mission_items ?? [];
  const forecast     = summary?.performance_forecast ?? null;

  return (
    <div style={s.page}>
      <BroadcastCard
        athlete={summary?.athlete ?? { first_name: athlete.first_name }}
        events={events}
        trafficLight={tl}
        fuelScore={fuelScore}
        onNavigateMealPlan={() => onNavigate("meal-plan")}
      />

      <div style={s.body}>
        <PerformanceForecast forecast={forecast} />

        <DailyMission
          missionItems={missionItems}
          eventType={eventType}
          date={summary?.date}
          athleteId={athlete.id}
          onToast={showToast}
        />

        <ScienceEdge
          trafficLight={tl}
          onToast={showToast}
        />

        <QuickRow
          waterCups={waterCups}
          targetCups={targetCups}
          caloriesLogged={tl.calories?.logged ?? 0}
          caloriesTarget={tl.calories?.target ?? 0}
          athleteId={athlete.id}
          onWaterUpdate={handleWaterUpdate}
        />

        <div style={s.logWrap}>
          <button style={s.logBtn} onClick={() => { showToast("Opening meal logger →"); onNavigate("nutrition"); }}>
            📸 Log a meal — 2 seconds
          </button>
        </div>

        <p style={s.disclaimer}>
          FuelUp provides food education guidance — not medical nutrition therapy.
          Consult your physician or a licensed RDN for medical nutrition concerns.
        </p>
      </div>

      <Toast message={toastMsg} />
    </div>
  );
}

const s = {
  page:       { fontFamily: "'Nunito', 'DM Sans', sans-serif", paddingBottom: "8px", background: "#f8faf9", minHeight: "100vh" },
  body:       { padding: "0 12px" },
  loadWrap:   { display: "flex", flexDirection: "column", alignItems: "center", gap: "14px", padding: "60px 0" },
  spinner:    { width: "30px", height: "30px", border: "3px solid #dce8e0", borderTopColor: "#2d6a4f", borderRadius: "50%", animation: "spin 0.7s linear infinite" },
  loadText:   { fontSize: "16px", color: "#4a6358", fontFamily: "'DM Sans', sans-serif" },
  logWrap:    { paddingTop: "10px" },
  logBtn:     { width: "100%", padding: "13px", background: "rgba(45,106,79,.07)", border: "1px dashed rgba(45,106,79,.25)", borderRadius: "14px", color: "#2d6a4f", fontFamily: "'Nunito', sans-serif", fontSize: "13px", fontWeight: "700", letterSpacing: "-.01em", cursor: "pointer", textAlign: "center" },
  disclaimer: { textAlign: "center", fontSize: "10px", color: "#8aa898", lineHeight: "1.5", fontWeight: "300", padding: "10px 0 0" },
};
