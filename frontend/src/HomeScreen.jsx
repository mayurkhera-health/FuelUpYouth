import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL ?? "";
const TODAY = new Date().toISOString().split("T")[0];

// ── Sport / day-type photos (Unsplash, free) ─────────────────────────────────
const DAY_PHOTO = {
  game:       "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=900&q=80",
  tournament: "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=900&q=80",
  practice:   "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=900&q=80",
  training:   "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=900&q=80",
  strength:   "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=900&q=80",
  rest:       "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=900&q=80",
};

// ── Food thumbnail photos per meal label ─────────────────────────────────────
const MEAL_PHOTO = {
  "Breakfast":               "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=160&q=80",
  "Tournament Breakfast":    "https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=160&q=80",
  "High-Carb Breakfast":     "https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=160&q=80",
  "Pre-Game Meal":           "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=160&q=80",
  "Pre-Practice Meal":       "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=160&q=80",
  "Pre-Strength Meal":       "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=160&q=80",
  "Pre-Game Snack":          "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=160&q=80",
  "Top-Up Snack":            "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=160&q=80",
  "Pre-Game 2 Top-Up":       "https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?w=160&q=80",
  "Recovery Window":         "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=160&q=80",
  "Recovery Snack":          "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=160&q=80",
  "Post-Workout Window":     "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=160&q=80",
  "Between-Games Recovery":  "https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?w=160&q=80",
  "Lunch":                   "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=160&q=80",
  "Dinner":                  "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=160&q=80",
  "Tournament Dinner":       "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=160&q=80",
  "Snack":                   "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=160&q=80",
  "Bedtime Snack":           "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=160&q=80",
};

// ── Day config ────────────────────────────────────────────────────────────────
const DAY_CFG = {
  game:       { label: "Game Day",        emoji: "⚽", color: "#dc2626", light: "#fef2f2", grad: "linear-gradient(135deg,#991b1b 0%,#dc2626 100%)" },
  tournament: { label: "Tournament Day",  emoji: "🏆", color: "#9333ea", light: "#faf5ff", grad: "linear-gradient(135deg,#4c1d95 0%,#9333ea 100%)" },
  practice:   { label: "Practice Day",    emoji: "🏃", color: "#d97706", light: "#fffbeb", grad: "linear-gradient(135deg,#92400e 0%,#d97706 100%)" },
  training:   { label: "Training Day",    emoji: "💪", color: "#ea580c", light: "#fff7ed", grad: "linear-gradient(135deg,#7c2d12 0%,#ea580c 100%)" },
  strength:   { label: "Strength Day",    emoji: "🏋️", color: "#2563eb", light: "#eff6ff", grad: "linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%)" },
  rest:       { label: "Rest & Recovery", emoji: "🌿", color: "#0f4c35", light: "#f0fdf4", grad: "linear-gradient(135deg,#0a3324 0%,#0f4c35 100%)" },
};

// ── Meal macros ───────────────────────────────────────────────────────────────
const MACROS = {
  "Oatmeal + Eggs + OJ":         { calories: 480, carbs_g: 68, protein_g: 22, fat_g: 14 },
  "Power Pasta Bowl":             { calories: 650, carbs_g: 85, protein_g: 45, fat_g: 12 },
  "Banana + Peanut Butter":       { calories: 280, carbs_g: 36, protein_g:  8, fat_g: 12 },
  "Chocolate Milk + Banana":      { calories: 380, carbs_g: 62, protein_g: 17, fat_g:  5 },
  "Brown Rice Salmon Bowl":       { calories: 580, carbs_g: 72, protein_g: 38, fat_g: 18 },
  "High-Carb Pancakes + Eggs":    { calories: 680, carbs_g: 95, protein_g: 28, fat_g: 14 },
  "Banana + Honey":               { calories: 200, carbs_g: 52, protein_g:  1, fat_g:  0 },
  "Crackers + Peanut Butter":     { calories: 290, carbs_g: 38, protein_g: 10, fat_g: 11 },
  "Tournament Recovery Pasta":    { calories: 720, carbs_g: 82, protein_g: 48, fat_g: 16 },
  "Greek Yogurt + Berries":       { calories: 250, carbs_g: 30, protein_g: 20, fat_g:  4 },
  "Turkey Wrap + Milk":           { calories: 520, carbs_g: 65, protein_g: 38, fat_g: 14 },
  "Chicken + Brown Rice + Veg":   { calories: 580, carbs_g: 62, protein_g: 46, fat_g: 14 },
  "Eggs + Toast + Greek Yogurt":  { calories: 480, carbs_g: 44, protein_g: 34, fat_g: 16 },
  "Greek Yogurt + Banana":        { calories: 280, carbs_g: 42, protein_g: 20, fat_g:  3 },
  "Strength Day Protein Plate":   { calories: 640, carbs_g: 60, protein_g: 52, fat_g: 12 },
  "Cottage Cheese + Honey":       { calories: 240, carbs_g: 26, protein_g: 26, fat_g:  4 },
  "Eggs + Berries + Toast":       { calories: 420, carbs_g: 48, protein_g: 26, fat_g: 14 },
  "Salmon + Grain Bowl":          { calories: 520, carbs_g: 52, protein_g: 38, fat_g: 16 },
  "Almonds + Berries":            { calories: 180, carbs_g: 16, protein_g:  6, fat_g: 12 },
  "Iron-Boost Hummus Plate":      { calories: 420, carbs_g: 52, protein_g: 18, fat_g: 14 },
  "Cottage Cheese + Pineapple":   { calories: 250, carbs_g: 28, protein_g: 28, fat_g:  4 },
};

