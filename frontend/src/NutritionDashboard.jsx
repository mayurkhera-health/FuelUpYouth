import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL ?? "";
const TODAY = new Date().toISOString().split("T")[0];

const EVENT_LABELS = {
  game:       { label: "Game Day",        color: "#c05a4a", bg: "#fdf2f0", border: "#f4c0b8" },
  tournament: { label: "Tournament Day",  color: "#7e6ab5", bg: "#f4f1fb", border: "#c8bde8" },
  practice:   { label: "Practice Day",    color: "#c8903a", bg: "#fdf5e7", border: "#f4d3a0" },
  rest:       { label: "Rest Day",        color: "#2d6a4f", bg: "#f0faf4", border: "#b0e8c8" },
};

// ── SVG ring dial ─────────────────────────────────────────────────────────────
function MacroDial({ label, consumed, minVal, maxVal, unit, color, size = 110 }) {
  const target = maxVal || minVal || 1;
  const pct    = Math.min(1, consumed / target);
  const over   = consumed > maxVal && maxVal > 0;
  const near   = !over && maxVal > 0 && consumed / maxVal >= 0.85;
  const stroke = over ? "#dc2626" : near ? "#d97706" : color;

  const R    = 38;
  const circ = 2 * Math.PI * R;
  const dash = circ * pct;

  return (
    <div style={d.wrap}>
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "block", margin: "0 auto" }}>
        {/* Track */}
        <circle cx="50" cy="50" r={R} fill="none" stroke="#dce8e0" strokeWidth="9" />
        {/* Progress */}
        <circle
          cx="50" cy="50" r={R}
          fill="none"
          stroke={stroke}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          transform="rotate(-90 50 50)"
          style={{ transition: "stroke-dasharray 0.55s cubic-bezier(.4,0,.2,1), stroke 0.3s" }}
        />
        {/* Center value */}
        <text x="50" y="47" textAnchor="middle" fontSize="15" fontWeight="800"
          fill={over ? "#dc2626" : "#1b3a2a"} style={{ fontFamily: "inherit" }}>
          {Math.round(consumed)}
        </text>
        <text x="50" y="61" textAnchor="middle" fontSize="9" fill="#8aa898"
          style={{ fontFamily: "inherit" }}>
          {unit}
        </text>
      </svg>
      <div style={d.label}>{label}</div>
      <div style={d.range}>{minVal}–{maxVal}{unit}</div>
    </div>
  );
}

// Large calorie dial with different proportions
function CalorieDial({ consumed, target }) {
  const pct  = Math.min(1, consumed / (target || 1));
  const over = consumed > target * 1.1;
  const near = !over && pct >= 0.85;
  const stroke = over ? "#dc2626" : near ? "#d97706" : "#2d6a4f";

  const R    = 54;
  const circ = 2 * Math.PI * R;
  const dash = circ * pct;

  const statusText = over ? "Over target" : pct >= 0.9 ? "On track ✓" : pct >= 0.5 ? "In progress" : "Getting started";
  const pctLabel   = Math.round(pct * 100);

  return (
    <div style={{ textAlign: "center", marginBottom: "12px" }}>
      <svg width="160" height="160" viewBox="0 0 140 140" style={{ display: "block", margin: "0 auto" }}>
        {/* Outer glow ring */}
        <circle cx="70" cy="70" r={R + 8} fill="none" stroke={stroke} strokeWidth="1" opacity="0.12" />
        {/* Track */}
        <circle cx="70" cy="70" r={R} fill="none" stroke="#dce8e0" strokeWidth="11" />
        {/* Progress */}
        <circle
          cx="70" cy="70" r={R}
          fill="none"
          stroke={stroke}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          transform="rotate(-90 70 70)"
          style={{ transition: "stroke-dasharray 0.6s cubic-bezier(.4,0,.2,1), stroke 0.3s" }}
        />
        {/* Center content */}
        <text x="70" y="60" textAnchor="middle" fontSize="11" fill="#8aa898" style={{ fontFamily: "inherit" }}>Calories</text>
        <text x="70" y="82" textAnchor="middle" fontSize="26" fontWeight="800"
          fill={over ? "#dc2626" : "#1b3a2a"} style={{ fontFamily: "inherit" }}>
          {Math.round(consumed)}
        </text>
        <text x="70" y="97" textAnchor="middle" fontSize="10" fill="#8aa898" style={{ fontFamily: "inherit" }}>
          of {target} kcal
        </text>
      </svg>
      <div style={{ fontSize: "14px", fontWeight: "700", color: stroke, marginTop: "2px" }}>
        {pctLabel}% — {statusText}
      </div>
    </div>
  );
}

