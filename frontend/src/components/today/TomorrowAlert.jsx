const CONTENT = {
  game: {
    title: "Friday dinner is the most important meal of the week.",
    body: "Muscle glycogen takes 24–48hrs to load. Saturday's performance runs on tonight's pasta, not tomorrow's breakfast. FuelUp will remind you at 6:30 PM.",
    action: "See tomorrow's plan →",
  },
  tournament: {
    title: "Tournament starts tomorrow. Carb loading starts tonight.",
    body: "Multi-game tournaments require maximum glycogen stores. Begin eating high-carb now — tonight's dinner matters more than tournament morning breakfast.",
    action: "See tournament plan →",
  },
  practice: {
    title: "Practice tomorrow. Pre-fuel reminder set.",
    body: "FuelUp will remind you to eat your pre-practice lunch by noon. Carbs + protein 2hrs before = better training output.",
    action: "See tomorrow's meals →",
  },
  training: {
    title: "Training tomorrow. Pre-fuel reminder set.",
    body: "FuelUp will remind you to eat your pre-training lunch by noon. Carbs + protein 2hrs before = better training output.",
    action: "See tomorrow's meals →",
  },
  strength: {
    title: "Strength day tomorrow. Highest protein day of the week.",
    body: "Bedtime casein snack tonight + high protein tomorrow. Cottage cheese or Greek yogurt before bed supports overnight muscle repair. — Everett MD 2025",
    action: "See strength plan →",
  },
  rest: {
    title: "Recovery continues tomorrow.",
    body: "Light fueling tomorrow supports muscle repair and glycogen restoration. Iron-rich foods are the priority — lentils, beef, or fortified cereal.",
    action: "See recovery plan →",
  },
};

function getDayName(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "long" });
}

export default function TomorrowAlert({ tomorrowEvent, onNavigate }) {
  if (!tomorrowEvent) return null;
  const et = tomorrowEvent.event_type || "rest";
  const content = CONTENT[et] || CONTENT.rest;
  const dayName = getDayName(tomorrowEvent.event_date);

  return (
    <div style={s.card}>
      <div style={s.icon}>⚡</div>
      <div style={s.body}>
        <div style={s.eyebrow}>{dayName} · {et.charAt(0).toUpperCase() + et.slice(1)}</div>
        <div style={s.title}>{content.title}</div>
        <div style={s.text}>{content.body}</div>
        <button style={s.chip} onClick={() => onNavigate("meal-plan")}>
          {content.action}
        </button>
      </div>
    </div>
  );
}

const s = {
  card:    { background: "rgba(126,106,181,0.07)", border: "1px solid rgba(126,106,181,0.2)", borderRadius: "12px", padding: "13px 14px", display: "flex", gap: "12px", marginTop: "8px" },
  icon:    { fontSize: "22px", flexShrink: 0, marginTop: "1px" },
  body:    { flex: 1, minWidth: 0 },
  eyebrow: { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.1em", color: "#7e6ab5", marginBottom: "3px" },
  title:   { fontSize: "16px", fontWeight: "700", fontFamily: "'Nunito', sans-serif", color: "#1b3a2a", letterSpacing: "-0.01em", marginBottom: "4px", lineHeight: 1.6 },
  text:    { fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "400", color: "#3d5448", lineHeight: 1.5, marginBottom: "8px" },
  chip:    { display: "inline-block", padding: "6px 12px", borderRadius: "5px", background: "rgba(126,106,181,0.12)", border: "1px solid rgba(126,106,181,0.25)", color: "#7e6ab5", fontSize: "13px", fontFamily: "'DM Sans', sans-serif", fontWeight: "500", cursor: "pointer" },
};
