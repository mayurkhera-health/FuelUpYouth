import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL ?? "";

const EVENT_COLORS = {
  game:       { bg: "#fdf2f0", border: "#f4c0b8", text: "#c05a4a", label: "⚽ Game" },
  tournament: { bg: "#f4f1fb", border: "#c8bde8", text: "#7e6ab5", label: "🏆 Tournament" },
  practice:   { bg: "#fdf5e7", border: "#f4d3a0", text: "#c8903a", label: "🏃 Practice" },
  training:   { bg: "#fdf5e7", border: "#f4d3a0", text: "#c8903a", label: "💪 Training" },
  strength:   { bg: "#eef5fb", border: "#b8d8ef", text: "#4a8fc4", label: "🏋️ Strength" },
  rest:       { bg: "#f4f8f5", border: "#dce8e0", text: "#8aa898", label: "🌿 Rest" },
};

function getMondayOf(d) {
  const day = new Date(d);
  const diff = (day.getDay() + 6) % 7;
  day.setDate(day.getDate() - diff);
  day.setHours(0, 0, 0, 0);
  return day;
}

function addDays(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function toISO(d) {
  return d.toISOString().split("T")[0];
}

function formatWeekRange(monday) {
  const sunday = addDays(monday, 6);
  const fmt = (d) => d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${fmt(monday)} – ${fmt(sunday)}, ${monday.getFullYear()}`;
}

// ── CalorieSummaryBar ─────────────────────────────────────────────────────────
function CalorieSummaryBar({ planned, target }) {
  if (!target) return null;
  const pct = Math.min(100, Math.round((planned / target) * 100));
  const color = pct >= 90 ? "#2d6a4f" : pct >= 70 ? "#d97706" : "#dc2626";
  return (
    <div style={csb.wrap}>
      <div style={csb.track}>
        <div style={{ ...csb.fill, width: `${pct}%`, background: color }} />
      </div>
      <div style={csb.label}>
        <span style={{ color }}>{planned}</span>
        <span style={csb.target}> / {target} kcal</span>
      </div>
    </div>
  );
}
const csb = {
  wrap: { marginBottom: "8px" },
  track: { height: "5px", background: "#dce8e0", borderRadius: "99px", overflow: "hidden", marginBottom: "3px" },
  fill: { height: "100%", borderRadius: "99px", transition: "width 0.4s ease" },
  label: { fontSize: "14px", textAlign: "center", color: "#4a6358", fontWeight: "500" },
  target: { color: "#4a6358" },
};

// ── RecipePicker ──────────────────────────────────────────────────────────────
function RecipePicker({ slot, allRecipes, athleteAllergens, onSelect, onClose }) {
  const safeRecipes = allRecipes.filter(r => {
    if (r.category !== slot.recipe_category) return false;
    if (athleteAllergens.some(a => r.allergens.map(x => x.toLowerCase()).includes(a))) return false;
    return true;
  });

  return (
    <div style={rp.panel}>
      <div style={rp.header}>
        <span style={rp.title}>Choose a recipe</span>
        <button style={rp.close} onClick={onClose}>✕</button>
      </div>
      {safeRecipes.length === 0 ? (
        <div style={rp.empty}>No safe recipes found for this slot category.</div>
      ) : (
        <div style={rp.list}>
          {safeRecipes.map(r => (
            <button key={r.id} style={rp.option} onClick={() => onSelect(r)}>
              <div style={rp.optName}>{r.name}</div>
              <div style={rp.optMeta}>
                {r.macros.calories} kcal · {r.macros.carbs_g}g carbs · {r.macros.protein_g}g protein
              </div>
              {r.dietary.length > 0 && (
                <div style={rp.tags}>
                  {r.dietary.slice(0, 3).map(d => <span key={d} style={rp.tag}>{d}</span>)}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
const rp = {
  panel: { background: "#fff", border: "2px solid #0f4c35", borderRadius: "12px", padding: "12px", marginTop: "6px", boxShadow: "0 8px 24px rgba(0,0,0,0.12)", zIndex: 10 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" },
  title: { fontSize: "14px", fontWeight: "700", color: "#2d6a4f" },
  close: { background: "none", border: "none", cursor: "pointer", color: "#4a6358", fontSize: "16px", padding: "2px 6px" },
  empty: { fontSize: "14px", color: "#4a6358", textAlign: "center", padding: "12px 0" },
  list: { display: "flex", flexDirection: "column", gap: "6px", maxHeight: "200px", overflowY: "auto" },
  option: { background: "#f4f8f5", border: "1.5px solid #e5e7eb", borderRadius: "8px", padding: "8px 10px", cursor: "pointer", textAlign: "left" },
  optName: { fontSize: "14px", fontWeight: "700", color: "#1b3a2a", marginBottom: "2px" },
  optMeta: { fontSize: "13px", color: "#4a6358" },
  tags: { display: "flex", gap: "4px", marginTop: "4px", flexWrap: "wrap" },
  tag: { background: "#f0fdf4", color: "#2d6a4f", fontSize: "12px", fontWeight: "600", padding: "1px 6px", borderRadius: "99px" },
};

// ── SlotCard ──────────────────────────────────────────────────────────────────
function SlotCard({ slot, date, allRecipes, athleteAllergens, isActive, onOpenPicker, onClosePicker, onAssign, onAutoSwap, onClear, onLogEaten }) {
  const filled = !!slot.recipe_id;

  return (
    <div style={sc.wrap}>
      <div style={sc.label}>{slot.display_label}</div>

      {filled ? (
        <div style={{ ...sc.filledCard, ...(slot.is_ai_generated ? sc.aiCard : {}) }}>
          {slot.is_ai_generated && <div style={sc.aiBadge}>✨ AI</div>}
          <div style={sc.recipeName}>{slot.recipe_name}</div>
          <div style={sc.recipeCal}>{slot.calories} kcal</div>
          <div style={sc.actions}>
            {slot.logged ? (
              <div style={sc.eatenBadge}>✅ Eaten</div>
            ) : (
              <button style={sc.eatBtn} onClick={() => onLogEaten(date, slot.slot_name)}>
                ✓ Mark as Eaten
              </button>
            )}
            <button style={sc.swapBtn} onClick={() => onAutoSwap(date, slot.slot_name)} title="Get a different recipe">🔄</button>
            <button style={sc.clearBtn} onClick={() => onClear(date, slot.slot_name)} title="Remove">✕</button>
          </div>
        </div>
      ) : (
        <button style={sc.emptyCard} onClick={() => onOpenPicker(date, slot.slot_name)}>
          + Add
        </button>
      )}

      {isActive && (
        <RecipePicker
          slot={slot}
          allRecipes={allRecipes}
          athleteAllergens={athleteAllergens}
          onSelect={(recipe) => { onAssign(date, slot.slot_name, recipe); onClosePicker(); }}
          onClose={onClosePicker}
        />
      )}
    </div>
  );
}
const sc = {
  wrap: { marginBottom: "6px" },
  label: { fontSize: "13px", fontWeight: "700", color: "#4a6358", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "3px" },
  emptyCard: { width: "100%", minHeight: "44px", background: "none", border: "1.5px dashed #d1d5db", borderRadius: "8px", color: "#4a6358", fontSize: "14px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", boxSizing: "border-box" },
  filledCard: { background: "#f4f8f5", border: "1.5px solid #e5e7eb", borderRadius: "8px", padding: "8px", position: "relative" },
  aiCard: { background: "#f0fdf4", borderColor: "#b0e8c8" },
  aiBadge: { fontSize: "11px", fontWeight: "800", color: "#2d6a4f", marginBottom: "2px" },
  recipeName: { fontSize: "13px", fontWeight: "700", color: "#1b3a2a", lineHeight: 1.6, marginBottom: "2px" },
  recipeCal: { fontSize: "13px", color: "#4a6358", marginBottom: "6px" },
  actions: { display: "flex", gap: "4px", alignItems: "center", flexWrap: "wrap" },
  eatBtn: { flex: 1, background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "6px", padding: "4px 6px", fontSize: "13px", fontWeight: "700", cursor: "pointer", whiteSpace: "nowrap" },
  eatenBadge: { flex: 1, fontSize: "13px", fontWeight: "700", color: "#2d6a4f", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "6px", padding: "4px 6px", textAlign: "center" },
  swapBtn: { background: "#f0f4f1", border: "none", borderRadius: "6px", padding: "4px 6px", fontSize: "13px", cursor: "pointer" },
  clearBtn: { background: "#fef2f2", border: "none", borderRadius: "6px", padding: "4px 6px", fontSize: "13px", cursor: "pointer", color: "#dc2626" },
};

// ── DayColumn ─────────────────────────────────────────────────────────────────
function DayColumn({ day, allRecipes, athleteAllergens, activeSlot, onOpenPicker, onClosePicker, onAssign, onAutoSwap, onClear, onLogEaten }) {
  const evColor = EVENT_COLORS[day.event_type] || EVENT_COLORS.rest;
  const isToday = day.date === new Date().toISOString().split("T")[0];

  return (
    <div style={{ ...dc.col, ...(isToday ? dc.colToday : {}) }}>
      {/* Day header */}
      <div style={dc.header}>
        <div style={{ ...dc.dayLabel, ...(isToday ? dc.todayLabel : {}) }}>{day.day_label}</div>
        <div style={{ ...dc.dateNum, ...(isToday ? dc.todayNum : {}) }}>
          {new Date(day.date + "T12:00:00").getDate()}
        </div>
        <div style={{ ...dc.eventBadge, background: evColor.bg, color: evColor.text, borderColor: evColor.border }}>
          {evColor.label}
        </div>
        {day.event_name && <div style={dc.eventName}>{day.event_name.length > 14 ? day.event_name.slice(0,13) + "…" : day.event_name}</div>}
      </div>

      <CalorieSummaryBar planned={day.planned_calories} target={day.calorie_target} />

      {/* Slots */}
      {day.slots.map(slot => (
        <SlotCard
          key={slot.slot_name}
          slot={slot}
          date={day.date}
          allRecipes={allRecipes}
          athleteAllergens={athleteAllergens}
          isActive={activeSlot?.date === day.date && activeSlot?.slot === slot.slot_name}
          onOpenPicker={(date, slotName) => onOpenPicker(date, slotName)}
          onClosePicker={onClosePicker}
          onAssign={onAssign}
          onAutoSwap={onAutoSwap}
          onClear={onClear}
          onLogEaten={onLogEaten}
        />
      ))}
    </div>
  );
}
const dc = {
  col: { flex: "0 0 160px", minWidth: "140px", padding: "10px 8px", borderRight: "1px solid #f3f4f6" },
  colToday: { background: "#fafffe" },
  header: { textAlign: "center", marginBottom: "8px", paddingBottom: "8px", borderBottom: "1.5px solid #e5e7eb" },
  dayLabel: { fontSize: "13px", fontWeight: "700", color: "#4a6358", textTransform: "uppercase", letterSpacing: "0.06em" },
  todayLabel: { color: "#2d6a4f" },
  dateNum: { fontSize: "22px", fontWeight: "800", color: "#1b3a2a", lineHeight: 1.6, marginBottom: "4px" },
  todayNum: { color: "#2d6a4f" },
  eventBadge: { fontSize: "13px", fontWeight: "700", padding: "2px 6px", borderRadius: "99px", border: "1px solid", display: "inline-block", marginBottom: "2px" },
  eventName: { fontSize: "13px", color: "#4a6358", marginTop: "2px" },
};

// ── MealPlannerScreen ─────────────────────────────────────────────────────────
export default function MealPlannerScreen({ athlete, onNavigate, freshImport = false, onFreshImportSeen }) {
  const [weekStart, setWeekStart]     = useState(getMondayOf(new Date()));
  const [weekData, setWeekData]       = useState(null);
  const [allRecipes, setAllRecipes]   = useState([]);
  const [activeSlot, setActiveSlot]   = useState(null); // { date, slot }
  const [generating, setGenerating]   = useState(false);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const [aiReasoning, setAiReasoning] = useState("");
  const [overwriteWarning, setOverwriteWarning] = useState(false);

  const athleteAllergens = (athlete.allergies || "").split(",").map(a => a.trim().toLowerCase()).filter(Boolean);

  // Load recipes once
  useEffect(() => {
    fetch(`${API}/api/recipes/`)
      .then(r => r.json())
      .then(setAllRecipes)
      .catch(() => {});
  }, []);

  // Load week plan whenever weekStart changes
  const loadWeek = useCallback(async () => {
    setLoading(true); setError("");
    const res = await fetch(`${API}/api/meal-plans/${athlete.id}?week_start=${toISO(weekStart)}`);
    if (res.ok) setWeekData(await res.json());
    else setError("Failed to load meal plan.");
    setLoading(false);
  }, [athlete.id, weekStart]);

  useEffect(() => { loadWeek(); }, [loadWeek]);

  function prevWeek() { setWeekStart(addDays(weekStart, -7)); setActiveSlot(null); setAiReasoning(""); }
  function nextWeek() { setWeekStart(addDays(weekStart,  7)); setActiveSlot(null); setAiReasoning(""); }

  // Assign recipe to a slot
  async function handleAssign(date, slotName, recipe) {
    const res = await fetch(`${API}/api/meal-plans/${athlete.id}/slot`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_date: date, slot_name: slotName, recipe_id: recipe.id }),
    });
    if (res.ok) {
      const updated = await res.json();
      updateSlotInState(date, slotName, updated);
    }
  }

  // Auto-swap: pick a random different recipe from the same slot category
  function handleAutoSwap(date, slotName) {
    const day = weekData?.days.find(d => d.date === date);
    const slot = day?.slots.find(s => s.slot_name === slotName);
    if (!slot?.recipe_category) return;

    const safe = allRecipes.filter(r => {
      if (r.category !== slot.recipe_category) return false;
      if (athleteAllergens.some(a => r.allergens.map(x => x.toLowerCase()).includes(a))) return false;
      return true;
    });

    const alternatives = safe.filter(r => r.id !== slot.recipe_id);
    if (alternatives.length === 0) return;

    const pick = alternatives[Math.floor(Math.random() * alternatives.length)];
    handleAssign(date, slotName, pick);
  }

  // Clear a slot
  async function handleClear(date, slotName) {
    const res = await fetch(`${API}/api/meal-plans/${athlete.id}/slot?plan_date=${date}&slot_name=${slotName}`, { method: "DELETE" });
    if (res.ok) updateSlotInState(date, slotName, { recipe_id: null, recipe_name: null, calories: null, carbs_g: null, protein_g: null, fat_g: null, is_ai_generated: false, logged: false });
  }

  // Mark as eaten
  async function handleLogEaten(date, slotName) {
    const res = await fetch(`${API}/api/meal-plans/${athlete.id}/log-slot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_date: date, slot_name: slotName }),
    });
    if (res.ok) {
      updateSlotFieldInState(date, slotName, "logged", true);
    }
  }

  // Optimistic state update helpers
  function updateSlotInState(date, slotName, patch) {
    setWeekData(prev => {
      if (!prev) return prev;
      const days = prev.days.map(day => {
        if (day.date !== date) return day;
        const slots = day.slots.map(s => s.slot_name === slotName ? { ...s, ...patch } : s);
        const planned = slots.reduce((sum, s) => sum + (s.calories || 0), 0);
        return { ...day, slots, planned_calories: Math.round(planned) };
      });
      return { ...prev, days };
    });
  }

  function updateSlotFieldInState(date, slotName, field, value) {
    setWeekData(prev => {
      if (!prev) return prev;
      const days = prev.days.map(day => {
        if (day.date !== date) return day;
        const slots = day.slots.map(s => s.slot_name === slotName ? { ...s, [field]: value } : s);
        return { ...day, slots };
      });
      return { ...prev, days };
    });
  }

  // Generate AI plan
  async function handleGenerate(overwrite = false) {
    // Check if any slots are already filled
    if (!overwrite && weekData) {
      const filled = weekData.days.reduce((n, d) => n + d.slots.filter(s => s.recipe_id).length, 0);
      if (filled > 0) { setOverwriteWarning(true); return; }
    }
    setOverwriteWarning(false);
    setGenerating(true); setError(""); setAiReasoning("");
    const res = await fetch(`${API}/api/meal-plans/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: athlete.id, week_start: toISO(weekStart), overwrite_existing: overwrite }),
    });
    const data = await res.json();
    if (res.ok) {
      setWeekData(data);
      setAiReasoning(data.ai_reasoning || "");
    } else {
      setError(data.detail || "AI generation failed. Please try again.");
    }
    setGenerating(false);
  }

  const filledCount = weekData ? weekData.days.reduce((n, d) => n + d.slots.filter(s => s.recipe_id).length, 0) : 0;

  return (
    <div>
      {freshImport && (
        <div style={s.importBanner}>
          <div style={s.importBannerInner}>
            <div style={s.importBannerText}>
              <div style={s.importBannerTitle}>🎉 Schedule loaded — meal slots are ready!</div>
              <div style={s.importBannerSub}>Assign meals to each slot, or let AI generate the full week in one tap.</div>
            </div>
            <button style={s.importBannerClose} onClick={onFreshImportSeen}>✕</button>
          </div>
        </div>
      )}

      <h2 style={s.title}>🍳 Meal Planner</h2>
      <p style={s.subtitle}>
        Plan {athlete.first_name}'s meals for the week. Slots adapt to each day's training schedule.
        Tap any planned meal to log it as eaten.
      </p>

      {/* Week navigator */}
      <div style={s.navRow}>
        <button style={s.navBtn} onClick={prevWeek}>‹</button>
        <div style={s.weekLabel}>Week of {formatWeekRange(weekStart)}</div>
        <button style={s.navBtn} onClick={nextWeek}>›</button>
      </div>

      {/* Generate AI plan */}
      {overwriteWarning ? (
        <div style={s.overwriteWarn}>
          <span>{filledCount} slots are already planned. Overwrite them with AI suggestions?</span>
          <div style={s.overwriteActions}>
            <button style={s.overwriteYes} onClick={() => handleGenerate(true)}>Yes, overwrite</button>
            <button style={s.overwriteKeep} onClick={() => handleGenerate(false)}>Fill empty slots only</button>
            <button style={s.overwriteCancel} onClick={() => setOverwriteWarning(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button style={s.genBtn} onClick={() => handleGenerate(false)} disabled={generating}>
          {generating ? "✨ Building your week plan…" : "✨ Generate Week Plan"}
        </button>
      )}

      {error && <div style={s.errorBox}>{error}</div>}

      {aiReasoning && (
        <div style={s.reasoningBox}>
          <span style={s.reasoningLabel}>AI reasoning: </span>{aiReasoning}
        </div>
      )}

      {/* Week grid */}
      {loading ? (
        <div style={s.loadingMsg}>Loading plan…</div>
      ) : weekData ? (
        <div style={s.weekGrid}>
          {weekData.days.map(day => (
            <DayColumn
              key={day.date}
              day={day}
              allRecipes={allRecipes}
              athleteAllergens={athleteAllergens}
              activeSlot={activeSlot}
              onOpenPicker={(date, slot) => setActiveSlot({ date, slot })}
              onClosePicker={() => setActiveSlot(null)}
              onAssign={handleAssign}
              onAutoSwap={handleAutoSwap}
              onClear={handleClear}
              onLogEaten={handleLogEaten}
            />
          ))}
        </div>
      ) : null}

      {/* Legend */}
      <div style={s.legend}>
        <span style={s.legendItem}><span style={{ ...s.legendDot, background: "#2d6a4f" }} />AI generated</span>
        <span style={s.legendItem}><span style={{ ...s.legendDot, background: "#8aa898" }} />Manual</span>
        <span style={s.legendItem}>✅ = Logged to Nutrition tab</span>
      </div>

      <p style={s.disclaimer}>
        Meal plans are suggestions based on event type and nutrition targets.
        FuelUp provides educational food guidance — not medical nutrition therapy.
      </p>
    </div>
  );
}

const s = {
  importBanner: { margin: "0 0 16px", borderRadius: "14px", background: "linear-gradient(135deg, #0f4c35 0%, #1a7a54 100%)", padding: "1px" },
  importBannerInner: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", background: "linear-gradient(135deg, #0f4c35 0%, #1a7a54 100%)", borderRadius: "13px", padding: "16px 18px" },
  importBannerText: { flex: 1 },
  importBannerTitle: { fontSize: "17px", fontWeight: "700", color: "#ffffff", marginBottom: "3px" },
  importBannerSub: { fontSize: "15px", color: "#b7e4c7", lineHeight: 1.6 },
  importBannerClose: { background: "rgba(255,255,255,0.15)", border: "none", color: "#fff", borderRadius: "50%", width: "28px", height: "28px", cursor: "pointer", fontSize: "15px", flexShrink: 0 },

  title: { fontSize: "20px", fontWeight: "700", color: "#1b3a2a", margin: "0 0 4px" },
  subtitle: { fontSize: "15px", color: "#4a6358", marginBottom: "16px", lineHeight: 1.5 },

  navRow: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" },
  navBtn: { background: "#f0f4f1", border: "1.5px solid #e5e7eb", borderRadius: "8px", width: "36px", height: "36px", fontSize: "20px", cursor: "pointer", color: "#4a6358", fontWeight: "700" },
  weekLabel: { fontSize: "15px", fontWeight: "700", color: "#1b3a2a", textAlign: "center" },

  genBtn: { width: "100%", padding: "12px", background: "linear-gradient(135deg, #0f4c35, #1a7a54)", color: "#fff", border: "none", borderRadius: "10px", fontSize: "16px", fontWeight: "700", cursor: "pointer", marginBottom: "12px", letterSpacing: "0.01em" },

  overwriteWarn: { background: "#fffbeb", border: "1.5px solid #fde68a", borderRadius: "10px", padding: "12px 16px", marginBottom: "12px", fontSize: "15px", color: "#92400e" },
  overwriteActions: { display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" },
  overwriteYes: { background: "#dc2626", color: "#fff", border: "none", borderRadius: "7px", padding: "6px 14px", fontSize: "14px", fontWeight: "700", cursor: "pointer" },
  overwriteKeep: { background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "7px", padding: "6px 14px", fontSize: "14px", fontWeight: "700", cursor: "pointer" },
  overwriteCancel: { background: "#f0f4f1", color: "#4a6358", border: "1.5px solid #e5e7eb", borderRadius: "7px", padding: "6px 14px", fontSize: "14px", fontWeight: "600", cursor: "pointer" },

  errorBox: { background: "#fef2f2", border: "1.5px solid #fecaca", borderRadius: "8px", padding: "10px 14px", fontSize: "15px", color: "#dc2626", marginBottom: "12px" },
  reasoningBox: { background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "8px", padding: "10px 14px", fontSize: "14px", color: "#4a6358", marginBottom: "12px", lineHeight: 1.5 },
  reasoningLabel: { fontWeight: "700", color: "#2d6a4f" },

  loadingMsg: { textAlign: "center", color: "#4a6358", padding: "40px 0", fontSize: "16px" },

  weekGrid: { display: "flex", overflowX: "auto", border: "1.5px solid #e5e7eb", borderRadius: "12px", marginBottom: "16px", scrollbarWidth: "thin" },

  legend: { display: "flex", gap: "16px", fontSize: "13px", color: "#4a6358", marginBottom: "8px", flexWrap: "wrap" },
  legendItem: { display: "flex", alignItems: "center", gap: "4px" },
  legendDot: { width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" },

  disclaimer: { fontSize: "13px", color: "#8aa898", textAlign: "center", marginTop: "4px", lineHeight: 1.6 },
};
