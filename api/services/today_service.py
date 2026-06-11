from datetime import date, datetime, timedelta


def compute_logged_totals(meal_logs: list) -> dict:
    keys = ("calories", "carbs_g", "protein_g", "fat_g", "iron_mg", "calcium_mg", "water_oz")
    totals = {k: 0.0 for k in keys}
    for m in meal_logs:
        for k in keys:
            totals[k] += m.get(k) or 0.0
    return {k: round(v, 1) for k, v in totals.items()}


def compute_traffic_light(targets: dict, logged: dict) -> dict:
    mapping = [
        ("calories",   "total_calories",   0.30),
        ("carbs_g",    "carbs_g_max",      0.25),
        ("protein_g",  "protein_g_max",    0.20),
        ("water_oz",   "hydration_oz_min", 0.15),
        ("iron_mg",    "iron_mg",          0.05),
        ("calcium_mg", "calcium_mg",       0.05),
    ]
    tl = {}
    fuel_score = 0.0
    for logged_key, target_key, weight in mapping:
        logged_val = logged.get(logged_key) or 0.0
        target_val = targets.get(target_key) or 1.0
        pct = min(150, round(logged_val / target_val * 100))
        gap = round(max(0.0, target_val - logged_val), 1)
        status = "met" if pct >= 80 else "low" if pct >= 50 else "critical"
        tl[logged_key] = {
            "logged": round(logged_val, 1),
            "target": round(target_val, 1),
            "pct_met": pct,
            "gap": gap,
            "status": status,
        }
        fuel_score += min(100, pct) * weight
    tl["daily_fuel_score"] = round(fuel_score)
    return tl


def calc_letter_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 83: return "B+"
    if score >= 75: return "B"
    if score >= 67: return "B-"
    if score >= 57: return "C+"
    if score >= 47: return "C"
    if score >= 37: return "D"
    return "F"


def get_positive_rows(tl: dict, event_type: str, gender: str) -> list:
    checks = [
        ("calories",   "🔥", lambda pct, et: f"{pct}% of daily calories met" if pct < 100 else "Calorie target met today"),
        ("carbs_g",    "⚡", lambda pct, et: f"Carbs on track for {et} day" if et in ("game", "tournament") else "Carbs building nicely"),
        ("protein_g",  "💪", lambda pct, et: "Protein target met" if pct >= 90 else f"Protein at {pct}% — strong"),
        ("calcium_mg", "🦴", lambda pct, et: "Calcium on track" if pct >= 90 else "Bone-building on track"),
        ("water_oz",   "💧", lambda pct, et: "Hydration goal met!" if pct >= 100 else f"Hydration at {pct}%"),
    ]
    if gender.lower() not in ("girl", "female") or tl.get("iron_mg", {}).get("pct_met", 0) >= 90:
        checks.append(("iron_mg", "🩸", lambda pct, et: "Iron target met — great!"))
    positives = []
    for key, icon, label_fn in checks:
        pct = tl.get(key, {}).get("pct_met", 0)
        if pct >= 80:
            positives.append({"icon": icon, "text": label_fn(pct, event_type), "pct": f"{pct}%"})
    return positives[:2]


