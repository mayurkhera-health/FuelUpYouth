import os
import json
import anthropic

SCIENCE_SYSTEM = """You are FuelUp's AI nutrition engine, built exclusively on pediatric sports nutrition science for athletes ages 13-17.

SCIENCE FRAMEWORK:
- Everett MD 2025 (Stony Brook) — primary reference
- Boston Children's Hospital RDN recommendations
- AAP (American Academy of Pediatrics) guidelines
- ACSM 2016

CRITICAL RULES:
1. NEVER use Harris-Benedict or adult formulas for youth
2. RMR Girls = 11.1×wt(kg)+8.4×ht(cm)−537 | RMR Boys = 11.1×wt(kg)+8.4×ht(cm)−340 (Everett 2025)
3. NEVER restrict fat in youth — disrupts hormone production (Everett 2025)
4. Iron: Girls 15mg/day, Boys 11mg/day (AAP/NIH DRI)
5. Calcium: 1,300mg/day ALL athletes — peak bone mass window (AAP)
6. LEA Alert: calories < 30 kcal/kg fat-free mass — alert parent immediately
7. Flag: protein powder/creatine/energy drinks in youth with Boston Children's Hospital evidence
8. NEVER recommend artificial food dyes (Red #40, Yellow #5, Yellow #6)
9. Pre-game day is the most missed nutrition day — glycogen takes 24-48hrs to replenish
10. FuelUp is an EDUCATIONAL food guidance tool — NOT medical nutrition therapy

Respond ONLY with valid JSON. No markdown, no prose outside the JSON."""


def _client():
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def prompt1_nutrient_targets(athlete: dict, event_type: str, calculated_targets: dict) -> dict:
    """Prompt 1: Validate + explain daily nutrient targets for athlete."""
    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""Validate these daily nutrition targets for a youth soccer athlete.

ATHLETE: {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}
Weight: {athlete['weight_lbs']}lbs | Height: {athlete['height_ft']}'{athlete['height_in']}"
Position: {athlete.get('position','N/A')} | Level: {athlete.get('competition_level','N/A')}
Sweat profile: {athlete.get('sweat_profile','Moderate')}
Allergies: {athlete.get('allergies','None')} | Diet: {athlete.get('dietary_restrictions','None')}
Supplements: {athlete.get('supplement_use','None')}

TODAY'S EVENT: {event_type}
CALCULATED TARGETS: {json.dumps(calculated_targets)}

Return JSON:
{{"validated": true, "adjustments": [], "explanation": "2-3 sentence science-backed explanation", "parent_note": "One sentence for parent dashboard", "supplement_flag": null, "lea_alert": null}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"validated": True, "explanation": msg.content[0].text, "adjustments": [], "parent_note": "", "supplement_flag": None, "lea_alert": None}


def prompt2_meal_analysis(athlete: dict, targets: dict, meal_logs: list, date: str) -> dict:
    """Prompt 2: Analyze logged meals vs targets. Generate traffic light + gap fix suggestions."""
    totals = {
        "calories": sum(m.get("calories") or 0 for m in meal_logs),
        "carbs_g": sum(m.get("carbs_g") or 0 for m in meal_logs),
        "protein_g": sum(m.get("protein_g") or 0 for m in meal_logs),
        "fat_g": sum(m.get("fat_g") or 0 for m in meal_logs),
        "iron_mg": sum(m.get("iron_mg") or 0 for m in meal_logs),
        "calcium_mg": sum(m.get("calcium_mg") or 0 for m in meal_logs),
        "water_oz": sum(m.get("water_oz") or 0 for m in meal_logs),
    }
    meal_descriptions = [m.get("description", "Unknown meal") for m in meal_logs]

    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""Analyze today's nutrition for {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}.

DATE: {date} | EVENT: {targets.get('event_type','rest')}

TARGETS: calories={targets['total_calories']} | carbs={targets['carbs_g_min']}-{targets['carbs_g_max']}g | protein={targets['protein_g_min']}-{targets['protein_g_max']}g | fat={targets['fat_g_min']}-{targets['fat_g_max']}g | iron={targets['iron_mg']}mg | calcium={targets['calcium_mg']}mg | water={targets['hydration_oz_min']}-{targets['hydration_oz_max']}oz

