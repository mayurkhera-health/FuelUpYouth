from datetime import date, timedelta
from api.services.today_service import compute_logged_totals, compute_traffic_light

NUTRIENT_LABELS: dict = {
    "iron_mg":    ("🩸", "Iron",          "mg"),
    "calcium_mg": ("🦴", "Calcium",       "mg"),
    "carbs_g":    ("⚡",  "Carbohydrates", "g"),
    "protein_g":  ("💪", "Protein",       "g"),
    "water_oz":   ("💧", "Hydration",     "oz"),
    "calories":   ("🔥", "Calories",      "kcal"),
}

FIX_FOODS: dict = {
    "iron_mg": [
        {"food": "🥩 Lean beef or ground turkey at lunch",                         "gain": "+3.5mg"},
        {"food": "🫘 Lentil soup or chickpeas",                                    "gain": "+4.2mg"},
        {"food": "🥬 Spinach + bell pepper (vitamin C doubles absorption)",         "gain": "+2.1mg"},
    ],
    "calcium_mg": [
        {"food": "🥛 2 glasses of milk daily",                                     "gain": "+600mg"},
        {"food": "🧀 Greek yogurt at breakfast",                                   "gain": "+250mg"},
        {"food": "🧀 Cheese + crackers as a snack",                                "gain": "+200mg"},
    ],
    "water_oz": [
        {"food": "💧 1 glass when waking up",                                      "gain": "+8oz"},
        {"food": "💧 Water bottle at every meal",                                  "gain": "+24oz"},
        {"food": "🍋 Sparkling water as afternoon snack",                          "gain": "+12oz"},
    ],
    "carbs_g": [
        {"food": "🍝 Pasta or rice at dinner",                                     "gain": "+80g"},
        {"food": "🍞 Toast + honey before practice",                               "gain": "+45g"},
        {"food": "🍌 Banana + peanut butter before training",                      "gain": "+30g"},
    ],
    "protein_g": [
        {"food": "🥚 2 eggs + Greek yogurt at breakfast",                          "gain": "+25g"},
        {"food": "🐟 Tuna or salmon at lunch",                                     "gain": "+22g"},
        {"food": "🍗 Chicken breast at dinner",                                    "gain": "+30g"},
    ],
    "calories": [
        {"food": "🥜 Peanut butter on toast (extra snack)",                        "gain": "+200kcal"},
        {"food": "🍌 Banana + granola bar",                                        "gain": "+150kcal"},
        {"food": "🥛 Whole milk + almonds",                                        "gain": "+180kcal"},
    ],
}


def score_to_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 85: return "A−"
    if score >= 80: return "B+"
    if score >= 75: return "B"
    if score >= 70: return "B−"
    if score >= 65: return "C+"
    if score >= 60: return "C"
    if score >= 55: return "C−"
    if score >= 50: return "D+"
    return "D"


def _compute_streak(athlete_id: int, conn) -> int:
    today = date.today()
    streak = 0
    d = today
    for _ in range(365):
        row = conn.execute(
            "SELECT COUNT(*) FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ?",
            (athlete_id, d.isoformat()),
        ).fetchone()
        if row and row[0] > 0:
            streak += 1
            d -= timedelta(days=1)
        else:
            break
    return streak


def _rank_gaps(totals: dict, targets: dict, days: int, gender: str) -> list:
    if days == 0:
        return []
    gaps = []
    for nutrient, (emoji, label, unit) in NUTRIENT_LABELS.items():
        target_total = targets.get(nutrient, 0)
        if not target_total:
            continue
        logged_total = totals.get(nutrient, 0)
        avg_amount   = round(logged_total / days, 1)
        avg_target   = round(target_total  / days, 1)
        avg_pct      = round(min(100, (logged_total / target_total) * 100))
        gaps.append({
            "nutrient":   nutrient,
            "label":      label,
            "emoji":      emoji,
            "unit":       unit,
            "avg_amount": avg_amount,
            "target":     avg_target,
            "avg_pct":    avg_pct,
        })

    gaps.sort(key=lambda g: g["avg_pct"])

    if gender in ("girl", "female"):
        iron = next((g for g in gaps if g["nutrient"] == "iron_mg"), None)
        if iron and iron["avg_pct"] < 75:
            gaps.remove(iron)
            gaps.insert(0, iron)

    return gaps