def get_gap_rows(tl: dict, gender: str, event_type: str) -> list:
    gaps = []
    iron_pct = tl.get("iron_mg", {}).get("pct_met", 100)
    if iron_pct < 75 and gender.lower() in ("girl", "female"):
        gaps.append({
            "key": "iron_mg", "icon": "🩸",
            "name": "Iron — critical gap" if iron_pct < 40 else "Iron — below target",
            "detail": "Add lean beef or lentils to recovery lunch. Pair with vitamin C. 52% of female athletes are deficient. — Everett MD 2025",
            "pct": iron_pct, "target": f"of {round(tl['iron_mg']['target'])}mg",
        })
    calcium_pct = tl.get("calcium_mg", {}).get("pct_met", 100)
    if calcium_pct < 75:
        gaps.append({
            "key": "calcium_mg", "icon": "🦴",
            "name": "Calcium — below target",
            "detail": "Add 2 glasses of milk today. Peak bone mass window — ages 9–17 only. — AAP",
            "pct": calcium_pct, "target": f"of {round(tl['calcium_mg']['target'])}mg",
        })
    cal_pct = tl.get("calories", {}).get("pct_met", 100)
    if cal_pct < 60:
        gaps.append({
            "key": "calories", "icon": "🔥",
            "name": "Calories below target",
            "detail": f"{round(tl['calories']['gap'])} kcal remaining · Recovery lunch + bedtime snack will close this gap",
            "pct": cal_pct, "target": f"of {round(tl['calories']['target'])} kcal",
        })
    carbs_pct = tl.get("carbs_g", {}).get("pct_met", 100)
    if carbs_pct < 60 and event_type in ("game", "practice", "tournament", "training"):
        gaps.append({
            "key": "carbs_g", "icon": "⚡",
            "name": f"Carbs low for {event_type} day",
            "detail": f"Need {round(tl['carbs_g']['gap'])}g more · Add rice, pasta, or fruit to next meal",
            "pct": carbs_pct, "target": f"of {round(tl['carbs_g']['target'])}g",
        })
    water_pct = tl.get("water_oz", {}).get("pct_met", 100)
    if water_pct < 50:
        oz_gap = round(tl["water_oz"]["gap"])
        gaps.append({
            "key": "water_oz", "icon": "💧",
            "name": "Hydration below target",
            "detail": f"{oz_gap}oz remaining · {max(1, round(oz_gap / 8))} more cups needed",
            "pct": water_pct, "target": f"of {round(tl['water_oz']['target'])}oz",
        })
    return gaps[:3]


def get_athlete_streak(athlete_id: int, conn) -> dict:
    today = date.today()
    streak = 0
    check_date = today
    while streak <= 365:
        cnt = conn.execute(
            "SELECT COUNT(*) as cnt FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ?",
            (athlete_id, check_date.isoformat()),
        ).fetchone()["cnt"]
        if cnt > 0:
            streak += 1
            check_date -= timedelta(days=1)
        elif check_date == today:
            check_date -= timedelta(days=1)
            continue
        else:
            break

    rows = conn.execute(
        "SELECT DISTINCT DATE(logged_at) as d FROM meal_logs WHERE athlete_id = ? ORDER BY d ASC",
        (athlete_id,),
    ).fetchall()
    dates = [r["d"] for r in rows]
    best, best_end, cur = 0, None, 0
    for i, d in enumerate(dates):
        if i == 0:
            cur = 1
        else:
            prev_dt = datetime.strptime(dates[i - 1], "%Y-%m-%d").date()
            curr_dt = datetime.strptime(d, "%Y-%m-%d").date()
            cur = cur + 1 if (curr_dt - prev_dt).days == 1 else 1
        if cur > best:
            best = cur
            best_end = d

    week_start = today - timedelta(days=today.weekday())
    week_logged = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        cnt = conn.execute(
            "SELECT COUNT(*) as cnt FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ?",
            (athlete_id, d.isoformat()),
        ).fetchone()["cnt"]
        week_logged.append(cnt > 0)

    return {
        "current_streak": streak,
        "best_streak": best,
        "best_streak_date": best_end,
        "week_logged": week_logged,
    }