const d = {
  wrap:  { textAlign: "center", flex: "1 1 0" },
  label: { fontSize: "14px", fontWeight: "700", color: "#4a6358", marginTop: "4px" },
  range: { fontSize: "13px", color: "#4a6358", marginTop: "1px" },
};

export default function NutritionDashboard({ athlete }) {
  const [targets, setTargets]   = useState(null);
  const [timing, setTiming]     = useState(null);
  const [meals, setMeals]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");

  const [logOpen, setLogOpen]         = useState(false);
  const [logForm, setLogForm]         = useState({ description: "", mealType: "", servingSize: "", numServings: "1", water_oz: "" });
  const [baseMacros, setBaseMacros]   = useState(null); // macros for 1 serving from AI
  const [logLoading, setLogLoading]   = useState(false);
  const [logError, setLogError]       = useState("");
  const [estimating, setEstimating]   = useState(false);
  const [portionNote, setPortionNote] = useState("");
  const [estimateConf, setEstimateConf] = useState("");

  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");

  const fetchAll = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [tRes, mRes, timRes] = await Promise.all([
        fetch(`${API}/api/nutrition/targets/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/meals/athlete/${athlete.id}?date=${TODAY}`),
        fetch(`${API}/api/nutrition/timing/${athlete.id}?date=${TODAY}`),
      ]);
      if (!tRes.ok) throw new Error("Failed to load nutrition targets.");
      setTargets(await tRes.json());
      setMeals(mRes.ok ? await mRes.json() : []);
      setTiming(timRes.ok ? await timRes.json() : null);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [athlete.id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const consumed = meals.reduce(
    (acc, m) => ({
      calories: acc.calories + (m.calories || 0),
      carbs_g:  acc.carbs_g  + (m.carbs_g  || 0),
      protein_g:acc.protein_g+ (m.protein_g || 0),
      fat_g:    acc.fat_g    + (m.fat_g    || 0),
      water_oz: acc.water_oz + (m.water_oz  || 0),
    }),
    { calories: 0, carbs_g: 0, protein_g: 0, fat_g: 0, water_oz: 0 }
  );

  // Scale macros from base (1 serving) by current numServings
  function scaledMacros(base, servings) {
    const n = parseFloat(servings) || 1;
    return {
      calories:  Math.round((base.calories  || 0) * n),
      carbs_g:   Math.round((base.carbs_g   || 0) * n),
      protein_g: Math.round((base.protein_g || 0) * n),
      fat_g:     Math.round((base.fat_g     || 0) * n),
    };
  }

  async function lookupMacros(descOverride) {
    const desc = (descOverride ?? logForm.description).trim();
    if (desc.length < 3) return;
    setEstimating(true); setPortionNote(""); setEstimateConf(""); setBaseMacros(null);
    try {
      const res = await fetch(`${API}/api/nutrition/estimate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: athlete.id, description: desc }),
      });
      if (!res.ok) return;
      const data = await res.json();
      const base = { calories: data.calories || 0, carbs_g: data.carbs_g || 0, protein_g: data.protein_g || 0, fat_g: data.fat_g || 0 };
      setBaseMacros(base);
      setPortionNote(data.portion_note || "");
      setEstimateConf(data.confidence || "");
      // Apply to current serving count
      setLogForm(f => ({ ...f, ...Object.fromEntries(Object.entries(scaledMacros(base, f.numServings)).map(([k, v]) => [k, String(v)])) }));
    } catch (_) {}
    finally { setEstimating(false); }
  }

  // When user changes serving count, rescale the macros if we have a base
  function handleServingsChange(val) {
    setLogForm(f => {
      const updated = { ...f, numServings: val };
      if (baseMacros) {
        const scaled = scaledMacros(baseMacros, val);
        updated.calories  = String(scaled.calories);
        updated.carbs_g   = String(scaled.carbs_g);
        updated.protein_g = String(scaled.protein_g);
        updated.fat_g     = String(scaled.fat_g);
      }
      return updated;
    });
  }

  async function handleLogMeal(e) {
    e.preventDefault();
    if (!logForm.description.trim()) return setLogError("Please describe the meal.");
    if (!logForm.mealType) return setLogError("Please select a meal (Breakfast, Lunch, etc.).");
    setLogLoading(true); setLogError("");
    try {
      const servings = parseFloat(logForm.numServings) || 1;
      const macros   = baseMacros ? scaledMacros(baseMacros, servings)
                                  : { calories: parseFloat(logForm.calories) || 0, carbs_g: parseFloat(logForm.carbs_g) || 0, protein_g: parseFloat(logForm.protein_g) || 0, fat_g: parseFloat(logForm.fat_g) || 0 };
      const sizeLabel = logForm.servingSize ? `, ${servings} × ${logForm.servingSize}` : servings !== 1 ? `, ${servings} servings` : "";
      const fullDesc  = `${logForm.mealType}: ${logForm.description}${sizeLabel}`;

      const res = await fetch(`${API}/api/meals/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          athlete_id: athlete.id, log_method: "manual",
          description: fullDesc,
          calories: macros.calories, carbs_g: macros.carbs_g,
          protein_g: macros.protein_g, fat_g: macros.fat_g,
          iron_mg: 0, calcium_mg: 0,
          water_oz: parseFloat(logForm.water_oz) || 0,
          edamam_raw: null,
        }),
      });
      if (!res.ok) throw new Error("Failed to log meal.");
      setLogForm({ description: "", mealType: "", servingSize: "", numServings: "1", water_oz: "" });
      setPortionNote(""); setEstimateConf(""); setBaseMacros(null);
      setLogOpen(false);
      await fetchAll();
    } catch (err) { setLogError(err.message); }
    finally { setLogLoading(false); }
  }

  async function handleDeleteMeal(id) {
    await fetch(`${API}/api/meals/${id}`, { method: "DELETE" });
    await fetchAll();
  }

  async function runAnalysis() {
    setAnalysisLoading(true); setAnalysisError(""); setAnalysis(null);
    try {
      const res = await fetch(`${API}/api/analysis/${athlete.id}?date=${TODAY}`);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Analysis failed.");
      }
      setAnalysis(await res.json());
    } catch (e) { setAnalysisError(e.message); }
    finally { setAnalysisLoading(false); }
  }

  const eventStyle = targets ? (EVENT_LABELS[targets.event_type] || EVENT_LABELS.rest) : EVENT_LABELS.rest;
  const dateLabel  = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });

  if (loading) return <p style={s.center}>Loading nutrition data…</p>;
  if (error)   return <p style={{ ...s.center, color: "#dc2626" }}>{error}</p>;

  return (
    <div>
      <div style={s.dateLabel}>{dateLabel}</div>

      {targets && (
        <>
          <div style={{ ...s.dayBadge, background: eventStyle.bg, border: `1.5px solid ${eventStyle.border}`, color: eventStyle.color }}>
            {eventStyle.label}
            {targets.lea_alert && <span style={{ fontWeight: 400 }}> · ⚠️ Low Energy Availability Risk</span>}
          </div>

          {/* Calorie dial — large, centered */}
          <CalorieDial
            consumed={Math.round(consumed.calories)}
            target={targets.total_calories}
          />

          {/* Macro dials row */}
          <div style={s.dialRow}>
            <MacroDial label="Carbs"      consumed={Math.round(consumed.carbs_g)}   minVal={targets.carbs_g_min}      maxVal={targets.carbs_g_max}      unit="g"   color="#2563eb" />
            <MacroDial label="Protein"    consumed={Math.round(consumed.protein_g)} minVal={targets.protein_g_min}    maxVal={targets.protein_g_max}    unit="g"   color="#d97706" />
            <MacroDial label="Fat"        consumed={Math.round(consumed.fat_g)}     minVal={targets.fat_g_min}        maxVal={targets.fat_g_max}        unit="g"   color="#7c3aed" />
            <MacroDial label="Hydration"  consumed={Math.round(consumed.water_oz)}  minVal={targets.hydration_oz_min} maxVal={targets.hydration_oz_max} unit="oz"  color="#0ea5e9" />
          </div>

          {/* Micro targets */}
          <div style={s.microRow}>
            <div style={s.microCard}><div style={s.microVal}>{targets.iron_mg} mg</div><div style={s.microLabel}>Iron Target</div></div>
            <div style={s.microCard}><div style={s.microVal}>{targets.calcium_mg} mg</div><div style={s.microLabel}>Calcium Target</div></div>
          </div>
        </>
      )}

      {/* Meal timing */}
      {timing?.meals && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Meal Timing</div>
          {timing.meals.map((m, i) => (
            <div key={i} style={s.timingRow}>
              <div style={s.timingTime}>{m.timing}</div>
              <div><div style={s.timingName}>{m.meal_name}</div><div style={s.timingDesc}>{m.focus}</div></div>
            </div>
          ))}
        </div>
      )}

      {/* Meal log */}
      <div style={s.section}>
        <div style={s.sectionHeader}>
          <div style={s.sectionTitle}>Meals Logged Today</div>
          <button style={s.addBtn} onClick={() => setLogOpen(!logOpen)}>{logOpen ? "Cancel" : "+ Log Meal"}</button>
        </div>

        {logOpen && (
          <form onSubmit={handleLogMeal} style={s.logForm}>

            {/* ① Food description */}
            <label style={s.fieldLabel}>What did you eat?</label>
            <div style={s.descRow}>
              <input
                style={{ ...s.input, flex: 1, marginBottom: 0 }}
                placeholder="e.g. Grilled chicken with pasta and marinara"
                value={logForm.description}
                onChange={e => { setLogForm(f => ({ ...f, description: e.target.value })); setPortionNote(""); setEstimateConf(""); setBaseMacros(null); }}
                onBlur={e => lookupMacros(e.target.value)}
              />
              <button type="button" style={{ ...s.lookupBtn, opacity: estimating ? 0.7 : 1 }}
                onClick={() => lookupMacros(logForm.description)}
                disabled={estimating || logForm.description.trim().length < 3}>
                {estimating ? "Calculating…" : "Calculate"}
              </button>
            </div>

            {estimating && <div style={s.estimatingBanner}>Estimating nutrition values…</div>}
            {portionNote && !estimating && (
              <div style={{ ...s.estimateBanner, borderColor: estimateConf === "low" ? "#fde68a" : "#b0e8c8", background: estimateConf === "low" ? "#fffbeb" : "#f0fdf4", color: estimateConf === "low" ? "#92400e" : "#1b5e42" }}>
                {estimateConf === "low" ? "⚠️ " : "✓ "}Based on: <b>{portionNote}</b>
                {estimateConf === "low" && " — description vague, please verify"}.
              </div>
            )}

            {/* ② Meal type */}
            <label style={{ ...s.fieldLabel, marginTop: "14px" }}>Meal</label>
            <div style={s.chipRow}>
              {["Breakfast", "Lunch", "Dinner", "Snack", "Pre-Game", "Post-Game", "Halftime"].map(m => (
                <button key={m} type="button"
                  style={{ ...s.chip, ...(logForm.mealType === m ? s.chipActive : {}) }}
                  onClick={() => setLogForm(f => ({ ...f, mealType: m }))}>
                  {m}
                </button>
              ))}
            </div>

            {/* ③ Serving size */}
            <label style={{ ...s.fieldLabel, marginTop: "14px" }}>Serving Size</label>
            <div style={s.chipRow}>
              {["1 Cup", "1 Bowl", "1 Plate", "1 Piece", "1 Handful", "1 oz", "Custom"].map(sz => (
                <button key={sz} type="button"
                  style={{ ...s.chip, ...(logForm.servingSize === sz ? s.chipActive : {}) }}
                  onClick={() => setLogForm(f => ({ ...f, servingSize: sz }))}>
                  {sz}
                </button>
              ))}
            </div>

            {/* ④ Number of servings */}
            <label style={{ ...s.fieldLabel, marginTop: "14px" }}>Number of Servings</label>
            <div style={s.chipRow}>
              {["0.5", "1", "1.5", "2", "2.5", "3"].map(n => (
                <button key={n} type="button"
                  style={{ ...s.chip, ...(logForm.numServings === n ? s.chipActive : {}) }}
                  onClick={() => handleServingsChange(n)}>
                  {n}
                </button>
              ))}
            </div>

            {/* ⑤ Nutrition summary (auto-filled, editable) */}
            <div style={s.macroSummary}>
              <div style={s.macroSummaryTitle}>
                Nutrition {baseMacros ? <span style={s.aiTag}>AI estimated · tap to edit</span> : ""}
              </div>
              <div style={s.macroGrid}>
                {[
                  ["calories", "Calories", "kcal"],
                  ["carbs_g",  "Carbs",    "g"],
                  ["protein_g","Protein",  "g"],
                  ["fat_g",    "Fat",      "g"],
                  ["water_oz", "Water",    "oz"],
                ].map(([k, lbl, unit]) => (
                  <div key={k} style={s.macroField}>
                    <label style={s.inputLabel}>{lbl} <span style={s.unitLabel}>{unit}</span></label>
                    <input
                      style={{ ...s.smallInput, background: baseMacros && k !== "water_oz" ? "#f0fdf4" : "#fff", borderColor: baseMacros && k !== "water_oz" ? "#b0e8c8" : "#c8d8d0" }}
                      type="number" placeholder="0"
                      value={logForm[k] ?? ""}
                      onChange={e => { setLogForm(f => ({ ...f, [k]: e.target.value })); if (k !== "water_oz") setBaseMacros(null); }}
                    />
                  </div>
                ))}
              </div>
            </div>

            {logError && <p style={s.errorTxt}>{logError}</p>}
            <button style={s.saveBtn} type="submit" disabled={logLoading}>
              {logLoading ? "Saving…" : "Save Meal"}
            </button>
          </form>
        )}

        {meals.length === 0 && !logOpen && <p style={s.empty}>No meals logged yet today.</p>}
        {meals.map(m => {
          const colonIdx = m.description?.indexOf(":");
          const mealTag  = colonIdx > 0 ? m.description.slice(0, colonIdx) : null;
          const mealDesc = colonIdx > 0 ? m.description.slice(colonIdx + 1).trim() : m.description;
          return (
            <div key={m.id} style={s.mealRow}>
              <div style={{ flex: 1 }}>
                {mealTag && <div style={s.mealTag}>{mealTag}</div>}
                <div style={s.mealDesc}>{mealDesc}</div>
                <div style={s.mealMacros}>
                  {m.calories  ? `${Math.round(m.calories)} kcal`         : ""}
                  {m.carbs_g   ? ` · ${Math.round(m.carbs_g)}g carbs`     : ""}
                  {m.protein_g ? ` · ${Math.round(m.protein_g)}g protein`  : ""}
                  {m.fat_g     ? ` · ${Math.round(m.fat_g)}g fat`         : ""}
                </div>
              </div>
              <button style={s.deleteBtn} onClick={() => handleDeleteMeal(m.id)}>✕</button>
            </div>
          );
        })}
      </div>

      {/* AI Gap Analysis */}
      <div style={s.section}>
        <div style={s.sectionHeader}>
          <div>
            <div style={s.sectionTitle}>AI Nutrient Gap Analysis</div>
            <div style={s.analysisDesc}>Claude AI reviews today's meals vs. your targets.</div>
          </div>
          <button style={s.addBtn} onClick={runAnalysis} disabled={analysisLoading}>
            {analysisLoading ? "Analyzing…" : analysis ? "Re-run" : "Run Analysis"}
          </button>
        </div>
        {analysisError && <p style={s.errorTxt}>{analysisError}</p>}
        {analysis && (
          <div style={s.analysisCard}>
            {analysis.fuel_score !== undefined && (
              <div style={s.scoreRow}>
                <span style={s.scoreNum}>{analysis.fuel_score}</span>
                <span style={s.scoreLabel}>/ 100 Fuel Score</span>
              </div>
            )}
            {analysis.gap_fix_suggestions?.map((sg, i) => <div key={i} style={s.suggestion}>• {sg}</div>)}
            {analysis.lea_alert  && <div style={s.alertBox}>⚠️ LEA Risk: {analysis.lea_alert}</div>}
            {analysis.iron_alert && <div style={s.alertBox}>⚠️ Iron: {analysis.iron_alert}</div>}
          </div>
        )}
      </div>

      <p style={s.disclaimer}>FuelUp provides educational food guidance — not medical nutrition therapy.</p>
    </div>
  );
}