def build_weekly_report(athlete_id: int, week_start: str, conn) -> dict:
    from api.services.claude_ai import prompt3_weekly_report_v2

    row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
    if not row:
        raise ValueError(f"Athlete {athlete_id} not found")
    athlete = dict(row)

    week_start_date = date.fromisoformat(week_start)
    week_end_date   = week_start_date + timedelta(days=6)

    daily_scores: list        = []
    week_fuel_scores: list    = []
    nutrient_totals: dict     = {}
    nutrient_targets: dict    = {}
    days_with_data            = 0

    for i in range(7):
        day_str  = (week_start_date + timedelta(days=i)).isoformat()
        day_date = date.fromisoformat(day_str)
        abbr     = day_date.strftime("%a")[:2]

        targets_row = conn.execute(
            "SELECT * FROM daily_targets WHERE athlete_id = ? AND target_date = ?",
            (athlete_id, day_str),
        ).fetchone()

        event_row = conn.execute(
            "SELECT event_type, event_name FROM events WHERE athlete_id = ? AND event_date = ?",
            (athlete_id, day_str),
        ).fetchone()

        meal_rows = conn.execute(
            "SELECT * FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ?",
            (athlete_id, day_str),
        ).fetchall()

        fuel_score = None
        if targets_row and meal_rows:
            logged = compute_logged_totals([dict(m) for m in meal_rows])
            tl     = compute_traffic_light(dict(targets_row), logged)
            fuel_score = tl.get("daily_fuel_score")
            if fuel_score is not None:
                week_fuel_scores.append(fuel_score)
                days_with_data += 1

                for nutrient in NUTRIENT_LABELS:
                    nutrient_totals[nutrient] = (
                        nutrient_totals.get(nutrient, 0) + (logged.get(nutrient) or 0)
                    )

                t = dict(targets_row)
                target_map = {
                    "calories":   t.get("total_calories", 0),
                    "carbs_g":    t.get("carbs_g_max", 0),
                    "protein_g":  t.get("protein_g_max", 0),
                    "iron_mg":    t.get("iron_mg", 0),
                    "calcium_mg": t.get("calcium_mg", 0),
                    "water_oz":   t.get("hydration_oz_min", 0),
                }
                for nutrient, val in target_map.items():
                    nutrient_targets[nutrient] = (
                        nutrient_targets.get(nutrient, 0) + (val or 0)
                    )

        daily_scores.append({
            "date":       day_str,
            "abbr":       abbr,
            "fuel_score": fuel_score,
            "event_type": event_row["event_type"] if event_row else None,
            "event_name": event_row["event_name"] if event_row else None,
        })

    avg_score    = round(sum(week_fuel_scores) / len(week_fuel_scores)) if week_fuel_scores else 0
    letter_grade = score_to_grade(avg_score)
    streak       = _compute_streak(athlete_id, conn)

    first_event = conn.execute(
        "SELECT MIN(event_date) FROM events WHERE athlete_id = ?", (athlete_id,)
    ).fetchone()
    season_start = (first_event[0] if first_event and first_event[0] else week_start)
    season_week  = max(
        1, ((week_start_date - date.fromisoformat(season_start)).days // 7) + 1
    )

    ranked_gaps  = _rank_gaps(nutrient_totals, nutrient_targets, days_with_data, athlete["gender"])
    critical_gap = ranked_gaps[0] if ranked_gaps else None
    fix_foods    = FIX_FOODS.get(critical_gap["nutrient"], []) if critical_gap else []

    next_week_start = week_end_date + timedelta(days=1)
    next_week_end   = next_week_start + timedelta(days=6)
    next_events = [
        dict(r) for r in conn.execute(
            "SELECT event_type, event_name, event_date FROM events "
            "WHERE athlete_id = ? AND event_date BETWEEN ? AND ? ORDER BY event_date",
            (athlete_id, next_week_start.isoformat(), next_week_end.isoformat()),
        ).fetchall()
    ]

    narrative = prompt3_weekly_report_v2({
        "athlete":      athlete,
        "week_start":   week_start,
        "avg_score":    avg_score,
        "letter_grade": letter_grade,
        "days_logged":  days_with_data,
        "critical_gap": critical_gap,
        "next_events":  next_events,
        "streak":       streak,
    })

    tips = narrative.get("next_week_tips") or []
    padded_tips = tips + ["Focus on balanced meals and hydration."] * max(0, len(next_events) - len(tips))

    return {
        "week_start":  week_start,
        "week_end":    week_end_date.isoformat(),
        "season_week": season_week,
        "athlete": {
            "id":         athlete["id"],
            "first_name": athlete["first_name"],
            "gender":     athlete["gender"],
        },
        "grade": {
            "letter":      letter_grade,
            "score":       avg_score,
            "days_logged": days_with_data,
            "streak":      streak,
            "headline":    narrative.get("grade_headline", f"Great week, {athlete['first_name']}!"),
            "summary":     narrative.get("grade_summary", "Keep building those habits."),
        },
        "what_went_well": narrative.get("what_went_well") or [
            {"text": f"Logged {days_with_data} days this week", "stat": f"{days_with_data}/7"},
        ],
        "critical_gap": {
            "nutrient":       critical_gap["nutrient"]  if critical_gap else None,
            "label":          critical_gap["label"]     if critical_gap else None,
            "emoji":          critical_gap["emoji"]     if critical_gap else None,
            "avg_amount":     critical_gap["avg_amount"] if critical_gap else 0,
            "target":         critical_gap["target"]    if critical_gap else 0,
            "unit":           critical_gap["unit"]      if critical_gap else "",
            "weekly_avg_pct": critical_gap["avg_pct"]   if critical_gap else 0,
            "why":            narrative.get("critical_gap_why", ""),
            "fix_foods":      fix_foods,
        },
        "daily_scores": daily_scores,
        "next_week": [
            {
                "event_type": e["event_type"],
                "event_name": e["event_name"],
                "event_date": e["event_date"],
                "prep_tip":   tip,
            }
            for e, tip in zip(next_events, padded_tips)
        ],
        "summary": narrative.get("summary_paragraphs") or [],
    }
