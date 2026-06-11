import { useState, useEffect } from "react";

const CARDS = [
  {
    id: "iron",
    quote: (ironPct) => `<em>Iron</em> carries oxygen to your muscles. At ${ironPct}%, your legs will feel heavy in minute 70.`,
    detail: "Iron enables red blood cells to deliver oxygen during sustained running. When iron is low, your sprint recovery slows — you feel it as heavy legs in the second half, not the first.",
    fixes: [
      { food: "Lentil soup at lunch",           gain: "+4.2mg iron" },
      { food: "Lean beef at dinner",             gain: "+3.5mg iron" },
      { food: "Spinach + OJ (vitamin C helps)",  gain: "+2.1mg iron" },
    ],
    source: "Everett MD 2025 · Stony Brook University",
  },
  {
    id: "carbs",
    quote: () => `<em>Carb loading</em> starts 24 hours before kickoff — not the morning of the game.`,
    detail: "Muscle glycogen — your sprint fuel — takes 24 to 48 hours to fully replenish. Friday dinner fills Saturday's tank. Saturday breakfast just tops it off. Most athletes don't know this.",
    fixes: [
      { food: "Tonight: Power Pasta Bowl",   gain: "High carb load" },
      { food: "Tomorrow: OJ + toast at 7am", gain: "Top-off fuel" },
      { food: "9:15am snack: Banana + PB",   gain: "Fast glucose" },
    ],
    source: "Everett MD 2025 · Stony Brook University",
  },
  {
    id: "calcium",
    quote: () => `Ages 9–17 is the <em>only window</em> to build peak bone mass. After this, the opportunity closes.`,
    detail: "Peak bone mineral density is established almost entirely during adolescence. Every day of adequate calcium at 13–17 is a deposit into a bone bank that cannot be reopened after age 25.",
    fixes: [
      { food: "2 glasses of milk today",       gain: "+600mg calcium" },
      { food: "Greek yogurt bedtime snack",     gain: "+280mg calcium" },
      { food: "Fortified OJ with breakfast",    gain: "+350mg calcium" },
    ],
    source: "American Academy of Pediatrics (AAP)",
  },
];

export default function ScienceEdge({ trafficLight, onToast }) {
  const ironPct = trafficLight?.iron_mg?.pct_met ?? 100;

  // Iron < 50 → always show card 0 first
  const startIdx = ironPct < 50 ? 0 : new Date().getDay() % 3;
  const [active, setActive] = useState(startIdx);

  useEffect(() => {
    const interval = setInterval(() => setActive(i => (i + 1) % 3), 8000);
    return () => clearInterval(interval);
  }, []);

  const card = CARDS[active];
  const quoteHtml = card.quote(ironPct);

  function handleFixTap(food) {
    onToast?.(`${food} added to meal plan →`);
  }

  return (
    <div style={s.card}>
      <div style={s.header}>
        <div style={s.iconBox}>🔬</div>
        <span style={s.eyebrow}>Today's Performance Edge</span>
        <div style={s.dots}>
          {CARDS.map((_, i) => (
            <div
              key={i}
              onClick={() => setActive(i)}
              style={{ ...s.dot, ...(i === active ? s.dotActive : s.dotInactive) }}
            />
          ))}
        </div>
      </div>
      <div style={s.body}>
        <div
          style={s.quote}
          dangerouslySetInnerHTML={{ __html: quoteHtml }}
        />
        <div style={s.detail}>{card.detail}</div>
        {card.fixes.map(fix => (
          <div key={fix.food} style={s.fix} onClick={() => handleFixTap(fix.food)}>
            <span style={s.fixName}>{fix.food}</span>
            <span style={s.fixGain}>{fix.gain}</span>
          </div>
        ))}
        <div style={s.source}>📖 {card.source}</div>
      </div>
    </div>
  );
}

const s = {
  card:       { background: "#fff", borderRadius: "14px", border: "1px solid #dce8e0", overflow: "hidden", marginTop: "10px" },
  header:     { padding: "10px 14px 8px", borderBottom: "1px solid #dce8e0", display: "flex", alignItems: "center", gap: "8px" },
  iconBox:    { width: "26px", height: "26px", borderRadius: "6px", background: "rgba(45,106,79,.10)", border: "1px solid rgba(45,106,79,.20)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "13px" },
  eyebrow:    { fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: ".1em", color: "#2d6a4f", flex: 1 },
  dots:       { display: "flex", gap: "4px", alignItems: "center" },
  dot:        { width: "5px", height: "5px", borderRadius: "50%", cursor: "pointer" },
  dotActive:  { background: "#2d6a4f" },
  dotInactive:{ background: "#f4f8f5", border: "1px solid #dce8e0" },
  body:       { padding: "14px" },
  quote:      { fontFamily: "'Nunito', sans-serif", fontSize: "15px", fontWeight: "700", letterSpacing: "-.01em", color: "#1b3a2a", lineHeight: "1.4", marginBottom: "8px" },
  detail:     { fontSize: "12px", color: "#8aa898", fontWeight: "300", lineHeight: "1.6", marginBottom: "10px" },
  fix:        { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", background: "#f4f8f5", border: "1px solid #dce8e0", borderRadius: "7px", marginBottom: "6px", cursor: "pointer" },
  fixName:    { fontSize: "12px", color: "#1b3a2a" },
  fixGain:    { fontSize: "11px", fontWeight: "700", color: "#2d6a4f" },
  source:     { marginTop: "10px", paddingTop: "10px", borderTop: "1px solid #dce8e0", fontSize: "10px", color: "#8aa898", fontWeight: "300" },
};