const s = {
  center: { textAlign: "center", color: "#4a6358", padding: "40px 0" },
  dateLabel: { fontSize: "16px", color: "#4a6358", marginBottom: "12px" },
  dayBadge: { display: "inline-block", padding: "6px 14px", borderRadius: "99px", fontSize: "15px", fontWeight: "700", marginBottom: "20px" },
  section: { marginBottom: "24px" },
  sectionHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" },
  sectionTitle: { fontSize: "16px", fontWeight: "700", color: "#1b3a2a", paddingBottom: "8px", borderBottom: "1.5px solid #e5e7eb", marginBottom: "12px" },
  dialRow: { display: "flex", gap: "4px", justifyContent: "space-around", marginBottom: "20px", padding: "8px 0", borderTop: "1.5px solid #f3f4f6", borderBottom: "1.5px solid #f3f4f6" },
  microRow: { display: "flex", gap: "12px", marginBottom: "24px" },
  microCard: { flex: 1, background: "#f4f8f5", borderRadius: "10px", padding: "14px", textAlign: "center" },
  microVal: { fontSize: "22px", fontWeight: "800", color: "#2d6a4f" },
  microLabel: { fontSize: "14px", color: "#4a6358", marginTop: "2px" },
  timingRow: { display: "flex", gap: "16px", marginBottom: "10px", padding: "10px 12px", background: "#f4f8f5", borderRadius: "8px" },
  timingTime: { fontSize: "14px", fontWeight: "700", color: "#2d6a4f", minWidth: "80px" },
  timingName: { fontSize: "15px", fontWeight: "600", color: "#1b3a2a" },
  timingDesc: { fontSize: "14px", color: "#4a6358", marginTop: "2px" },
  addBtn: { background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", padding: "6px 14px", fontSize: "15px", fontWeight: "600", cursor: "pointer" },
  logForm: { background: "#f4f8f5", border: "1.5px solid #e5e7eb", borderRadius: "12px", padding: "18px", marginBottom: "14px" },
  fieldLabel: { display: "block", fontSize: "14px", fontWeight: "700", color: "#4a6358", marginBottom: "7px", textTransform: "uppercase", letterSpacing: "0.05em" },
  descRow: { display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px" },
  input: { width: "100%", padding: "9px 12px", border: "1.5px solid #d1d5db", borderRadius: "8px", fontSize: "16px", boxSizing: "border-box", marginBottom: "0", outline: "none" },
  lookupBtn: { flexShrink: 0, padding: "9px 14px", background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", fontSize: "15px", fontWeight: "700", cursor: "pointer", whiteSpace: "nowrap" },
  estimatingBanner: { fontSize: "14px", color: "#2d6a4f", fontWeight: "600", padding: "7px 10px", background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "7px", marginTop: "8px" },
  estimateBanner: { fontSize: "14px", padding: "7px 10px", border: "1.5px solid", borderRadius: "7px", marginTop: "8px", lineHeight: 1.5 },
  chipRow: { display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "4px" },
  chip: { padding: "6px 12px", background: "#fff", border: "1.5px solid #d1d5db", borderRadius: "99px", fontSize: "14px", fontWeight: "600", color: "#4a6358", cursor: "pointer" },
  chipActive: { background: "#2d6a4f", borderColor: "#2d6a4f", color: "#fff" },
  macroSummary: { background: "#fff", border: "1.5px solid #e5e7eb", borderRadius: "10px", padding: "14px", marginTop: "14px", marginBottom: "12px" },
  macroSummaryTitle: { fontSize: "14px", fontWeight: "700", color: "#4a6358", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px", display: "flex", alignItems: "center", gap: "8px" },
  aiTag: { fontSize: "13px", fontWeight: "600", color: "#2d6a4f", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "99px", padding: "1px 8px", textTransform: "none", letterSpacing: 0 },
  macroGrid: { display: "flex", gap: "8px", flexWrap: "wrap" },
  macroField: { flex: "1 1 80px" },
  unitLabel: { fontWeight: "400", color: "#4a6358" },
  inputLabel: { display: "block", fontSize: "13px", fontWeight: "600", color: "#4a6358", marginBottom: "3px" },
  smallInput: { width: "100%", padding: "7px 8px", border: "1.5px solid #d1d5db", borderRadius: "6px", fontSize: "15px", boxSizing: "border-box", outline: "none" },
  saveBtn: { width: "100%", padding: "10px", background: "linear-gradient(135deg, #2d6a4f, #52b788)", color: "#fff", border: "none", borderRadius: "8px", fontSize: "16px", fontWeight: "700", cursor: "pointer" },
  mealRow: { display: "flex", alignItems: "flex-start", gap: "10px", padding: "10px 12px", background: "#f4f8f5", borderRadius: "8px", marginBottom: "6px" },
  mealTag: { fontSize: "12px", fontWeight: "800", color: "#2d6a4f", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "2px" },
  mealDesc: { fontSize: "15px", fontWeight: "600", color: "#1b3a2a" },
  mealMacros: { fontSize: "13px", color: "#4a6358", marginTop: "2px" },
  deleteBtn: { background: "none", border: "none", color: "#4a6358", cursor: "pointer", fontSize: "16px" },
  empty: { fontSize: "16px", color: "#4a6358", textAlign: "center", padding: "16px 0" },
  errorTxt: { color: "#dc2626", fontSize: "15px", marginBottom: "8px" },
  analysisDesc: { fontSize: "14px", color: "#4a6358", marginTop: "2px" },
  analysisCard: { background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "10px", padding: "14px" },
  scoreRow: { display: "flex", alignItems: "baseline", gap: "6px", marginBottom: "10px" },
  scoreNum: { fontSize: "36px", fontWeight: "800", color: "#2d6a4f" },
  scoreLabel: { fontSize: "16px", color: "#4a6358" },
  suggestion: { fontSize: "15px", color: "#4a6358", marginBottom: "4px" },
  alertBox: { background: "#fffbeb", border: "1.5px solid #fde68a", borderRadius: "8px", padding: "8px 12px", fontSize: "15px", color: "#92400e", marginTop: "8px" },
  disclaimer: { textAlign: "center", fontSize: "13px", color: "#8aa898", marginTop: "8px" },
};
