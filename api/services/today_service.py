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


def _fmt_time(time_str: str, offset_hours: float = 0) -> str:
    """'14:30' + 0.5 → '3:00 PM'"""
    if not time_str:
        return ""
    try:
        h, m = map(int, time_str.split(":"))
        base = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        dt = base + timedelta(hours=offset_hours)
        hour = dt.hour % 12 or 12
        period = "AM" if dt.hour < 12 else "PM"
        minute_str = f":{dt.minute:02d}" if dt.minute else ""
        return f"{hour}{minute_str} {period}"
    except Exception:
        return ""


def _has_log_type(meal_logs: list, keywords: list) -> bool:
    for m in meal_logs:
        desc = (m.get("description") or "").lower()
        if any(kw.lower() in desc for kw in keywords):
            return True
    return False


def get_mission_items(
    event_type: str,
    events: list,
    traffic_light: dict,
    meal_logs: list,
    targets: dict,
    water_cups: int,
    gender: str,
) -> list:
    """
    Returns exactly 5 mission items for today.
    Each item: {label, sub, time, state, tag, item_type}
    state: "done" | "urgent" | "critical" | "pending"
    tag:   "DONE" | "NOW" | "FIX THIS" | "UPCOMING"
    """
    now = datetime.now()
    is_female = gender.lower() in ("girl", "female")
    iron_pct = traffic_light.get("iron_mg", {}).get("pct_met") or 0
    iron_gap = round(traffic_light.get("iron_mg", {}).get("gap", 0), 1)
    water_pct = traffic_light.get("water_oz", {}).get("pct_met") or 0
    target_cups = max(1, round((targets.get("hydration_oz_min") or 64) / 8))
    cups_remaining = max(0, target_cups - (water_cups or 0))

    event = events[0] if events else None
    start = event.get("start_time") if event else None
    dur = (event.get("duration_hours") or 1.5) if event else 1.5

    def mins_to_start():
        if not start:
            return None
        try:
            h, m = map(int, start.split(":"))
            t = now.replace(hour=h, minute=m, second=0, microsecond=0)
            return round((t - now).total_seconds() / 60)
        except Exception:
            return None

    def _item(item_type, label, sub, time, state):
        tag = {"done": "DONE", "urgent": "NOW", "critical": "FIX THIS", "pending": "UPCOMING"}[state]
        return {"label": label, "sub": sub, "time": time, "state": state, "tag": tag, "item_type": item_type}

    def iron_item():
        if is_female and iron_pct < 50:
            return _item("iron_lunch", "Close the iron gap at lunch",
                         f"Add lean beef or lentils · <em>{iron_gap}mg needed</em>",
                         "1:00 PM", "critical")
        return _item("iron_lunch", "Iron-rich lunch today",
                     "Lentils, lean beef, or fortified cereal", "1:00 PM", "pending")

    def hydration_item():
        cups_done = water_cups or 0
        state = "urgent" if water_pct < 40 else "pending"
        return _item("hydration",
                     f"Drink {cups_remaining} more cup{'s' if cups_remaining != 1 else ''} of water",
                     f"<em>{cups_done}</em> of {target_cups} cups done · {cups_done * 8}oz logged",
                     "All day", state)

    norm = (event_type or "rest").lower()

    # ── GAME DAY ──────────────────────────────────────────────────────────────
    if norm in ("game", "tournament"):
        mins = mins_to_start()
        breakfast_done = _has_log_type(meal_logs, ["breakfast", "oatmeal", "eggs", "pancake", "toast"])
        snack_done = _has_log_type(meal_logs, ["snack", "banana", "pre-game snack"])

        item1_state = "done" if breakfast_done or (mins is not None and mins < 150) else "pending"
        item2_state = "done" if snack_done else ("urgent" if mins is not None and 10 <= mins <= 90 else "pending")
        recovery_time = _fmt_time(start, dur + 0.5) if start else "After game"
        snack_time = _fmt_time(start, -0.75) if start else "45 min before"

        return [
            _item("pregame_breakfast", "Pre-game breakfast logged",
                  "High-carb meal 2.5–4 hrs before kickoff",
                  _fmt_time(start, -3) if start else "Morning", item1_state),
            _item("pregame_snack", "Eat your pre-game snack NOW" if item2_state == "urgent" else "Pre-game snack",
                  f"Banana + PB · Window closes in <em>{max(1, (mins or 45) - 10)} min</em>" if item2_state == "urgent" else "Banana + PB or rice cakes",
                  snack_time, item2_state),
            iron_item(),
            _item("recovery", "Hit recovery window after the game",
                  "Chocolate milk + banana · <em>30-min window</em>",
                  recovery_time, "pending"),
            hydration_item(),
        ]

    # ── PRACTICE / TRAINING / STRENGTH DAY ───────────────────────────────────
    if norm in ("practice", "training", "strength"):
        mins = mins_to_start()
        recovery_time = _fmt_time(start, dur + 0.5) if start else "After training"
        snack_time = _fmt_time(start, -0.75) if start else "45 min before"
        pre_time = _fmt_time(start, -2.0) if start else "2 hrs before"

        if norm == "strength":
            return [
                _item("pre_strength_meal", "Pre-strength meal 2hrs before training",
                      "Rice + chicken or oatmeal + eggs · complex carbs + protein",
                      pre_time, "pending"),
                _item("pre_practice_snack", "Fast carb snack 30 min before",
                      "Banana or rice cakes · <em>fast glucose</em>",
                      _fmt_time(start, -0.5) if start else "30 min before", "pending"),
                _item("protein_recovery", "CRITICAL: Protein recovery within 30 min",
                      "Chocolate milk or Greek yogurt + banana · <em>30-min window</em>",
                      recovery_time, "critical"),
                _item("casein_snack", "Bedtime casein snack tonight",
                      "Cottage cheese or Greek yogurt · <em>overnight muscle repair</em>",
                      "9:30 PM", "pending"),
                hydration_item(),
            ]

        return [
            _item("pre_practice_lunch", "Eat your pre-practice lunch by noon",
                  "High-carb lunch · rice, pasta, or sweet potato",
                  "12:00 PM", "pending"),
            _item("pre_practice_snack",
                  f"Pre-practice snack {round((mins or 45))} min before training" if mins and mins > 0 else "Pre-practice snack",
                  "Banana + PB or toast + honey · <em>fast carbs</em>",
                  snack_time, "pending"),
            _item("protein_recovery", "Protein recovery within 30 min of whistle",
                  "Chocolate milk + banana · <em>30-min window</em>",
                  recovery_time, "pending"),
            iron_item(),
            hydration_item(),
        ]

    # ── PRE-GAME DAY ──────────────────────────────────────────────────────────
    if norm == "pregame_day":
        return [
            _item("hc_breakfast", "High-carb breakfast this morning",
                  "Oatmeal + banana + OJ · carb loading starts now",
                  "8:00 AM", "pending"),
            _item("pasta_lunch", "Big pasta or rice lunch — carb load begins",
                  "Pasta + tomato sauce + chicken · <em>high carbs, low fat</em>",
                  "12:00 PM", "pending"),
            _item("afternoon_snack", "Afternoon snack — keep carbs high all day",
                  "Toast + honey or rice cakes · no heavy protein",
                  "3:00 PM", "pending"),
            _item("pregame_dinner", "MOST IMPORTANT: Pre-game dinner tonight",
                  "Pasta + lean protein · <em>biggest carb meal of the week</em>",
                  "6:30 PM", "critical"),
            _item("low_fiber", "Limit fiber and fat today",
                  "Easy digestion for tomorrow · no salads or heavy sauces",
                  "All day", "pending"),
        ]

    # ── REST / RECOVERY DAY (default) ─────────────────────────────────────────
    return [
        _item("active_recovery", "Active recovery nutrition — don't undereat",
              "Rest days need 80%+ of normal calories to repair muscle",
              "All day", "pending"),
        iron_item(),
        _item("calcium", "2 glasses of milk for calcium restoration",
              "Ages 9–17 is the bone-building window · <em>+600mg calcium</em>",
              "With meals",
              "critical" if (traffic_light.get("calcium_mg", {}).get("pct_met") or 0) < 50 else "pending"),
        _item("anti_inflammatory", "Anti-inflammatory dinner tonight",
              "Salmon, leafy greens, or olive oil · reduces muscle soreness",
              "7:00 PM", "pending"),
        hydration_item(),
    ]


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