LOGGED: calories={totals['calories']:.0f} | carbs={totals['carbs_g']:.0f}g | protein={totals['protein_g']:.0f}g | fat={totals['fat_g']:.0f}g | iron={totals['iron_mg']:.1f}mg | calcium={totals['calcium_mg']:.0f}mg | water={totals['water_oz']:.0f}oz

MEALS: {json.dumps(meal_descriptions)}

Traffic light rules: green=>=80% of target | yellow=50-79% | red=<50%
Fuel score: 0-100 based on overall achievement + critical nutrients (iron, calcium, hydration weight extra)

Return JSON:
{{"fuel_score": 0, "overall_status": "elite/game-ready/getting-there/needs-fuel", "teen_message": "energetic encouraging message", "traffic_lights": [{{"nutrient": "Calories", "target_min": {targets['total_calories']}, "target_max": null, "logged": {totals['calories']:.0f}, "percentage": 0, "status": "green/yellow/red", "message": "short actionable message"}}], "gap_fix_suggestions": ["specific food fix 1", "food fix 2", "food fix 3"], "lea_alert": null, "iron_alert": null}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"fuel_score": 50, "overall_status": "getting-there", "teen_message": "Keep fueling!", "traffic_lights": [], "gap_fix_suggestions": [], "lea_alert": None, "iron_alert": None}


def prompt3_weekly_report(athlete: dict, week_data: dict) -> dict:
    """Prompt 3: Generate weekly parent fuel report."""
    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""Generate a weekly fuel report for the parent of {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}.

Brand voice: warm, professional, science-backed, encouraging. Never alarmist. Always solution-focused.

WEEK DATA: {json.dumps(week_data)}

Return JSON:
{{"weekly_fuel_score": 0, "score_trend": "improving/stable/declining", "what_went_well": ["specific positive 1", "specific positive 2"], "nutrients_to_focus_on": [{{"nutrient": "Iron", "gap": "Xmg/day short", "food_fixes": ["food 1"], "recipe": "R020 Iron-Boost Hummus Plate"}}], "game_day_readiness": "assessment string", "hydration_report": {{"days_goal_met": 0, "avg_oz": 0}}, "iron_alert": null, "featured_recipe": {{"id": "R001", "name": "...", "reason": "..."}}, "report_text": "full warm professional 3-4 paragraph report for email/SMS", "legal_disclaimer": "FuelUp provides educational food guidance — not medical nutrition therapy. Consult your child's physician for medical concerns."}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"report_text": msg.content[0].text, "weekly_fuel_score": 0}


def prompt4_recipe_swap(athlete: dict, disliked_recipe: str, meal_timing_category: str) -> dict:
    """Prompt 4: Generate 3 alternatives when athlete dislikes a recipe."""
    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""Generate 3 alternative meal suggestions.

ATHLETE: {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}, weight {athlete['weight_lbs']}lbs
Allergies: {athlete.get('allergies','None')} | Diet restrictions: {athlete.get('dietary_restrictions','None')}

DISLIKED: {disliked_recipe}
MEAL TIMING CATEGORY: {meal_timing_category}

Alternatives must: match nutritional goals for this timing, avoid all allergens/restrictions, appeal to a 13-17 year old, be realistic for a family to prepare.

Return JSON:
{{"alternatives": [{{"name": "Recipe name", "description": "1-2 sentences", "ingredients": "main ingredients", "why_it_works": "brief science reason", "macros": {{"calories": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0}}, "prep_time_min": 0, "dietary_tags": [], "allergens": []}}], "powered_by_note": "Nutrition data — Powered by Edamam"}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"alternatives": [], "powered_by_note": "Powered by Edamam"}


def prompt5_hydration(athlete: dict, event: dict, weather: dict, sweat_output: dict) -> dict:
    """Prompt 5: Personalized hydration + electrolyte plan."""
    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""Generate a personalized hydration plan.

ATHLETE: {athlete['first_name']}, {athlete['weight_lbs']}lbs, sweat profile: {athlete.get('sweat_profile','Moderate')}
EVENT: {event.get('event_type','practice')}, {event.get('duration_hours',1.5)}hrs, city: {event.get('city','Unknown')}
WEATHER: {weather.get('temp_f','?')}°F, humidity {weather.get('humidity','?')}%, {weather.get('description','unknown')}
SWEAT OUTPUT: {sweat_output.get('sweat_loss_liters',0):.2f}L total loss, {sweat_output.get('hydration_oz_during',0)}oz during event needed
ELECTROLYTES NEEDED: {sweat_output.get('electrolytes_needed',False)}

