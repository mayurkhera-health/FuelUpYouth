const EVENT_BADGE = {
  game:       { bg: "rgba(192,90,74,0.12)", color: "#c05a4a", border: "rgba(192,90,74,0.25)", label: "Game Day ⚽" },
  tournament: { bg: "rgba(126,106,181,0.12)", color: "#7e6ab5", border: "rgba(126,106,181,0.25)", label: "Tournament 🏆" },
  practice:   { bg: "rgba(200,144,58,0.12)", color: "#c8903a", border: "rgba(200,144,58,0.25)", label: "Practice 🏃" },
  training:   { bg: "rgba(200,144,58,0.12)", color: "#c8903a", border: "rgba(200,144,58,0.25)", label: "Training 💪" },
  strength:   { bg: "rgba(74,143,196,0.12)", color: "#4a8fc4", border: "rgba(74,143,196,0.25)", label: "Strength 🏋️" },
  rest:       { bg: "rgba(139,168,152,0.12)", color: "#4a6358", border: "rgba(139,168,152,0.2)", label: "Rest Day 🌿" },
};

function getGreeting(firstName, events) {
  const hour = new Date().getHours();
  const prefix = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const upcoming = events.find(e => {
    if (!e.start_time) return false;
    const [h, m] = e.start_time.split(":").map(Number);
    const t = new Date(); t.setHours(h, m, 0, 0);
    return t > new Date();
  });

  let subLine;
  if (upcoming) {
    const [h, m] = upcoming.start_time.split(":").map(Number);
    const t = new Date(); t.setHours(h, m, 0, 0);
    const minsUntil = Math.round((t - new Date()) / 60000);
    const hrs = Math.floor(minsUntil / 60);
    const mins = minsUntil % 60;
    const label = upcoming.event_type === "game" ? "Kickoff"
      : upcoming.event_type === "tournament" ? "Tournament"
      : upcoming.event_type === "practice" || upcoming.event_type === "training" ? "Practice"
      : upcoming.event_type === "strength" ? "Strength session"
      : "Event";
    subLine = minsUntil < 60
      ? `${label} starts in ${mins} min.`
      : `${label} starts in ${hrs} hr ${mins} min.`;
  } else if (events.length > 0) {
    subLine = "Great effort today. Recovery mode active.";
  } else {
    subLine = "Rest day — recovery nutrition active.";
  }

  return { greeting: `${prefix}, ${firstName}.`, subLine };
}

export default function Greeting({ firstName, events, eventType }) {
  const { greeting, subLine } = getGreeting(firstName, events);
  const badge = EVENT_BADGE[eventType] || EVENT_BADGE.rest;

  return (
    <div style={s.wrap}>
      <div style={s.left}>
        <div style={s.name}>{greeting}</div>
        <div style={s.sub}>{subLine}</div>
      </div>
      {eventType && eventType !== "rest" && (
        <div style={{ ...s.badge, background: badge.bg, color: badge.color, border: `1px solid ${badge.border}` }}>
          {badge.label}
        </div>
      )}
    </div>
  );
}

const s = {
  wrap:  { display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px", marginBottom: "14px" },
  left:  { minWidth: 0 },
  name:  { fontSize: "22px", fontWeight: "800", color: "#1b3a2a", letterSpacing: "-0.03em", fontFamily: "'Nunito', sans-serif", lineHeight: 1.6 },
  sub:   { fontSize: "14px", color: "#4a6358", marginTop: "3px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400" },
  badge: { flexShrink: 0, fontSize: "12px", fontWeight: "700", padding: "5px 10px", borderRadius: "99px", fontFamily: "'Nunito', sans-serif", letterSpacing: "0.02em", marginTop: "2px" },
};