def get_urgent_action(events: list, tl: dict, meal_logs: list) -> dict:
    now = datetime.now()

    def mins_until(time_str):
        try:
            h, m = map(int, time_str.split(":"))
            t = now.replace(hour=h, minute=m, second=0, microsecond=0)
            return round((t - now).total_seconds() / 60)
        except Exception:
            return None

    def has_log_type(keywords):
        for m in meal_logs:
            desc = (m.get("description") or "").lower()
            if any(kw.lower() in desc for kw in keywords):
                return True
        return False

    for ev in events:
        start = ev.get("start_time")
        dur = ev.get("duration_hours") or 1.5
        if not start:
            continue
        mins_to = mins_until(start)
        if mins_to is None:
            continue

        if 10 <= mins_to <= 90 and not has_log_type(["snack", "banana", "pre-game snack", "top-up"]):
            return {
                "icon": "🍌", "title": "Eat your pre-game snack now",
                "sub": "Banana + PB or toast + honey · fast carbs",
                "window": f"Window closes in {max(1, mins_to - 10)} min",
                "window_duration_secs": max(1, mins_to - 10) * 60,
                "action": "log_meal", "meal_type": "snack",
            }

        mins_since_end = -(mins_to + round(dur * 60))
        if 0 <= mins_since_end <= 30 and not has_log_type(["recovery", "chocolate milk", "post-game"]):
            remaining = 30 - mins_since_end
            return {
                "icon": "🏆", "title": "Recovery window open — act now",
                "sub": "Chocolate milk + banana · 3:1 carb:protein",
                "window": f"{remaining} min remaining",
                "window_duration_secs": remaining * 60,
                "action": "log_meal", "meal_type": "recovery",
            }

        if 150 <= mins_to <= 240 and not has_log_type(["breakfast", "oatmeal", "eggs", "pre-game meal"]):
            return {
                "icon": "🍳", "title": "Pre-game breakfast window is open",
                "sub": f"Eat now · {mins_to // 60}hr {mins_to % 60}min to kickoff",
                "window": "Optimal window: 2.5–4hrs before event",
                "window_duration_secs": (mins_to - 150) * 60,
                "action": "log_meal", "meal_type": "breakfast",
            }

    iron_pct = tl.get("iron_mg", {}).get("pct_met", 100)
    if iron_pct < 35:
        return {
            "icon": "🩸", "title": "Iron is critically low today",
            "sub": f"Need {round(tl['iron_mg']['gap'])}mg more · Add lentils or beef",
            "window": "52% of female athletes are iron deficient · Everett MD 2025",
            "window_duration_secs": None, "action": "log_meal", "meal_type": "lunch",
        }

    water_pct = tl.get("water_oz", {}).get("pct_met", 100)
    if water_pct < 40:
        cups = max(1, round(tl["water_oz"]["gap"] / 8))
        return {
            "icon": "💧", "title": f"Drink {cups} more cups today",
            "sub": "Tap your hydration tracker below as you drink",
            "window": "Dehydration by 2% measurably slows reaction time",
            "window_duration_secs": None, "action": "scroll_to_hydration",
        }

    score = tl.get("daily_fuel_score", 0)
    if score >= 80:
        return {
            "icon": "🏆", "title": "You're fueling like a pro today",
            "sub": f"Fuel score {score}/100 · Keep it going",
            "window": "Check your meal plan for tonight's recovery snack",
            "window_duration_secs": None, "action": "view_plan",
        }
    return {
        "icon": "📋", "title": "Check today's meal plan",
        "sub": f"Fuel score {score}/100 · Log your next meal",
        "window": "Every logged meal improves your fuel score",
        "window_duration_secs": None, "action": "view_plan",
    }


def get_mission_items(tl: dict, events: list, gender: str, event_type: str) -> list:
    """Returns prioritized mission items for today's dashboard. Placeholder for future implementation."""
    return []


def calculate_performance_forecast(traffic_light: dict) -> dict:
    """Derives 4 performance metrics from nutrition traffic light. Pure math."""
    def pct(key): return min(traffic_light.get(key, {}).get("pct_met") or 0, 100)

    # calcium excluded — no direct acute per-match performance effect
    return {
        "sprint_capacity":   round(pct("carbs_g")   * 0.40 + pct("iron_mg")   * 0.35 + pct("protein_g") * 0.25),
        "energy_reserves":   round(pct("calories")  * 0.60 + pct("carbs_g")   * 0.40),
        "second_half_power": round(pct("iron_mg")   * 0.50 + pct("carbs_g")   * 0.30 + pct("water_oz")  * 0.20),
        "mental_focus":      round(pct("calories")  * 0.40 + pct("water_oz")  * 0.35 + pct("protein_g") * 0.25),
    }
