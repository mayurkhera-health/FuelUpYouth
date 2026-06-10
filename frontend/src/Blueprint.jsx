import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL ?? "";

// ── Food source emoji map ─────────────────────────────────────────────────────
const FOOD_EMOJI = {
  "lean red meat": "🥩", "grass-fed": "🥩", "spinach": "🥬", "lentils": "🫘",
  "hummus": "🫙", "fortified cereal": "🥣", "milk": "🥛", "plant milk": "🥛",
  "greek yogurt": "🫙", "cottage cheese": "🧀", "broccoli": "🥦", "kale": "🥬",
  "chicken": "🍗", "eggs": "🥚", "fish": "🐟", "salmon": "🐟",
  "avocado": "🥑", "nuts": "🥜", "olive oil": "🫒", "banana": "🍌",
  "oats": "🌾", "rice": "🍚", "pasta": "🍝", "fruit": "🍓",
  "bell peppers": "🫑", "orange juice": "🍊", "strawberries": "🍓",
};

function foodEmoji(label) {
  const lower = label.toLowerCase();
  for (const [key, emoji] of Object.entries(FOOD_EMOJI)) {
    if (lower.includes(key)) return emoji;
  }
  return "🥗";
}

// ── Section header with icon image strip ─────────────────────────────────────
function SectionHeader({ icon, title, subtitle }) {
  return (
    <div style={sh.wrap}>
      <div style={sh.iconCircle}>{icon}</div>
      <div>
        <h2 style={sh.title}>{title}</h2>
        {subtitle && <p style={sh.sub}>{subtitle}</p>}
      </div>
    </div>
  );
}
const sh = {
  wrap: { display: "flex", alignItems: "center", gap: "14px", marginBottom: "16px" },
  iconCircle: { width: "48px", height: "48px", borderRadius: "14px", background: "linear-gradient(135deg, #1b4332, #52b788)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "22px", flexShrink: 0, boxShadow: "0 4px 12px rgba(27,67,50,0.22)" },
  title: { fontSize: "17px", fontWeight: "800", color: "#1b3a2a", margin: 0 },
  sub: { fontSize: "12px", color: "#8aa898", margin: "2px 0 0" },
};


// ── Event icons ───────────────────────────────────────────────────────────────
const EVENT_ICONS = {
  rest: "😴", practice: "🏋️", game: "⚽", tournament: "🏆", strength: "💪"
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function SectionCard({ children, style = {} }) {
  return <div style={{ ...s.card, ...style }}>{children}</div>;
}

function BothVoices({ parentText, athleteText }) {
  return (
    <div style={s.bothVoices}>
      {parentText && <p style={s.voiceText}>{parentText}</p>}
      {athleteText && parentText !== athleteText && (
        <p style={s.athleteText}>⚽ {athleteText}</p>
      )}
    </div>
  );
}


function UrgencyBadge({ level }) {
  const map = {
    critical: { bg: "#fee2e2", color: "#dc2626", text: "⚠ CRITICAL" },
    important: { bg: "#fef3c7", color: "#d97706", text: "▲ IMPORTANT" },
    normal:   { bg: "#f0fdf4", color: "#2d6a4f", text: "✓ NORMAL" },
  };
  const c = map[level] || map.normal;
  return <span style={{ ...s.badge, background: c.bg, color: c.color }}>{c.text}</span>;
}

// ── Macro tab data ────────────────────────────────────────────────────────────
const MACRO_TABS = [
  { key: "carbs",   label: "Carbs",   emoji: "🍞", color: "#c8903a", light: "#fdf5e7", photo: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&q=80", alt: "Rice and grains" },
  { key: "protein", label: "Protein", emoji: "🥩", color: "#c05a4a", light: "#fdf2f0", photo: "https://images.unsplash.com/photo-1603048297172-c92544798d5a?w=600&q=80", alt: "Grilled chicken" },
  { key: "fat",     label: "Fats",    emoji: "🥑", color: "#2d6a4f", light: "#f0faf4", photo: "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80", alt: "Avocado and nuts" },
];

function MacroTabs({ macros }) {
  const [active, setActive] = useState("carbs");
  const tab = MACRO_TABS.find(t => t.key === active);
  const m   = macros?.[active];
  if (!m) return null;
  return (
    <div>
      {/* Tab pills */}
      <div style={mt.tabRow}>
        {MACRO_TABS.map(t => (
          <button
            key={t.key}
            style={{ ...mt.tab, ...(active === t.key ? { ...mt.tabActive, background: t.color, borderColor: t.color } : {}) }}
            onClick={() => setActive(t.key)}
          >
            <span style={mt.tabEmoji}>{t.emoji}</span>
            {t.label}
          </button>
        ))}
      </div>
      {/* Content panel */}
      <div style={{ ...mt.panel, borderTopColor: tab.color }}>
        {/* Photo strip */}
        <div style={mt.photoStrip}>
          <img src={tab.photo} alt={tab.alt} style={mt.photo} />
          <div style={{ ...mt.photoOverlay, background: `linear-gradient(to right, rgba(0,0,0,0) 40%, ${tab.light} 100%)` }} />
          <div style={{ ...mt.photoBadge, background: tab.color }}>{tab.emoji} {tab.label}</div>
        </div>
        {/* Text */}
        <div style={mt.body}>
          <p style={mt.voiceText}>{m.parent_explanation}</p>
          {m.athlete_explanation && m.athlete_explanation !== m.parent_explanation && (
            <p style={mt.athleteText}>⚽ {m.athlete_explanation}</p>
          )}
          {m.why_it_matters && (
            <div style={{ ...mt.whyBox, borderLeftColor: tab.color }}>
              <span style={{ ...mt.whyLabel, color: tab.color }}>Why it matters</span>
              <p style={mt.whyText}>{m.why_it_matters}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const mt = {
  tabRow: { display: "flex", gap: "8px", marginBottom: "0" },
  tab: { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "5px", padding: "9px 6px", border: "1.5px solid #d1d5db", borderRadius: "10px 10px 0 0", background: "#f4f8f5", fontSize: "13px", fontWeight: "700", color: "#8aa898", cursor: "pointer", transition: "all 0.15s" },
  tabActive: { color: "#fff", borderBottomColor: "transparent" },
  tabEmoji: { fontSize: "16px" },
  panel: { border: "1.5px solid #e5e7eb", borderTop: "3px solid", borderRadius: "0 0 14px 14px", overflow: "hidden", marginTop: "-1px" },
  photoStrip: { position: "relative", height: "110px", overflow: "hidden" },
  photo: { width: "100%", height: "100%", objectFit: "cover", objectPosition: "center" },
  photoOverlay: { position: "absolute", inset: 0 },
  photoBadge: { position: "absolute", bottom: "10px", left: "12px", color: "#fff", fontSize: "13px", fontWeight: "800", padding: "3px 10px", borderRadius: "6px" },
  body: { padding: "14px", display: "flex", flexDirection: "column", gap: "8px" },
  voiceText: { fontSize: "13px", color: "#4a6358", lineHeight: 1.6, margin: 0, background: "#f4f8f5", padding: "12px", borderRadius: "10px" },
  athleteText: { fontSize: "13px", color: "#1b5e42", lineHeight: 1.6, margin: 0, background: "#f0fdf4", padding: "12px", borderRadius: "10px", fontStyle: "italic" },
  whyBox: { background: "#fff", border: "1px solid #e5e7eb", borderLeft: "3px solid", borderRadius: "8px", padding: "10px 12px" },
  whyLabel: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "4px" },
  whyText: { fontSize: "12px", color: "#4a6358", margin: 0, lineHeight: 1.5 },

  // Micro tab extras (photo top-right overlay, stat pill, food grid, tip)
  photoTopRight: { position: "absolute", top: "10px", right: "10px", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "5px" },
  statPill: { background: "rgba(255,255,255,0.92)", border: "1.5px solid", borderRadius: "8px", padding: "3px 9px", backdropFilter: "blur(4px)" },
  statPillVal: { fontSize: "14px", fontWeight: "900" },
  statPillUnit: { fontSize: "10px", color: "#8aa898", fontWeight: "400" },
  foodLabel: { fontSize: "11px", fontWeight: "700", color: "#8aa898", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "8px" },
  foodGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(84px, 1fr))", gap: "8px" },
  foodCard: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "8px 6px", textAlign: "center" },
  foodEmoji: { fontSize: "22px", marginBottom: "4px" },
  foodText: { fontSize: "10px", color: "#4a6358", lineHeight: 1.3, fontWeight: "500" },
  tipBox: { background: "#fefce8", border: "1px solid #fde68a", borderLeft: "3px solid", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", color: "#92400e", lineHeight: 1.5 },
};

// ── Micro tab data ────────────────────────────────────────────────────────────
const MICRO_TABS = [
  { key: "iron",      label: "Iron",       emoji: "🩸", color: "#dc2626", light: "#fef2f2", photo: "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80", alt: "Iron-rich foods" },
  { key: "calcium",   label: "Calcium",    emoji: "🦴", color: "#2563eb", light: "#eff6ff", photo: "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=600&q=80", alt: "Dairy and calcium foods" },
  { key: "magnesium", label: "Magnesium",  emoji: "⚡", color: "#7c3aed", light: "#f5f3ff", photo: "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=600&q=80", alt: "Nuts and seeds rich in magnesium" },
  { key: "vitamin_d", label: "Vitamin D",  emoji: "☀️", color: "#d97706", light: "#fffbeb", photo: "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80", alt: "Salmon and vitamin D foods" },
];

const MICRO_FALLBACK = {
  magnesium: {
    parent_explanation: "Magnesium powers over 300 enzymatic reactions including ATP energy production and muscle contraction. Youth athletes are frequently deficient, especially during growth spurts.",
    athlete_explanation: "Magnesium helps your muscles relax after a hard game — it's the mineral that prevents cramps. Almonds, pumpkin seeds, spinach, and dark chocolate are your best sources.",
    urgency_level: "important",
    food_sources: ["Pumpkin seeds", "Almonds + cashews", "Spinach + edamame", "Dark chocolate (70%+)", "Black beans + lentils"],
    absorption_tip: "Magnesium absorption improves when paired with vitamin B6-rich foods (chicken, bananas, potatoes).",
  },
  vitamin_d: {
    parent_explanation: "Vitamin D deficiency is extremely common in youth athletes. It governs calcium absorption — without it, even adequate calcium intake can't build bone — and supports muscle power output and immune function. Boston Children's Hospital recommends 1,000 IU/day for active youth athletes.",
    athlete_explanation: "Vitamin D is the 'sunshine vitamin' — it helps your body actually use the calcium you eat for stronger bones. Salmon, fortified milk, and eggs are your best food sources.",
    urgency_level: "important",
    food_sources: ["Salmon + tuna (best food source)", "Fortified milk or plant milk", "Egg yolks", "Fortified orange juice", "UV-exposed mushrooms"],
    absorption_tip: "Vitamin D is fat-soluble — eat D-rich foods alongside healthy fats (avocado, olive oil, nuts) for maximum absorption.",
  },
};

function MicroTabs({ micronutrients, cal }) {
  const [active, setActive] = useState("iron");
  const tab  = MICRO_TABS.find(t => t.key === active);
  const data = micronutrients?.[active] || MICRO_FALLBACK[active];

  const targetVal = active === "iron"      ? cal.iron_mg
                  : active === "calcium"   ? (cal.calcium_mg / 1000).toFixed(1)
                  : active === "magnesium" ? cal.magnesium_mg
                  : cal.vitamin_d_iu;
  const targetUnit = active === "calcium"   ? "g / day"
                   : active === "vitamin_d" ? "IU / day"
                   : "mg / day";

  return (
    <div>
      {/* Tab pills */}
      <div style={mt.tabRow}>
        {MICRO_TABS.map(t => (
          <button
            key={t.key}
            style={{ ...mt.tab, ...(active === t.key ? { ...mt.tabActive, background: t.color, borderColor: t.color } : {}) }}
            onClick={() => setActive(t.key)}
          >
            <span style={mt.tabEmoji}>{t.emoji}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content panel */}
      <div style={{ ...mt.panel, borderTopColor: tab.color }}>
        {/* Photo strip */}
        <div style={mt.photoStrip}>
          <img src={tab.photo} alt={tab.alt} style={mt.photo} />
          <div style={{ ...mt.photoOverlay, background: `linear-gradient(to right, rgba(0,0,0,0) 40%, ${tab.light} 100%)` }} />
          <div style={{ ...mt.photoBadge, background: tab.color }}>{tab.emoji} {tab.label}</div>
          {/* Urgency badge + stat pill float over photo */}
          <div style={mt.photoTopRight}>
            <UrgencyBadge level={data.urgency_level} />
            <div style={{ ...mt.statPill, borderColor: tab.color }}>
              <span style={{ ...mt.statPillVal, color: tab.color }}>{targetVal}</span>
              <span style={mt.statPillUnit}> {targetUnit}</span>
            </div>
          </div>
        </div>

        {/* Text + food grid */}
        <div style={mt.body}>
          <p style={mt.voiceText}>{data.parent_explanation}</p>
          {data.athlete_explanation && data.athlete_explanation !== data.parent_explanation && (
            <p style={mt.athleteText}>⚽ {data.athlete_explanation}</p>
          )}
          {data.food_sources?.length > 0 && (
            <div>
              <div style={mt.foodLabel}>Best food sources</div>
              <div style={mt.foodGrid}>
                {data.food_sources.map(f => (
                  <div key={f} style={mt.foodCard}>
                    <div style={mt.foodEmoji}>{foodEmoji(f)}</div>
                    <div style={mt.foodText}>{f}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {data.absorption_tip && (
            <div style={{ ...mt.tipBox, borderLeftColor: tab.color }}>
              💡 {data.absorption_tip}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function Blueprint({ athlete, onAddSchedule }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!athlete?.id) return;
    setLoading(true);
    fetch(`${API}/api/athletes/${athlete.id}/blueprint`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject("Failed to load Blueprint"))
      .then(json => { setData(json); setLoading(false); })
      .catch(e  => { setError(String(e)); setLoading(false); });
  }, [athlete?.id]);

  if (loading) return (
    <div style={s.center}>
      <div style={s.spinner} />
      <p style={s.loadingText}>Building your Nutrition Blueprint…</p>
    </div>
  );
  if (error) return (
    <div style={s.center}>
      <p style={{ color: "#dc2626", textAlign: "center" }}>⚠ {error}</p>
    </div>
  );
  if (!data) return null;

  const bp  = data.blueprint;
  const cal = data._calculated;
  const targets = cal.targets;

  const eventLabels = { rest: "Rest Day", practice: "Practice", game: "Game Day", tournament: "Tournament", strength: "Strength" };
  const eventColors = { rest: "#8aa898", practice: "#2563eb", game: "#dc2626", tournament: "#7c3aed", strength: "#d97706" };
  const eventBg    = { rest: "#f4f8f5", practice: "#eff6ff", game: "#fef2f2", tournament: "#faf5ff", strength: "#fffbeb" };

  return (
    <div style={s.wrapper}>

      {/* ── FIRST-RUN BANNER ── */}
      {onAddSchedule && (
        <div style={s.firstRunBanner}>
          <div style={s.bannerLeft}>
            <div style={s.bannerTitle}>🎉 Your Blueprint is ready!</div>
            <p style={s.bannerText}>
              Now add your athlete's training schedule — the app will automatically calculate
              game-day fuel plans, hydration needs, and personalized meal timing.
            </p>
          </div>
          <button style={s.bannerBtn} onClick={onAddSchedule}>➕ Add Schedule →</button>
        </div>
      )}

      {/* ── HERO ── */}
      <div style={s.heroOuter}>
        {/* Background photo */}
        <img
          src="https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800&q=80"
          alt="Youth soccer player"
          style={s.heroPhoto}
        />
        <div style={s.heroOverlay} />
        {/* Content */}
        <div style={s.heroContent}>
          <div style={s.heroBadge}>🏅 Nutrition Blueprint</div>
          <h1 style={s.heroHeadline}>{bp.hero?.headline}</h1>
          <p style={s.heroSub}>{bp.hero?.parent_subtext}</p>
          <div style={s.heroAthleteBox}>
            <span style={{ fontSize: "20px" }}>⚽</span>
            <p style={s.heroAthleteMsg}>{bp.hero?.athlete_message}</p>
          </div>
          {/* Stat strip */}
          <div style={s.heroStats}>
            <div style={s.heroStat}><div style={s.heroStatVal}>{cal.rmr.toLocaleString()}</div><div style={s.heroStatLabel}>RMR kcal</div></div>
            <div style={s.heroStatDivider} />
            <div style={s.heroStat}><div style={s.heroStatVal}>{cal.iron_mg}mg</div><div style={s.heroStatLabel}>Iron / day</div></div>
            <div style={s.heroStatDivider} />
            <div style={s.heroStat}><div style={s.heroStatVal}>{(cal.calcium_mg/1000).toFixed(1)}g</div><div style={s.heroStatLabel}>Calcium / day</div></div>
            <div style={s.heroStatDivider} />
            <div style={s.heroStat}><div style={s.heroStatVal}>{cal.ffm_kg}kg</div><div style={s.heroStatLabel}>Fat-free mass</div></div>
          </div>
        </div>
      </div>

      {/* ── RMR ── */}
      <SectionCard>
        <SectionHeader icon="🔥" title="Resting Metabolic Rate" subtitle="The calories your body burns at complete rest" />
        <div style={s.rmrRow}>
          <div style={s.rmrLeft}>
            <div style={s.bigNumber}>{cal.rmr.toLocaleString()}</div>
            <div style={s.bigUnit}>kcal / day</div>
            <p style={s.formulaNote}>{bp.rmr?.formula_note}</p>
          </div>
          <img
            src="https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&q=80"
            alt="Athlete resting"
            style={s.rmrPhoto}
          />
        </div>
        <BothVoices parentText={bp.rmr?.parent_explanation} athleteText={bp.rmr?.athlete_explanation} />
      </SectionCard>

      {/* ── CALORIE TARGETS ── */}
      <SectionCard>
        <SectionHeader icon="⚡" title="Daily Calorie Targets" subtitle="Automatically adjusts to your training day" />
        <BothVoices parentText={bp.calorie_range?.parent_explanation} athleteText={bp.calorie_range?.athlete_explanation} />
        {bp.calorie_range?.context_note && (
          <div style={s.contextNote}>💡 {bp.calorie_range.context_note}</div>
        )}
        <div style={s.eventGrid}>
          {Object.entries(targets).map(([et, t]) => (
            <div key={et} style={{ ...s.eventCard, background: eventBg[et], borderTopColor: eventColors[et] }}>
              <div style={s.eventIcon}>{EVENT_ICONS[et]}</div>
              <div style={{ ...s.eventLabel, color: eventColors[et] }}>{eventLabels[et]}</div>
              <div style={{ ...s.eventCal, color: eventColors[et] }}>{(t.total_calories || 0).toLocaleString()}</div>
              <div style={s.eventCalUnit}>kcal</div>
              <div style={s.eventMacros}>
                <span style={s.macroChip}>🍞 {t.carbs_g_min}–{t.carbs_g_max}g</span>
                <span style={s.macroChip}>🥩 {t.protein_g_min}–{t.protein_g_max}g</span>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* ── MACROS ── */}
      <SectionCard>
        <SectionHeader icon="🍽" title="Macronutrients" subtitle="Tap each fuel source to learn more" />
        <MacroTabs macros={bp.macros} />
      </SectionCard>

      {/* ── MICRONUTRIENTS ── */}
      <SectionCard>
        <SectionHeader icon="💊" title="Key Micronutrients" subtitle="Tap each nutrient to learn more" />
        <MicroTabs micronutrients={bp.micronutrients} cal={cal} />
      </SectionCard>

      {/* ── LEA WARNING ── */}
      {bp.lea_warning?.triggered && (
        <SectionCard style={s.leaCard}>
          <div style={s.leaHeader}>
            <div style={s.leaIconWrap}>⚠️</div>
            <h2 style={s.leaTitle}>Low Energy Availability Alert</h2>
          </div>
          <div style={s.leaPills}>
            <StatPill label="LEA threshold" value={cal.lea_threshold_kcal.toLocaleString()} unit="kcal/day" />
          </div>
          <p style={s.leaMsg}>{bp.lea_warning.parent_message}</p>
          {bp.lea_warning.action_required && (
            <div style={s.leaAction}>{bp.lea_warning.action_required}</div>
          )}
        </SectionCard>
      )}


      {/* ── FOOTER ── */}
      <p style={s.disclaimer}>{bp._meta?.generated_by} · {bp._meta?.disclaimer}</p>

    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  wrapper: { display: "flex", flexDirection: "column", gap: "16px", paddingBottom: "32px" },
  center: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 20px", gap: "16px" },
  spinner: { width: "40px", height: "40px", border: "3px solid #e5e7eb", borderTopColor: "#2d6a4f", borderRadius: "50%", animation: "spin 0.8s linear infinite" },
  loadingText: { color: "#8aa898", fontSize: "14px", margin: 0 },
  card: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: "16px", padding: "20px", overflow: "hidden" },

  // First-run banner
  firstRunBanner: { background: "linear-gradient(135deg, #0f4c35 0%, #1a7a54 100%)", borderRadius: "16px", padding: "20px", display: "flex", gap: "16px", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" },
  bannerLeft: { flex: 1, minWidth: "200px" },
  bannerTitle: { fontSize: "17px", fontWeight: "800", color: "#fff", marginBottom: "6px" },
  bannerText: { fontSize: "13px", color: "#b7e4c7", lineHeight: 1.6, margin: 0 },
  bannerBtn: { background: "#fff", color: "#2d6a4f", border: "none", borderRadius: "10px", padding: "12px 20px", fontSize: "14px", fontWeight: "800", cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0 },

  // Hero
  heroOuter: { position: "relative", borderRadius: "16px", overflow: "hidden", minHeight: "340px", display: "flex", alignItems: "flex-end" },
  heroPhoto: { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: "center top" },
  heroOverlay: { position: "absolute", inset: 0, background: "linear-gradient(to bottom, rgba(5,30,20,0.35) 0%, rgba(5,30,20,0.88) 100%)" },
  heroContent: { position: "relative", zIndex: 1, padding: "24px", width: "100%", boxSizing: "border-box" },
  heroBadge: { display: "inline-block", background: "rgba(255,255,255,0.15)", border: "1px solid rgba(255,255,255,0.25)", color: "#b7e4c7", fontSize: "11px", fontWeight: "700", letterSpacing: "0.07em", textTransform: "uppercase", padding: "4px 12px", borderRadius: "99px", marginBottom: "10px" },
  heroHeadline: { fontSize: "clamp(18px,3vw,24px)", fontWeight: "800", color: "#fff", margin: "0 0 8px", lineHeight: 1.2 },
  heroSub: { fontSize: "12px", color: "#b7e4c7", lineHeight: 1.6, margin: "0 0 12px", maxWidth: "480px" },
  heroAthleteBox: { display: "flex", gap: "8px", alignItems: "flex-start", background: "rgba(255,255,255,0.1)", borderRadius: "10px", padding: "10px 12px", marginBottom: "16px", border: "1px solid rgba(255,255,255,0.15)" },
  heroAthleteMsg: { margin: 0, fontSize: "12px", color: "#ecfdf5", fontStyle: "italic", lineHeight: 1.5 },
  heroStats: { display: "flex", gap: "0", background: "rgba(0,0,0,0.35)", borderRadius: "12px", overflow: "hidden", backdropFilter: "blur(4px)" },
  heroStat: { flex: 1, padding: "10px 8px", textAlign: "center" },
  heroStatVal: { fontSize: "16px", fontWeight: "900", color: "#fff" },
  heroStatLabel: { fontSize: "10px", color: "rgba(255,255,255,0.6)", marginTop: "2px", letterSpacing: "0.03em" },
  heroStatDivider: { width: "1px", background: "rgba(255,255,255,0.15)", margin: "8px 0" },

  // RMR
  rmrRow: { display: "flex", gap: "16px", alignItems: "flex-start", marginBottom: "14px" },
  rmrLeft: { flex: 1 },
  rmrPhoto: { width: "90px", height: "90px", borderRadius: "12px", objectFit: "cover", flexShrink: 0 },
  bigNumber: { fontSize: "44px", fontWeight: "900", color: "#2d6a4f", lineHeight: 1 },
  bigUnit: { fontSize: "14px", color: "#8aa898", fontWeight: "600", marginBottom: "4px" },
  formulaNote: { fontSize: "11px", color: "#8aa898", fontStyle: "italic", margin: 0 },

  // Event cards
  eventGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: "10px", marginTop: "14px" },
  eventCard: { border: "1px solid #e5e7eb", borderTop: "3px solid", borderRadius: "12px", padding: "12px 10px" },
  eventIcon: { fontSize: "20px", marginBottom: "4px" },
  eventLabel: { fontSize: "10px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" },
  eventCal: { fontSize: "22px", fontWeight: "900", lineHeight: 1 },
  eventCalUnit: { fontSize: "11px", color: "#8aa898", marginBottom: "6px" },
  eventMacros: { display: "flex", flexDirection: "column", gap: "3px" },
  macroChip: { fontSize: "10px", color: "#4a6358", background: "rgba(0,0,0,0.06)", borderRadius: "4px", padding: "2px 5px" },


  badge: { fontSize: "10px", fontWeight: "800", padding: "3px 10px", borderRadius: "99px", letterSpacing: "0.04em" },

  // Voice text
  bothVoices: { display: "flex", flexDirection: "column", gap: "8px" },
  voiceText: { fontSize: "13px", color: "#4a6358", lineHeight: 1.6, margin: 0, background: "#f4f8f5", padding: "12px", borderRadius: "10px" },
  athleteText: { fontSize: "13px", color: "#1b5e42", lineHeight: 1.6, margin: 0, background: "#f0fdf4", padding: "12px", borderRadius: "10px", fontStyle: "italic" },

  // Why box
  whyBox: { background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "8px", padding: "10px 12px" },
  whyLabel: { fontSize: "10px", fontWeight: "800", color: "#2d6a4f", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "4px" },
  whyText: { fontSize: "12px", color: "#15803d", margin: 0, lineHeight: 1.5 },

  // Context note
  contextNote: { fontSize: "12px", color: "#8aa898", background: "#f4f8f5", padding: "8px 12px", borderRadius: "8px", marginTop: "10px", lineHeight: 1.5 },

  // LEA
  leaCard: { background: "#fff7ed", border: "2px solid #f97316" },
  leaHeader: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" },
  leaIconWrap: { fontSize: "28px" },
  leaTitle: { fontSize: "16px", fontWeight: "800", color: "#c2410c", margin: 0 },
  leaPills: { display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" },
  leaMsg: { fontSize: "13px", color: "#7c2d12", lineHeight: 1.6, marginBottom: "10px" },
  leaAction: { background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", padding: "10px 12px", fontSize: "13px", fontWeight: "600", color: "#dc2626" },


  disclaimer: { fontSize: "10px", color: "#8aa898", textAlign: "center", lineHeight: 1.6, padding: "0 8px" },
};
