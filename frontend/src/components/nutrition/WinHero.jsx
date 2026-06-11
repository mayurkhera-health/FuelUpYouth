const NUTRIENT_LABELS = {
  iron_mg: "🩸 Iron",
  calcium_mg: "🦴 Calcium",
  carbs_g: "⚡ Carbs",
  protein_g: "💪 Protein",
  calories: "🔥 Calories",
  water_oz: "💧 Hydration",
};

const FOCUS_TIPS = {
  iron_mg: "Lentils or lean beef at lunch will move this fast.",
  calcium_mg: "2 glasses of milk or yogurt closes most of this gap.",
  water_oz: "A water bottle at school + one at practice does it.",
  carbs_g: "Rice, pasta, or oats at every main meal.",
  calories: "Don't skip snacks — add a recovery meal after training.",
  protein_g: "Add Greek yogurt or eggs to breakfast.",
};

const UNIT = {
  iron_mg: "mg",
  calcium_mg: "mg",
  carbs_g: "g",
  protein_g: "g",
  calories: " kcal",
  water_oz: "oz",
};

const COLOR_BOX = {
  gold: "rgba(217,119,6,.12)",
  green: "rgba(45,106,79,.12)",
  blue: "rgba(37,99,235,.10)",
  purple: "rgba(126,106,181,.12)",
  amber: "rgba(217,119,6,.12)",
};