// ── Schedule builder ──────────────────────────────────────────────────────────
function buildSchedule(eventType, startTimeStr, durationHours) {
  const dur = (durationHours || 1.5) * 60;
  function at(h, m = 0) { const d = new Date(); d.setHours(h, m, 0, 0); return d; }
  let anchor = null;
  if (startTimeStr) { const [h, m] = startTimeStr.split(":").map(Number); anchor = at(h, m); }
  function fromAnchor(mins, dh = 16) { return new Date((anchor || at(dh)).getTime() + mins * 60_000); }
  const slot = (time, icon, label, meal, tip = null, urgent = false) =>
    ({ time, icon, label, meal, kcal: MACROS[meal]?.calories, tip, urgent, isMarker: false });
  const marker = (time, icon, label) => ({ time, icon, label, isMarker: true });

  switch (eventType) {
    case "game": return [
      slot(at(7),              "🌅", "Breakfast",       "Oatmeal + Eggs + OJ",      "Complex carbs + protein to start the day"),
      slot(fromAnchor(-210),   "🍝", "Pre-Game Meal",   "Power Pasta Bowl",          "HIGH carbs · LOW fat & fiber · Familiar foods only"),
      slot(fromAnchor(-60),    "🍌", "Pre-Game Snack",  "Banana + Peanut Butter",    "Easy-digest carbs only · No heavy food"),
      marker(anchor || at(16), "⚽", "KICKOFF"),
      slot(fromAnchor(dur+20), "🥛", "Recovery Window", "Chocolate Milk + Banana",   "3:1 carb:protein — critical 30-min window", true),
      slot(at(19),             "🍽️", "Dinner",          "Brown Rice Salmon Bowl",    "Full recovery meal"),
    ];
    case "tournament": return [
      slot(at(7),                  "🥞", "Tournament Breakfast",  "High-Carb Pancakes + Eggs", "Biggest carb meal of the day"),
      slot(fromAnchor(-60, 9),     "🍌", "Pre-Game Snack",        "Banana + Honey",            "Before every game"),
      marker(anchor || at(9),      "🏆", "GAME 1"),
      slot(fromAnchor(dur+15, 9),  "🥛", "Between-Games Recovery","Chocolate Milk + Banana",   "Refuel immediately — don't wait", true),
      slot(fromAnchor(dur+105, 9), "🍌", "Pre-Game 2 Top-Up",     "Crackers + Peanut Butter",  "60 min before next game"),
      marker(fromAnchor(dur+150, 9),"🏆","GAME 2"),
      slot(at(19),                 "🍝", "Tournament Dinner",      "Tournament Recovery Pasta", "Rebuild glycogen for tomorrow"),
      slot(at(21, 30),             "🌙", "Bedtime Snack",          "Greek Yogurt + Berries",    "Casein protein repairs muscles overnight"),
    ];
    case "practice": case "training": return [
      slot(at(7),              "🌅", "Breakfast",         "Oatmeal + Eggs + OJ",      "Energy baseline for the whole day"),
      slot(fromAnchor(-150),   "🍗", "Pre-Practice Meal", "Turkey Wrap + Milk",        "2.5 hrs to digest · Complex carbs + protein"),
      slot(fromAnchor(-45),    "🍌", "Top-Up Snack",      "Banana + Peanut Butter",    "Only if hungry — keep it light"),
      marker(anchor || at(16), "🏃", eventType === "training" ? "TRAINING" : "PRACTICE"),
      slot(fromAnchor(dur+15), "🥛", "Recovery Snack",    "Chocolate Milk + Banana",   "30-min window — muscle repair starts here", true),
      slot(new Date(Math.max(fromAnchor(dur+90).getTime(), at(18,30).getTime())),
                               "🍽️", "Dinner",            "Chicken + Brown Rice + Veg","Full recovery meal"),
      slot(at(21, 30),         "🌙", "Bedtime Snack",     "Greek Yogurt + Berries",    "Casein protein — repairs muscles overnight"),
    ];
    case "strength": return [
      slot(at(7),               "🥚", "Breakfast",           "Eggs + Toast + Greek Yogurt","Protein-rich start — strength days need it"),
      slot(fromAnchor(-90, 15), "🍗", "Pre-Strength Meal",   "Turkey Wrap + Milk",         "90 min to digest · Moderate carbs + protein"),
      marker(anchor || at(15),  "🏋️", "STRENGTH TRAINING"),
      slot(fromAnchor(dur+5,15),"🥛", "Post-Workout Window", "Greek Yogurt + Banana",      "20–30g protein within 30 min — non-negotiable", true),
      slot(at(19),              "🍽️", "Dinner",              "Strength Day Protein Plate", "Highest protein meal of the week"),
      slot(at(21, 30),          "🌙", "Bedtime Snack",       "Cottage Cheese + Honey",     "Casein — muscle synthesis runs all night"),
    ];
    default: return [
      slot(at(7, 30),  "🫐", "Breakfast",    "Eggs + Berries + Toast",    "Anti-inflammatory foods speed recovery"),
      slot(at(12),     "🥗", "Lunch",         "Salmon + Grain Bowl",       "Keep protein high — recovery continues 48 hrs"),
      slot(at(15),     "🥜", "Snack",          "Almonds + Berries",        "Antioxidants reduce inflammation"),
      slot(at(18, 30), "🍽️", "Dinner",        "Iron-Boost Hummus Plate",  "Iron + calcium focus on rest days"),
      slot(at(21, 30), "🌙", "Bedtime Snack", "Cottage Cheese + Pineapple","Casein protein — recovery doesn't stop on rest days"),
    ];
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt     = d => d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
const cdStr   = t => { const d = t - Date.now(); if (d <= 0) return null; const h = Math.floor(d/3_600_000), m = Math.floor((d%3_600_000)/60_000); return h > 0 ? `${h}h ${m}m` : `${m}m`; };
const greeting = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"; };
const scoreColor = s => s >= 90 ? "#0f4c35" : s >= 75 ? "#d97706" : s >= 50 ? "#ea580c" : "#dc2626";
const scoreLabel = s => s >= 90 ? "Elite Fueler" : s >= 75 ? "Game Ready" : s >= 50 ? "Getting There" : "Needs Fuel";
const scoreEmoji = s => s >= 90 ? "🔥" : s >= 75 ? "✅" : s >= 50 ? "📈" : "⚠️";

// ── Event Hero ────────────────────────────────────────────────────────────────
function EventHero({ event, dayType, athlete }) {
  const day   = DAY_CFG[dayType] || DAY_CFG.rest;
  const photo = DAY_PHOTO[dayType] || DAY_PHOTO.rest;
  const eventTime = event?.start_time ? (() => {
    const [h, m] = event.start_time.split(":").map(Number);
    const d = new Date(); d.setHours(h, m, 0, 0); return d;
  })() : null;
  const cd = eventTime ? cdStr(eventTime) : null;
  const inProgress = eventTime && !cd && (Date.now() - eventTime.getTime()) < (event?.duration_hours || 1.5) * 3_600_000;
  const complete   = eventTime && !cd && !inProgress;

  return (
    <div style={hero.wrap}>
      <img src={photo} alt={day.label} style={hero.img} loading="lazy" />
      {/* dark tint */}
      <div style={hero.tint} />
      {/* bottom gradient so text is readable */}
      <div style={hero.fade} />

      <div style={hero.content}>
        {/* Top row — greeting + badge */}
        <div style={hero.topRow}>
          <div style={hero.greeting}>{greeting()}, {athlete.first_name} 👋</div>
          <div style={{ ...hero.badge, background: day.color }}>{day.emoji} {day.label}</div>
        </div>

        {/* Event name */}
        <div style={hero.eventName}>
          {event?.event_name || `${day.label} — No events`}
        </div>
        {event?.start_time && (
          <div style={hero.eventMeta}>
            Today · {fmt(eventTime)}{event.city ? ` · ${event.city}` : ""}
          </div>
        )}

        {/* Countdown chip */}
        {eventTime && (
          <div style={hero.chipRow}>
            {cd
              ? <div style={hero.chip}>⏱ Kickoff in <strong>{cd}</strong></div>
              : inProgress
              ? <div style={{ ...hero.chip, background: "rgba(16,185,129,0.9)" }}>🟢 In Progress</div>
              : complete
              ? <div style={{ ...hero.chip, background: "rgba(100,116,139,0.9)" }}>✓ Complete</div>
              : null
            }
          </div>
        )}
      </div>
    </div>
  );
}
const hero = {
  wrap:      { position: "relative", borderRadius: "18px", overflow: "hidden", height: "200px", marginBottom: "20px" },
  img:       { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" },
  tint:      { position: "absolute", inset: 0, background: "rgba(0,0,0,0.45)" },
  fade:      { position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 50%)" },
  content:   { position: "relative", zIndex: 1, padding: "16px 18px", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" },
  topRow:    { display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" },
  greeting:  { fontSize: "14px", fontWeight: "600", color: "rgba(255,255,255,0.85)" },
  badge:     { fontSize: "11px", fontWeight: "800", color: "#fff", padding: "4px 10px", borderRadius: "99px", letterSpacing: "0.04em", flexShrink: 0 },
  eventName: { fontSize: "22px", fontWeight: "800", color: "#fff", lineHeight: 1.2 },
  eventMeta: { fontSize: "13px", color: "rgba(255,255,255,0.7)", marginTop: "2px" },
  chipRow:   { display: "flex", gap: "8px" },
  chip:      { display: "inline-flex", alignItems: "center", gap: "6px", background: "rgba(0,0,0,0.5)", backdropFilter: "blur(6px)", border: "1px solid rgba(255,255,255,0.2)", color: "#fff", fontSize: "13px", fontWeight: "600", padding: "6px 14px", borderRadius: "99px" },
};

// ── Fuel Score Card ───────────────────────────────────────────────────────────
function FuelScoreCard({ fuelScore, consumed, targets, accentColor }) {
  const score = fuelScore?.fuel_score;
  const color = score != null ? scoreColor(score) : "#9ca3af";
  const r = 36, circ = 2 * Math.PI * r;
  const fill = score != null ? circ - (score / 100) * circ : circ;

  const bars = [
    { label: "Calories",  val: Math.round(consumed.calories),  target: targets.total_calories, unit: "kcal", color: accentColor },
    { label: "Protein",   val: Math.round(consumed.protein_g), target: Math.round((targets.protein_g_min + targets.protein_g_max) / 2), unit: "g", color: "#d97706" },
    { label: "Hydration", val: Math.round(consumed.water_oz),  target: targets.hydration_oz_max, unit: "oz", color: "#0ea5e9" },
  ];

  return (
    <div style={fc.card}>
      {/* Left — score ring */}
      <div style={fc.ringWrap}>
        <div style={{ position: "relative", width: 88, height: 88, flexShrink: 0 }}>
          <svg width="88" height="88" viewBox="0 0 88 88">
            <circle cx="44" cy="44" r={r} fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle cx="44" cy="44" r={r} fill="none" stroke={color} strokeWidth="8"
              strokeDasharray={circ} strokeDashoffset={fill} strokeLinecap="round"
              transform="rotate(-90 44 44)" style={{ transition: "stroke-dashoffset 0.8s ease" }} />
          </svg>
          <div style={fc.ringInner}>
            {score != null
              ? <><div style={{ ...fc.scoreNum, color }}>{score}</div><div style={fc.scoreOf}>/100</div></>
              : <div style={fc.scoreDash}>—</div>
            }
          </div>
        </div>
        <div style={{ ...fc.scoreLbl, color }}>
          {score != null ? `${scoreEmoji(score)} ${scoreLabel(score)}` : "Log meals"}
        </div>
      </div>

      {/* Right — macro bars */}
      <div style={fc.bars}>
        {bars.map(b => {
          const pct = Math.min(100, b.target > 0 ? Math.round(b.val / b.target * 100) : 0);
          const over = b.val > b.target;
          return (
            <div key={b.label} style={fc.barRow}>
              <div style={fc.barTop}>
                <span style={fc.barLabel}>{b.label}</span>
                <span style={{ ...fc.barVal, color: over ? "#dc2626" : "#111827" }}>
                  {b.val}<span style={fc.barUnit}>{b.unit}</span>
                </span>
              </div>
              <div style={fc.track}>
                <div style={{ ...fc.fill, width: `${pct}%`, background: over ? "#dc2626" : b.color }} />
              </div>
              <div style={fc.barTarget}>{b.target}{b.unit} target</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
const fc = {
  card:      { background: "#fff", border: "1.5px solid #e5e7eb", borderRadius: "16px", padding: "16px", display: "flex", gap: "16px", alignItems: "flex-start", marginBottom: "20px", boxShadow: "0 2px 12px rgba(0,0,0,0.06)" },
  ringWrap:  { display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, gap: "4px" },
  ringInner: { position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" },
  scoreNum:  { fontSize: "20px", fontWeight: "900", lineHeight: 1 },
  scoreOf:   { fontSize: "10px", color: "#9ca3af" },
  scoreDash: { fontSize: "22px", fontWeight: "800", color: "#9ca3af" },
  scoreLbl:  { fontSize: "11px", fontWeight: "700", textAlign: "center", marginTop: "2px" },
  bars:      { flex: 1, minWidth: 0 },
  barRow:    { marginBottom: "10px" },
  barTop:    { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" },
  barLabel:  { fontSize: "11px", fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" },
  barVal:    { fontSize: "14px", fontWeight: "800" },
  barUnit:   { fontSize: "10px", fontWeight: "400", color: "#9ca3af", marginLeft: "1px" },
  track:     { height: "5px", background: "#f3f4f6", borderRadius: "99px", overflow: "hidden", marginBottom: "2px" },
  fill:      { height: "100%", borderRadius: "99px", transition: "width 0.6s ease" },
  barTarget: { fontSize: "10px", color: "#9ca3af" },
};

// ── Timeline row ──────────────────────────────────────────────────────────────
function TimelineRow({ item, status, accentColor, accentLight, onLog, logging, logged }) {
  if (item.isMarker) return (
    <div style={tr.markerRow}>
      <div style={{ ...tr.markerLine, background: accentColor + "55" }} />
      <div style={{ ...tr.markerBadge, background: accentColor }}>{item.icon} {item.label}</div>
      <div style={{ ...tr.markerLine, background: accentColor + "55" }} />
    </div>
  );

  const isPast = status === "past" || logged;
  const isNext = status === "next" && !logged;
  const dotClr = isPast ? "#d1d5db" : accentColor;
  const photo  = MEAL_PHOTO[item.label];

  return (
    <div style={tr.row}>
      {/* Time column */}
      <div style={tr.timeCol}>
        <div style={{ ...tr.timeText, color: isPast ? "#9ca3af" : isNext ? accentColor : "#374151" }}>
          {fmt(item.time)}
        </div>
      </div>

      {/* Connector */}
      <div style={tr.connector}>
        {isNext
          ? <div style={{ ...tr.dotRing, borderColor: accentColor }}><div style={{ ...tr.dot, background: accentColor }} /></div>
          : <div style={{ ...tr.dot, background: dotClr, margin: "4px 0" }} />
        }
        <div style={{ ...tr.line, background: isPast ? "#f3f4f6" : accentColor + "30" }} />
      </div>

      {/* Content */}
      <div style={{ ...tr.content, opacity: isPast ? 0.42 : 1 }}>
        {isNext ? (
          // ── Highlighted "UP NEXT" card ──
          <div style={{ ...tr.nextCard, borderColor: accentColor, background: accentLight }}>
            <div style={tr.nextTop}>
              <div style={tr.nextLeft}>
                <div style={tr.nextBadge(accentColor)}>UP NEXT</div>
                <div style={tr.nextTitle}>{item.icon} {item.label}</div>
                <div style={tr.nextMealName}>{item.meal}</div>
                {item.kcal && <div style={tr.nextKcal}>{item.kcal} kcal</div>}
              </div>
              {photo && (
                <img
                  src={photo} alt={item.label} loading="lazy"
                  style={{ ...tr.nextPhoto, borderColor: accentColor + "44" }}
                  onError={e => e.target.style.display = "none"}
                />
              )}
            </div>
            {item.tip && (
              <div style={{ ...tr.tip, borderLeftColor: accentColor }}>
                {item.urgent ? "⚠ " : "💡 "}{item.tip}
              </div>
            )}
            <button
              style={{ ...tr.logBtn, background: accentColor, opacity: logging ? 0.6 : 1 }}
              onClick={() => onLog(item)} disabled={logging}
            >
              {logging ? "Logging…" : "✓ Log This Meal"}
            </button>
          </div>
        ) : (
          // ── Regular row ──
          <div style={tr.normalRow}>
            <div style={tr.normalMain}>
              <div style={tr.normalLabel}>
                {isPast && <span style={{ color: "#9ca3af" }}>✓ </span>}
                {item.icon} {item.label}
              </div>
              <div style={tr.normalMeal}>{item.meal}{item.kcal ? ` · ${item.kcal} kcal` : ""}</div>
              {!isPast && item.tip && item.urgent && (
                <div style={tr.urgentTip}>⚠ {item.tip}</div>
              )}
            </div>
            {photo && !isPast && (
              <img
                src={photo} alt={item.label} loading="lazy"
                style={tr.thumbPhoto}
                onError={e => e.target.style.display = "none"}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
const tr = {
  row:        { display: "flex", alignItems: "flex-start" },
  timeCol:    { width: "76px", flexShrink: 0, textAlign: "right", paddingRight: "14px", paddingTop: "8px" },
  timeText:   { fontSize: "12px", fontWeight: "700" },
  connector:  { display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: "20px" },
  dot:        { width: "11px", height: "11px", borderRadius: "50%", flexShrink: 0 },
  dotRing:    { width: "19px", height: "19px", borderRadius: "50%", border: "2px solid", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  line:       { width: "2px", flex: 1, minHeight: "24px" },
  content:    { flex: 1, paddingLeft: "12px", paddingBottom: "10px", paddingTop: "4px" },
  // next card
  nextCard:   { border: "2px solid", borderRadius: "14px", padding: "14px", overflow: "hidden" },
  nextTop:    { display: "flex", justifyContent: "space-between", gap: "10px", marginBottom: "10px" },
  nextLeft:   { flex: 1, minWidth: 0 },
  nextBadge:  c => ({ display: "inline-block", background: c, color: "#fff", fontSize: "10px", fontWeight: "800", letterSpacing: "0.08em", padding: "2px 8px", borderRadius: "99px", marginBottom: "6px" }),
  nextTitle:  { fontSize: "15px", fontWeight: "800", color: "#111827", marginBottom: "2px" },
  nextMealName:{ fontSize: "13px", fontWeight: "600", color: "#374151", marginBottom: "2px" },
  nextKcal:   { fontSize: "12px", color: "#6b7280" },
  nextPhoto:  { width: "72px", height: "72px", borderRadius: "12px", objectFit: "cover", flexShrink: 0, border: "2px solid" },
  tip:        { fontSize: "12px", color: "#374151", borderLeft: "3px solid", paddingLeft: "8px", lineHeight: 1.5, marginBottom: "10px", background: "rgba(0,0,0,0.03)", padding: "6px 8px", borderRadius: "0 6px 6px 0" },
  logBtn:     { width: "100%", padding: "10px", border: "none", borderRadius: "8px", color: "#fff", fontSize: "14px", fontWeight: "700", cursor: "pointer" },
  // normal row
  normalRow:  { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", paddingBottom: "2px" },
  normalMain: { flex: 1, minWidth: 0 },
  normalLabel:{ fontSize: "13px", fontWeight: "700", color: "#374151", marginBottom: "1px" },
  normalMeal: { fontSize: "12px", color: "#9ca3af" },
  urgentTip:  { fontSize: "11px", color: "#dc2626", marginTop: "2px", fontWeight: "600" },
  thumbPhoto: { width: "40px", height: "40px", borderRadius: "8px", objectFit: "cover", flexShrink: 0, border: "1.5px solid #e5e7eb" },
  // marker
  markerRow:  { display: "flex", alignItems: "center", gap: "8px", margin: "6px 0" },
  markerLine: { flex: 1, height: "1.5px" },
  markerBadge:{ flexShrink: 0, color: "#fff", fontSize: "12px", fontWeight: "800", padding: "4px 14px", borderRadius: "99px" },
};

// ── Quick action buttons ───────────────────────────────────────────────────────
const ACTIONS = [
  { icon: "🍽️", label: "Log a Meal",   tab: "nutrition",  bg: "#f0fdf4", border: "#bbf7d0", ic: "#0f4c35" },
  { icon: "📅",  label: "Schedule",     tab: "schedule",   bg: "#eff6ff", border: "#bfdbfe", ic: "#2563eb" },
  { icon: "🍳",  label: "Meal Planner", tab: "meal-plan",  bg: "#fff7ed", border: "#fed7aa", ic: "#d97706" },
  { icon: "💧",  label: "Hydration",    tab: "hydration",  bg: "#f0f9ff", border: "#bae6fd", ic: "#0ea5e9" },
];

// ── Main ──────────────────────────────────────────────────────────────────────
export default function HomeScreen({ athlete, onNavigate }) {
  const [targets,     setTargets]     = useState(null);
  const [meals,       setMeals]       = useState([]);
  const [todayEvent,  setTodayEvent]  = useState(null);
  const [fuelScore,   setFuelScore]   = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [logging,     setLogging]     = useState(false);
  const [loggedSlots, setLoggedSlots] = useState(new Set());

  const fetchHome = useCallback(async () => {
    setLoading(true);
    try {
      const [tRes, mRes, evRes] = await Promise.all([
        fetch(`${API}/api/nutrition/targets/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/meals/athlete/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/events/athlete/${athlete.id}?date=${TODAY}`),
      ]);
      const t  = tRes.ok  ? await tRes.json()  : null;
      const m  = mRes.ok  ? await mRes.json()  : [];
      const ev = evRes.ok ? await evRes.json() : [];
      setTargets(t); setMeals(m); setTodayEvent(ev[0] || null);
      if (t) {
        const sr = await fetch(`${API}/api/reports/${athlete.id}/daily?date=${TODAY}`);
        if (sr.ok) { const sd = await sr.json(); if (sd.fuel_score !== undefined) setFuelScore(sd); }
      }
    } catch (_) {}
    finally { setLoading(false); }
  }, [athlete.id]);

  useEffect(() => { fetchHome(); }, [fetchHome]);

  const consumed = meals.reduce(
    (a, m) => ({ calories: a.calories + (m.calories||0), protein_g: a.protein_g + (m.protein_g||0), water_oz: a.water_oz + (m.water_oz||0) }),
    { calories: 0, protein_g: 0, water_oz: 0 }
  );

  const dayType  = todayEvent?.event_type || targets?.event_type || "rest";
  const day      = DAY_CFG[dayType] || DAY_CFG.rest;
  const schedule = buildSchedule(dayType, todayEvent?.start_time, todayEvent?.duration_hours);

  const now = Date.now();
  let nextFound = false;
  const statusMap = schedule.map(item => {
    if (item.isMarker) return "marker";
    if (!nextFound && item.time.getTime() > now - 30 * 60_000) { nextFound = true; return "next"; }
    if (!nextFound) return "past";
    return "upcoming";
  });

  async function handleLog(item) {
    if (logging || loggedSlots.has(item.label)) return;
    setLogging(true);
    const mac = MACROS[item.meal] || {};
    try {
      await fetch(`${API}/api/meals/${athlete.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ log_method: "meal-plan", description: `${item.label}: ${item.meal}`, ...mac, water_oz: 0 }),
      });
      setLoggedSlots(p => new Set([...p, item.label]));
      setMeals(p => [...p, { ...mac }]);
    } catch (_) {}
    finally { setLogging(false); }
  }

  if (loading) return (
    <div style={s.loadingWrap}>
      <div style={s.spinner} />
      <div style={s.loadingText}>Loading today's plan…</div>
    </div>
  );

  return (
    <div style={s.page}>

      {/* ── Photo hero ──────────────────────────────────────────────────────── */}
      <EventHero event={todayEvent} dayType={dayType} athlete={athlete} />

      {/* ── No schedule nudge ───────────────────────────────────────────────── */}
      {!targets && (
        <div style={s.nudge}>
          <span style={{ fontSize: "24px" }}>📅</span>
          <div style={{ flex: 1 }}>
            <div style={s.nudgeHead}>Add your schedule to unlock meal times</div>
            <div style={s.nudgeSub}>FuelUp calculates exact windows from your event's kick-off time.</div>
          </div>
          <button style={{ ...s.nudgeBtn, background: day.color }} onClick={() => onNavigate("schedule")}>Add →</button>
        </div>
      )}

      {/* ── Fuel score + macro progress ─────────────────────────────────────── */}
      {targets && (
        <div style={{ position: "relative" }}>
          <FuelScoreCard fuelScore={fuelScore} consumed={consumed} targets={targets} accentColor={day.color} />
          {/* invisible absolute inner for SVG ring overlay */}
        </div>
      )}

      {/* ── Meal timeline ───────────────────────────────────────────────────── */}
      <div style={s.sectionHead}>
        <div style={{ ...s.sectionDot, background: day.grad }} />
        <div style={s.sectionTitle}>Today's Fuel Schedule</div>
      </div>

      <div style={s.timeline}>
        {schedule.map((item, i) => (
          <TimelineRow
            key={i} item={item}
            status={statusMap[i]}
            logged={loggedSlots.has(item.label)}
            accentColor={day.color} accentLight={day.light}
            onLog={handleLog} logging={logging}
          />
        ))}
      </div>

      {/* ── AI quick fixes ──────────────────────────────────────────────────── */}
      {fuelScore?.gap_fix_suggestions?.length > 0 && (
        <div style={s.fixes}>
          <div style={s.fixesTitle}>💡 Quick fixes for today</div>
          {fuelScore.gap_fix_suggestions.slice(0, 3).map((sg, i) => (
            <div key={i} style={s.fixRow}><div style={{ ...s.fixDot, background: day.color }} />{sg}</div>
          ))}
        </div>
      )}

      <p style={s.disclaimer}>FuelUp provides educational food guidance — not medical nutrition therapy.</p>
    </div>
  );
}

const s = {
  page:        { fontFamily: "'Inter', -apple-system, sans-serif", paddingBottom: "8px" },
  loadingWrap: { display: "flex", flexDirection: "column", alignItems: "center", gap: "14px", padding: "60px 0" },
  spinner:     { width: "30px", height: "30px", border: "3px solid #e5e7eb", borderTopColor: "#0f4c35", borderRadius: "50%", animation: "spin 0.7s linear infinite" },
  loadingText: { fontSize: "14px", color: "#6b7280" },
  nudge:       { display: "flex", alignItems: "center", gap: "12px", background: "#fffbeb", border: "1.5px solid #fde68a", borderRadius: "12px", padding: "14px 16px", marginBottom: "20px" },
  nudgeHead:   { fontSize: "13px", fontWeight: "700", color: "#92400e", marginBottom: "2px" },
  nudgeSub:    { fontSize: "12px", color: "#92400e", opacity: 0.8 },
  nudgeBtn:    { flexShrink: 0, border: "none", color: "#fff", borderRadius: "8px", padding: "8px 14px", fontSize: "13px", fontWeight: "700", cursor: "pointer" },
  sectionHead: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" },
  sectionDot:  { width: "10px", height: "10px", borderRadius: "50%", flexShrink: 0 },
  sectionTitle:{ fontSize: "14px", fontWeight: "700", color: "#111827" },
  timeline:    { marginBottom: "24px" },
  fixes:       { background: "#fff7ed", border: "1.5px solid #fed7aa", borderRadius: "12px", padding: "14px 16px", marginBottom: "24px" },
  fixesTitle:  { fontSize: "13px", fontWeight: "700", color: "#92400e", marginBottom: "10px" },
  fixRow:      { display: "flex", alignItems: "flex-start", gap: "8px", marginBottom: "6px", fontSize: "13px", color: "#374151" },
  fixDot:      { width: "6px", height: "6px", borderRadius: "50%", flexShrink: 0, marginTop: "5px" },
  actionGrid:  { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "24px" },
  actionBtn:   { display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", borderRadius: "14px", padding: "18px 8px", cursor: "pointer" },
  actionIcon:  { width: "44px", height: "44px", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "22px" },
  actionLabel: { fontSize: "13px", fontWeight: "700" },
  disclaimer:  { textAlign: "center", fontSize: "11px", color: "#9ca3af", lineHeight: 1.6 },
};
