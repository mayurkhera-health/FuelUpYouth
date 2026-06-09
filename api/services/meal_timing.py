from datetime import datetime, timedelta


def _offset(event_date: str, start_time: str, hours: float) -> str:
    if not start_time:
        return event_date
    try:
        dt = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
        return (dt + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return event_date


def get_meal_timing_protocol(event_type: str, event_date: str, start_time: str = None) -> dict:
    norm = event_type.lower()
    if "tournament" in norm:
        steps = _tournament(event_date, start_time)
    elif "game" in norm:
        steps = _game_day(event_date, start_time)
    elif "strength" in norm or "conditioning" in norm:
        steps = _strength(event_date, start_time)
    elif "practice" in norm or "training" in norm or "agility" in norm:
        steps = _practice(event_date, start_time)
    elif "pre-game" in norm:
        steps = _pre_game_day(event_date)
    elif "recovery" in norm or "yoga" in norm:
        steps = _recovery(event_date)
    else:
        steps = _rest_day(event_date)

    return {"event_type": event_type, "event_date": event_date, "protocol": steps}


def _game_day(event_date: str, start_time: str) -> list:
    return [
        {"timing": "Night before (7pm)", "when": f"{event_date} (night before 19:00)", "what": "High carb dinner — pasta/rice + protein + milk", "why": "Glycogen loading begins 24-48hrs before kickoff (Everett MD 2025)", "recipe": "Power Pasta Bowl (R001)", "recipient": "parent", "critical": True},
        {"timing": "3hrs before kickoff", "when": _offset(event_date, start_time, -3), "what": "Pre-game breakfast — carbs + protein + OJ", "why": "3hr fuel window opens — no GI distress risk", "recipe": "Tournament Morning Plate (R023)", "recipient": "both"},
        {"timing": "45min before kickoff", "when": _offset(event_date, start_time, -0.75), "what": "Pre-game snack — banana + PB or toast + honey", "why": "Fast glucose for warm-up energy", "recipe": "Banana + PB (R006) or Toast + Honey (R007)", "recipient": "teen"},
        {"timing": "Halftime", "when": _offset(event_date, start_time, 0.75), "what": "Orange slices + 16oz water OR banana + natural sports drink", "why": "Fast glucose for second half + rehydration", "recipe": "Orange Slices (R010) or Banana + Sports Drink (R011)", "recipient": "teen"},
        {"timing": "Within 30min after final whistle", "when": _offset(event_date, start_time, 2.0), "what": "Recovery snack — chocolate milk + banana", "why": "30min window is non-negotiable for glycogen + protein synthesis", "recipe": "Choc Milk Recovery (R013)", "recipient": "both", "critical": True},
        {"timing": "1-2hrs after game", "when": _offset(event_date, start_time, 3.0), "what": "Recovery meal — protein + carbs + veg + milk", "why": "Continue glycogen restoration for 4-6hrs post game", "recipe": "Post-Practice Rebuild Plate (R019)", "recipient": "both"},
        {"timing": "Bedtime", "when": f"{event_date} 21:00", "what": "Casein snack — cottage cheese or Greek yogurt", "why": "Overnight muscle repair — critical on game days", "recipe": "Cottage Cheese + Pineapple (R017)", "recipient": "teen"},
    ]


def _strength(event_date: str, start_time: str) -> list:
    return [
        {"timing": "2hrs before", "when": _offset(event_date, start_time, -2), "what": "Carb + protein meal — rice/pasta + chicken", "why": "Fuel glycogen + prime amino acid availability", "recipe": "Strength Day Protein Plate (R022)", "recipient": "both"},
        {"timing": "30min before", "when": _offset(event_date, start_time, -0.5), "what": "Fast carb snack — banana or rice cakes", "why": "Immediate glucose for lifting performance", "recipe": "Rice Cakes + Almond Butter (R009)", "recipient": "teen"},
        {"timing": "During (if >45min)", "when": "During session", "what": "Water — electrolytes if >45min or hot", "why": "Prevent dehydration-induced strength loss", "recipe": None, "recipient": "teen"},
        {"timing": "Within 30min after", "when": _offset(event_date, start_time, 1.5), "what": "0.25-0.30g protein/kg body weight", "why": "mTORC1 activation window for muscle protein synthesis (Everett 2025)", "recipe": "Post-Practice Rebuild Plate (R019)", "recipient": "both", "critical": True},
        {"timing": "Bedtime — MANDATORY", "when": f"{event_date} 21:00", "what": "30-40g casein — cottage cheese or Greek yogurt", "why": "Overnight muscle repair proven in adolescent athletes (Everett 2025)", "recipe": "Cottage Cheese + Pineapple (R017)", "recipient": "teen", "critical": True},
    ]


def _practice(event_date: str, start_time: str) -> list:
    return [
        {"timing": "3-4hrs before practice", "when": _offset(event_date, start_time, -3.5), "what": "Pre-practice meal — carbs + protein", "why": "Fuel tank filled before high-intensity session", "recipe": "Pre-Practice Oatmeal Bowl (R018)", "recipient": "both"},
        {"timing": "30-60min before practice", "when": _offset(event_date, start_time, -0.5), "what": "Fast carb snack — banana or toast", "why": "Top up blood glucose for practice intensity", "recipe": "Banana + PB (R006)", "recipient": "teen"},
        {"timing": "Within 30min after practice", "when": _offset(event_date, start_time, 2.0), "what": "Recovery dinner — protein + carbs + veg + milk", "why": "Glycogen restoration + muscle repair window", "recipe": "Post-Practice Rebuild Plate (R019)", "recipient": "both", "critical": True},
    ]


def _pre_game_day(event_date: str) -> list:
    return [
        {"timing": "Breakfast", "when": f"{event_date} 08:00", "what": "Carb-rich breakfast", "why": "Pre-game day carb loading begins at breakfast", "recipe": "Pre-Practice Oatmeal Bowl (R018)", "recipient": "both"},
        {"timing": "Lunch", "when": f"{event_date} 12:00", "what": "Large carb + protein meal", "why": "Filling muscle glycogen — takes 24-48hrs to replenish (Everett 2025)", "recipe": "Brown Rice Salmon Bowl (R002)", "recipient": "both"},
        {"timing": "Dinner — MOST IMPORTANT MEAL OF THE WEEK", "when": f"{event_date} 19:00", "what": "HIGH CARB dinner — pasta/rice + lean protein + milk", "why": "This dinner = tomorrow's game performance. Cannot be skipped.", "recipe": "Power Pasta Bowl (R001)", "recipient": "both", "critical": True},
        {"timing": "Bedtime snack", "when": f"{event_date} 21:00", "what": "Greek yogurt or cottage cheese", "why": "Overnight casein + keeps glycogen topped", "recipe": "Cottage Cheese + Pineapple (R017)", "recipient": "teen"},
    ]


def _tournament(event_date: str, start_time: str) -> list:
    return [
        {"timing": "2-3hrs before first game", "when": _offset(event_date, start_time, -2.5), "what": "High carb breakfast — oatmeal/pancakes + protein + OJ", "why": "Multi-game day requires maximum glycogen stores", "recipe": "Tournament Morning Plate (R023)", "recipient": "both"},
        {"timing": "Between games — MANDATORY", "when": "Between each game", "what": "Banana + natural sports drink + whole grain crackers", "why": "Glycogen partially depleted after each game — must refuel immediately", "recipe": "Between-Games Refuel (R024)", "recipient": "both", "critical": True},
        {"timing": "Every 20min during each game", "when": "Throughout tournament", "what": "6-8oz natural sports drink", "why": "Electrolytes MANDATORY on tournament day — sodium critical", "recipe": None, "recipient": "teen", "critical": True},
        {"timing": "Tournament recovery dinner", "when": f"{event_date} 19:00", "what": "High protein + carb dinner + extra hydration", "why": "Multi-game glycogen depletion requires aggressive recovery", "recipe": "Tournament Recovery Dinner (R025)", "recipient": "both"},
        {"timing": "Bedtime — MANDATORY", "when": f"{event_date} 21:00", "what": "Casein protein + carbs", "why": "Multiple games = maximum muscle damage — overnight repair critical", "recipe": "Bedtime Casein Snack (R026)", "recipient": "teen", "critical": True},
    ]


def _recovery(event_date: str) -> list:
    return [
        {"timing": "All day", "when": event_date, "what": "Light carb + anti-inflammatory foods — berries, salmon, turmeric, leafy greens", "why": "Continued glycogen restoration + reduce inflammation from training load", "recipe": "Iron-Boost Hummus Plate (R020)", "recipient": "both"},
        {"timing": "Hydration focus", "when": event_date, "what": "64-72oz water — add electrolytes if previous day was a game", "why": "Rehydration continues 24-48hrs after heavy exercise", "recipe": None, "recipient": "both"},
    ]


def _rest_day(event_date: str) -> list:
    return [
        {"timing": "All meals", "when": event_date, "what": "Slightly lower carbs, maintain protein and micronutrients", "why": "Lower energy expenditure — maintain muscle protein synthesis without surplus", "recipe": None, "recipient": "both"},
        {"timing": "Iron focus (girls)", "when": event_date, "what": "Iron-rich foods — lean red meat, spinach, lentils, fortified cereal", "why": "52% of female adolescent athletes are iron deficient. Daily target: 15mg (Everett 2025)", "recipe": "Iron-Boost Hummus Plate (R020)", "recipient": "both"},
        {"timing": "Calcium — every day", "when": event_date, "what": "3 servings dairy or fortified alternatives", "why": "1,300mg/day during peak bone mass window — cannot recover later (AAP)", "recipe": None, "recipient": "both"},
    ]