export default function WinHero({ athlete, weekSummary }) {
  const {
    week_fuel_score: score = 0,
    prev_week_score: prevScore = null,
    streak = {},
    wins = [],
    ranked_gaps: gaps = [],
    days_logged: daysLogged = 0,
  } = weekSummary;

  if (daysLogged === 0) {
    return (
      <div style={s.card}>
        <div style={s.banner}>
          <div style={s.eyebrow}>🏆 This week's performance</div>
          <div style={s.headline}>{athlete.first_name} is on{"\n"}the way.</div>
          <div style={s.sub}>Log the first meal of the week to unlock your weekly fuel report.</div>
        </div>
      </div>
    );
  }

  const delta = prevScore !== null ? score - prevScore : null;
  const deltaStr =
    delta === null ? "—" : delta >= 0 ? `↑${delta}` : `↓${Math.abs(delta)}`;
  const focusGaps = gaps.slice(0, 2);

  return (
    <div style={s.card}>
      <div style={s.banner}>
        <div style={s.eyebrow}>🏆 This week's performance</div>
        <div style={s.headline}>{athlete.first_name} is building{"\n"}great habits.</div>
        <div style={s.sub}>
          {streak.current_streak >= 2
            ? `${streak.current_streak} days logged in a row — discipline like this is what separates good athletes from great ones.`
            : "Every meal logged helps fuel better performance. Keep building the habit."}
        </div>
        <div style={s.statsRow}>
          <div style={s.statTile}>
            <div style={s.statVal}>{score}</div>
            <div style={s.statLabel}>Week fuel score</div>
          </div>
          <div style={s.statTile}>
            <div style={s.statVal}>{streak.current_streak ?? 0}🔥</div>
            <div style={s.statLabel}>Day streak</div>
          </div>
          <div style={s.statTile}>
            <div style={s.statVal}>{deltaStr}</div>
            <div style={s.statLabel}>vs last week</div>
          </div>
        </div>
      </div>

      <div style={s.winsList}>
        <div style={s.sectionLabel}>What {athlete.first_name} crushed this week</div>
        {wins.map((win, i) => (
          <div key={i} style={s.winItem}>
            <div
              style={{
                ...s.winIconBox,
                background: COLOR_BOX[win.color] ?? COLOR_BOX.green,
              }}
            >
              {win.icon}
            </div>
            <div>
              <div style={s.winLabel}>{win.label}</div>
              <div style={s.winDetail}>{win.detail}</div>
            </div>
          </div>
        ))}
      </div>

      {focusGaps.length > 0 && (
        <div style={s.focusStrip}>
          <div style={s.sectionLabel}>
            {focusGaps.length === 1
              ? "One area to build on"
              : "Two areas to build on this week"}
          </div>
          <div style={s.focusRow}>
            {focusGaps.map((gap) => {
              const pct = gap.avg_pct;
              const color = "#b45309";
              const label = NUTRIENT_LABELS[gap.nutrient] ?? gap.nutrient;
              const unit = UNIT[gap.nutrient] ?? "";
              return (
                <div key={gap.nutrient} style={s.focusTile}>
                  <div style={s.ftNutrient}>{label}</div>
                  <div style={{ ...s.ftVal, color }}>{pct}%</div>
                  <div style={s.ftTarget}>
                    avg · target {Math.round(gap.target)}{unit}
                  </div>
                  <div style={s.ftBar}>
                    <div
                      style={{
                        ...s.ftBarFill,
                        width: `${Math.min(100, pct)}%`,
                        background: color,
                      }}
                    />
                  </div>
                  <div style={s.ftTip}>
                    {FOCUS_TIPS[gap.nutrient] ?? "Focus on this nutrient this week."}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  card: {
    background: "#fff",
    borderRadius: "14px",
    border: "1px solid #dce8e0",
    overflow: "hidden",
  },
  banner: {
    background: "linear-gradient(145deg, #1b3a2a 0%, #2d6a4f 60%, #40916c 100%)",
    padding: "18px 16px 16px",
  },
  eyebrow: {
    fontSize: "12px",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: ".12em",
    color: "#b7e4c7",
    marginBottom: "6px",
  },
  headline: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "26px",
    fontWeight: "900",
    color: "#fff",
    letterSpacing: "-.02em",
    lineHeight: "1.2",
    marginBottom: "6px",
    whiteSpace: "pre-line",
  },
  sub: {
    fontSize: "13px",
    color: "rgba(255,255,255,.7)",
    lineHeight: "1.5",
    marginBottom: "14px",
  },
  statsRow: { display: "flex", gap: "8px" },
  statTile: {
    flex: 1,
    background: "rgba(255,255,255,.12)",
    border: "1px solid rgba(255,255,255,.15)",
    borderRadius: "10px",
    padding: "10px",
    textAlign: "center",
  },
  statVal: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "22px",
    fontWeight: "800",
    color: "#fff",
    lineHeight: "1",
    marginBottom: "3px",
  },
  statLabel: {
    fontSize: "10px",
    color: "rgba(255,255,255,.65)",
    textTransform: "uppercase",
    letterSpacing: ".06em",
  },
  winsList: { padding: "14px 14px 6px" },
  sectionLabel: {
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: ".1em",
    color: "#8aa898",
    fontWeight: "600",
    marginBottom: "10px",
  },
  winItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    marginBottom: "10px",
  },
  winIconBox: {
    width: "34px",
    height: "34px",
    borderRadius: "9px",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "17px",
  },
  winLabel: {
    fontSize: "14px",
    fontWeight: "700",
    color: "#1b3a2a",
    lineHeight: "1.3",
  },
  winDetail: { fontSize: "12px", color: "#4a6358", marginTop: "1px" },
  focusStrip: {
    borderTop: "1px solid #dce8e0",
    padding: "12px 14px 14px",
    background: "#fafcfb",
  },
  focusRow: { display: "flex", gap: "8px" },
  focusTile: {
    flex: 1,
    background: "#fff",
    border: "1px solid #dce8e0",
    borderRadius: "10px",
    padding: "10px",
  },
  ftNutrient: { fontSize: "13px", color: "#4a6358", fontWeight: "500", marginBottom: "3px" },
  ftVal: {
    fontFamily: "'Nunito', sans-serif",
    fontSize: "18px",
    fontWeight: "800",
    lineHeight: "1.1",
    marginBottom: "1px",
  },
  ftTarget: { fontSize: "10px", color: "#8aa898" },
  ftBar: {
    height: "2px",
    background: "#dce8e0",
    borderRadius: "2px",
    marginTop: "6px",
    marginBottom: "5px",
    overflow: "hidden",
  },
  ftBarFill: { height: "100%", borderRadius: "2px" },
  ftTip: { fontSize: "11px", color: "#4a6358", fontStyle: "italic", lineHeight: "1.4" },
};