Return JSON:
{{"pre_event_oz": 0, "during_event_oz_per_20min": 0, "post_event_oz": 0, "total_day_oz": 0, "electrolytes_needed": false, "electrolyte_type": "natural sports drink/coconut water/water only", "sports_drink_warning": "Avoid artificial dyes (Red #40, Yellow #5, Yellow #6) — linked to behavioral changes in adolescents (Everett 2025). Choose clear/natural brands only.", "teen_message": "energetic hydration reminder", "parent_alert": null, "timing_reminders": [{{"when": "2hrs before", "action": "Drink Xoz water", "reason": "..."}}]}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"total_day_oz": 80, "electrolytes_needed": sweat_output.get("electrolytes_needed", False), "sports_drink_warning": "Avoid artificial dyes — choose clear/natural brands only."}


def prompt6_weekly_meal_plan(athlete: dict, week_schedule: list, recipes: list) -> dict:
    """Prompt 6: Generate a full week meal plan from available recipes."""
    compact_recipes = [
        {"id": r["id"], "name": r["name"], "category": r["category"],
         "calories": r["macros"]["calories"], "dietary": r["dietary"], "allergens": r["allergens"]}
        for r in recipes
    ]
    dairy_free = "dairy-free" in (athlete.get("dietary_restrictions") or "").lower() or \
                 "dairy" in (athlete.get("allergies") or "").lower()

    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""You are FuelUp's AI meal planner for youth soccer athletes.

ATHLETE: {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}
Weight: {athlete['weight_lbs']}lbs
Allergies: {athlete.get('allergies', 'None')}
Dietary restrictions: {athlete.get('dietary_restrictions', 'None')}
Dairy-free: {dairy_free}

TASK: Assign one recipe_id to every meal slot in the 7-day schedule below.

RULES:
1. Only use recipe IDs from AVAILABLE RECIPES — never invent IDs.
2. Each slot has a recipe_category — only pick a recipe whose category matches exactly.
3. Do not repeat the same recipe_id more than twice across the entire week.
4. Vary protein sources: rotate chicken, fish, plant-based, eggs across days.
5. Game/tournament pre-game slots must have highest-carb recipe in that category.
6. Rest day total calories ~15-20% lower than game day total.
7. bedtime-snack on game/practice/tournament days must be a dairy casein recipe (R017 or R026) UNLESS dairy_free=True, in which case skip it (set to null).
8. Never assign a recipe whose allergens overlap with athlete's allergies.
9. Use null for a slot only if no safe recipe exists for that category.

WEEK SCHEDULE:
{json.dumps(week_schedule, indent=2)}

AVAILABLE RECIPES (id, name, category, calories, dietary, allergens):
{json.dumps(compact_recipes, indent=2)}

Return ONLY valid JSON, no prose:
{{
  "plan": {{
    "YYYY-MM-DD": {{
      "slot_name": "recipe_id_or_null"
    }}
  }},
  "reasoning": "2-3 sentence summary of your choices",
  "variety_check": "passed or warning message"
}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"plan": {}, "reasoning": "AI generation failed — please try again.", "variety_check": "failed"}


def prompt7_estimate_macros(description: str, athlete: dict) -> dict:
    """Prompt 7: Estimate macros from a free-text meal description."""
    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SCIENCE_SYSTEM,
        messages=[{"role": "user", "content": f"""Estimate the nutritional macros for this meal description.

ATHLETE CONTEXT: age {athlete.get('age', 14)}, gender {athlete.get('gender', 'unknown')}, weight {athlete.get('weight_lbs', 130)}lbs — youth soccer athlete.

MEAL DESCRIPTION: "{description}"

Instructions:
- Estimate a realistic single-serving portion for a youth athlete (not restaurant-sized).
- If multiple items are listed (e.g. "chicken with pasta"), sum all components.
- Be conservative and realistic — base estimates on USDA standard portions.
- Round calories to nearest 10, macros to nearest 1g.
- If the description is too vague to estimate (e.g. "lunch"), return confidence: "low".

Return ONLY valid JSON:
{{"calories": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0, "iron_mg": 0, "calcium_mg": 0, "confidence": "high|medium|low", "portion_note": "brief note on portion assumption, e.g. '2 cups pasta + 4oz chicken'"}}"""}]
    )
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return {"calories": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0, "iron_mg": 0, "calcium_mg": 0, "confidence": "low", "portion_note": "Could not parse"}
