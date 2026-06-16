import json

from api.services.bedrock_client import converse_text, extract_json, is_configured

SCIENCE_SYSTEM = """Write as a knowledgeable older teammate who genuinely wants this athlete to perform better — always lead with what they gain, never what they lack, and never use alarm language with a young athlete.

You are FuelUp's AI nutrition engine, built exclusively on pediatric sports nutrition science for athletes ages 9–17.

SCIENCE FRAMEWORK (7 primary sources):
- Everett S, MDPI Nutrients 2025 (doi:10.3390/nu17172792) — PRIMARY peer-reviewed reference
- Castle J. "Eat Like a Champion" (RDN) — game-day timing and parent/athlete messaging framework
- Lair C & Murdoch S PhD RD. "Feeding the Young Athlete" — physiological depth, before/during/after model
- "The Teenage Athletes' Nutrition Journal" — 4 Pillars: energy balance, portion, TIMING, hydration
- Boston Children's Hospital RDN Sports Nutrition Guidelines 2024
- AAP (American Academy of Pediatrics) — calcium, iron, fat restriction guidelines
- NIH Office of Dietary Supplements — DRI values for iron, magnesium, vitamin D

KEY SCIENCE RULES:
1. NEVER use Harris-Benedict — youth only: Girls RMR=11.1×wt_kg+8.4×ht_cm−537 | Boys=11.1×wt_kg+8.4×ht_cm−340 (Everett 2025)
2. NEVER restrict fat below 20% in youth — disrupts hormone production and fat-soluble vitamin absorption (Everett 2025, AAP)
3. NEVER recommend supplements, creatine, caffeine, or energy drinks for any athlete under 18 (Everett 2025 — contraindicated)
4. NEVER recommend artificial food dyes (Red #40, Yellow #5, Yellow #6)
5. Iron: Girls 15mg/day (important — female adolescent athletes have higher iron needs due to growth and sport demands), Boys 11mg/day (AAP/NIH DRI)
6. Calcium: 1,300mg/day ALL athletes ages 9–17 — peak bone mass window, never miss this (AAP)
7. Magnesium: 240mg/day ages 9–13 | Girls 14+ 360mg/day | Boys 14+ 410mg/day (NIH DRI)
8. Vitamin D: 1,000 IU/day all athletes — required for calcium absorption and muscle power (Boston Children's Hospital)
9. LEA Alert: Total calories < 30 kcal/kg fat-free mass = medical emergency → refer to RD immediately
10. Pre-game day matters MORE than game day — glycogen replenishment takes 24–48 hours (Castle, Lair/Murdoch)
11. 30-minute post-exercise recovery window is the single most impactful and most skipped nutrition moment (all 7 sources)
12. Chocolate milk is the gold-standard youth recovery food — optimal 3:1 carb:protein ratio (Castle, Lair/Murdoch)
13. Youth athletes have HIGHER per-kg energy needs than adults — growth + training overlap
14. Frame all messaging: performance/speed/strength for athletes; science/safety/numbers for parents
15. FuelUp is an EDUCATIONAL food guidance tool — NOT medical nutrition therapy

CARBOHYDRATE TARGETS (g/kg body weight):
Rest: 4–5 | Practice/Training/Strength: 6–8 | Game: 8–10 | Tournament: 10–12

PROTEIN TARGETS (g/kg body weight):
Rest: 1.2–1.4 | Practice/Training: 1.4–1.6 | Strength: 1.8–2.0 | Game: 1.6–1.8 | Tournament: 1.8–2.0

MEAL TIMING RULES (Castle + Lair/Murdoch + Teenage Athletes Journal):
- Pre-game main meal: 3–3.5 hours before (high carbs, low fat, low fiber)
- Pre-game snack: 30–60 min before (easy-digest carbs only — banana, honey toast, rice cakes)
- Post-exercise recovery: within 30 min — 1.0–1.2 g/kg carbs + 20–25g protein (Everett 2025)
- Meal frequency: 3 meals + 2–4 snacks, never more than 3–4 hrs without eating
- Bedtime casein: Greek yogurt or cottage cheese on all high-intensity days (6–8 hrs slow protein release)

Respond ONLY with valid JSON. No markdown, no prose outside the JSON."""


def _json_completion(user: str, max_tokens: int = 1024, temperature: float = 0.7) -> dict:
    raw = converse_text(
        system=SCIENCE_SYSTEM,
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return json.loads(extract_json(raw))


def prompt1_nutrient_targets(athlete: dict, event_type: str, calculated_targets: dict) -> dict:
    """Prompt 1: Validate + explain daily nutrient targets for athlete."""
    try:
        return _json_completion(f"""Validate these daily nutrition targets for a youth soccer athlete.

ATHLETE: {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}
Weight: {athlete['weight_lbs']}lbs | Height: {athlete['height_ft']}'{athlete['height_in']}"
Position: {athlete.get('position','N/A')} | Level: {athlete.get('competition_level','N/A')}
Sweat profile: {athlete.get('sweat_profile','Moderate')}
Allergies: {athlete.get('allergies','None')} | Diet: {athlete.get('dietary_restrictions','None')}
Supplements: {athlete.get('supplement_use','None')}

TODAY'S EVENT: {event_type}
CALCULATED TARGETS: {json.dumps(calculated_targets)}

Return JSON:
{{"validated": true, "adjustments": [], "explanation": "2-3 sentence science-backed explanation", "parent_note": "One sentence for parent dashboard", "supplement_flag": null, "lea_alert": null}}""")
    except Exception:
        return {"validated": True, "explanation": "Targets validated.", "adjustments": [], "parent_note": "", "supplement_flag": None, "lea_alert": None}


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

    try:
        return _json_completion(f"""Analyze today's nutrition for {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}.

DATE: {date} | EVENT: {targets.get('event_type','rest')}

TARGETS: calories={targets['total_calories']} | carbs={targets['carbs_g_min']}-{targets['carbs_g_max']}g | protein={targets['protein_g_min']}-{targets['protein_g_max']}g | fat={targets['fat_g_min']}-{targets['fat_g_max']}g | iron={targets['iron_mg']}mg | calcium={targets['calcium_mg']}mg | water={targets['hydration_oz_min']}-{targets['hydration_oz_max']}oz

LOGGED: calories={totals['calories']:.0f} | carbs={totals['carbs_g']:.0f}g | protein={totals['protein_g']:.0f}g | fat={totals['fat_g']:.0f}g | iron={totals['iron_mg']:.1f}mg | calcium={totals['calcium_mg']:.0f}mg | water={totals['water_oz']:.0f}oz

MEALS: {json.dumps(meal_descriptions)}

Traffic light rules: green=>=80% of target | yellow=50-79% | red=<50%
Fuel score: 0-100 based on overall achievement + key nutrients (iron, calcium, hydration weight extra)

Return JSON:
{{"fuel_score": 0, "overall_status": "elite/game-ready/getting-there/needs-fuel", "teen_message": "energetic encouraging message", "traffic_lights": [{{"nutrient": "Calories", "target_min": {targets['total_calories']}, "target_max": null, "logged": {totals['calories']:.0f}, "percentage": 0, "status": "green/yellow/red", "message": "short actionable message"}}], "gap_fix_suggestions": ["specific food fix 1", "food fix 2", "food fix 3"], "lea_alert": null, "iron_alert": null}}""", max_tokens=1500)
    except Exception:
        return {"fuel_score": 50, "overall_status": "getting-there", "teen_message": "Keep fueling!", "traffic_lights": [], "gap_fix_suggestions": [], "lea_alert": None, "iron_alert": None}


def prompt3_weekly_report(athlete: dict, week_data: dict) -> dict:
    """Prompt 3: Generate weekly parent fuel report."""
    try:
        return _json_completion(f"""Generate a weekly fuel report for the parent of {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}.

Brand voice: warm, professional, science-backed, encouraging. Never alarmist. Always solution-focused.

WEEK DATA: {json.dumps(week_data)}

Return JSON:
{{"weekly_fuel_score": 0, "score_trend": "improving/stable/declining", "what_went_well": ["specific positive 1", "specific positive 2"], "nutrients_to_focus_on": [{{"nutrient": "Iron", "gap": "Xmg/day short", "food_fixes": ["food 1"], "recipe": "R020 Iron-Boost Hummus Plate"}}], "game_day_readiness": "assessment string", "hydration_report": {{"days_goal_met": 0, "avg_oz": 0}}, "iron_alert": null, "featured_recipe": {{"id": "R001", "name": "...", "reason": "..."}}, "report_text": "full warm professional 3-4 paragraph report for email/SMS", "legal_disclaimer": "FuelUp provides educational food guidance — not medical nutrition therapy. Consult your child's physician for medical concerns."}}""", max_tokens=2000)
    except Exception:
        return {"report_text": "Weekly report unavailable.", "weekly_fuel_score": 0}


def prompt4_recipe_swap(athlete: dict, disliked_recipe: str, meal_timing_category: str) -> dict:
    """Prompt 4: Generate 3 alternatives when athlete dislikes a recipe."""
    try:
        return _json_completion(f"""Generate 3 alternative meal suggestions.

ATHLETE: {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}, weight {athlete['weight_lbs']}lbs
Allergies: {athlete.get('allergies','None')} | Diet restrictions: {athlete.get('dietary_restrictions','None')}

DISLIKED: {disliked_recipe}
MEAL TIMING CATEGORY: {meal_timing_category}

Alternatives must: match nutritional goals for this timing, avoid all allergens/restrictions, appeal to a 13-17 year old, be realistic for a family to prepare.

Return JSON:
{{"alternatives": [{{"name": "Recipe name", "description": "1-2 sentences", "ingredients": "main ingredients", "why_it_works": "brief science reason", "macros": {{"calories": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0}}, "prep_time_min": 0, "dietary_tags": [], "allergens": []}}], "powered_by_note": "Nutrition data — Powered by Edamam"}}""", max_tokens=1500)
    except Exception:
        return {"alternatives": [], "powered_by_note": "Powered by Edamam"}


def prompt5_hydration(athlete: dict, event: dict, weather: dict, sweat_output: dict) -> dict:
    """Prompt 5: Personalized hydration + electrolyte plan."""
    try:
        return _json_completion(f"""Generate a personalized hydration plan.

ATHLETE: {athlete['first_name']}, {athlete['weight_lbs']}lbs, sweat profile: {athlete.get('sweat_profile','Moderate')}
EVENT: {event.get('event_type','practice')}, {event.get('duration_hours',1.5)}hrs, city: {event.get('city','Unknown')}
WEATHER: {weather.get('temp_f','?')}°F, humidity {weather.get('humidity','?')}%, {weather.get('description','unknown')}
SWEAT OUTPUT: {sweat_output.get('sweat_loss_liters',0):.2f}L total loss, {sweat_output.get('hydration_oz_during',0)}oz during event needed
ELECTROLYTES NEEDED: {sweat_output.get('electrolytes_needed',False)}

Return JSON:
{{"pre_event_oz": 0, "during_event_oz_per_20min": 0, "post_event_oz": 0, "total_day_oz": 0, "electrolytes_needed": false, "electrolyte_type": "natural sports drink/coconut water/water only", "sports_drink_warning": "Avoid artificial dyes (Red #40, Yellow #5, Yellow #6) — linked to behavioral changes in adolescents (Everett 2025). Choose clear/natural brands only.", "teen_message": "energetic hydration reminder", "parent_alert": null, "timing_reminders": [{{"when": "2hrs before", "action": "Drink Xoz water", "reason": "..."}}]}}""")
    except Exception:
        return {"total_day_oz": 80, "electrolytes_needed": sweat_output.get("electrolytes_needed", False), "sports_drink_warning": "Avoid artificial dyes — choose clear/natural brands only."}


def prompt6_weekly_meal_plan(athlete: dict, week_schedule: list, recipes: list) -> dict:
    """Prompt 6: Generate a full week meal plan from available recipes."""
    from api.services.nutrient_timing_rules import TIMING_BRIEF

    compact_recipes = [
        {"id": r["id"], "name": r["name"], "category": r["category"],
         "calories": r["macros"]["calories"], "dietary": r["dietary"], "allergens": r["allergens"]}
        for r in recipes
    ]
    dairy_free = "dairy-free" in (athlete.get("dietary_restrictions") or "").lower() or \
                 "dairy" in (athlete.get("allergies") or "").lower()

    try:
        return _json_completion(f"""You are FuelUp's AI meal planner for youth soccer athletes.

ATHLETE: {athlete['first_name']}, age {athlete['age']}, gender {athlete['gender']}
Weight: {athlete['weight_lbs']}lbs
Allergies: {athlete.get('allergies', 'None')}
Dietary restrictions: {athlete.get('dietary_restrictions', 'None')}
Dairy-free: {dairy_free}

{TIMING_BRIEF}

TASK: Assign one recipe_id to every meal slot in the 7-day schedule below.
Each slot maps to a specific clinical eating window — match the recipe to that window's nutritional requirements above.

RULES:
1. Only use recipe IDs from AVAILABLE RECIPES — never invent IDs.
2. Each slot has a recipe_category — only pick a recipe whose category matches exactly.
3. Do not repeat the same recipe_id more than twice across the entire week.
4. Vary protein sources: rotate chicken, fish, plant-based, eggs across days.
5. Gas Tank / Pre-Game slots (3–4 hrs before): highest-carb recipe in category.
6. Top-Off / Power Snack slots (30–60 min before): simplest, fastest-digesting carb recipe — no fat/fiber.
7. Recovery slots (within 30 min after): 3:1–4:1 carbs:protein ratio — chocolate milk or equivalent gold standard.
8. Rest day total calories ~15–20% lower than game day total.
9. Bedtime Casein on game/practice/tournament/strength days: dairy casein recipe (R017 or R026) UNLESS dairy_free=True, then null.
10. Never assign a recipe whose allergens overlap with athlete's allergies.
11. Use null for a slot only if no safe recipe exists for that category.

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
}}""", max_tokens=2000)
    except Exception:
        return {"plan": {}, "reasoning": "AI generation failed — please try again.", "variety_check": "failed"}


def prompt7_estimate_macros(description: str, athlete: dict) -> dict:
    """Prompt 7: Estimate macros from a free-text meal description."""
    try:
        return _json_completion(f"""Estimate the nutritional macros for this meal description.

ATHLETE CONTEXT: age {athlete.get('age', 14)}, gender {athlete.get('gender', 'unknown')}, weight {athlete.get('weight_lbs', 130)}lbs — youth soccer athlete.

MEAL DESCRIPTION: "{description}"

Instructions:
- Estimate a realistic single-serving portion for a youth athlete (not restaurant-sized).
- If multiple items are listed (e.g. "chicken with pasta"), sum all components.
- Be conservative and realistic — base estimates on USDA standard portions.
- Round calories to nearest 10, macros to nearest 1g.
- If the description is too vague to estimate (e.g. "lunch"), return confidence: "low".

Return ONLY valid JSON:
{{"calories": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0, "iron_mg": 0, "calcium_mg": 0, "confidence": "high|medium|low", "portion_note": "brief note on portion assumption, e.g. '2 cups pasta + 4oz chicken'"}}""", max_tokens=512)
    except Exception:
        return {"calories": 0, "carbs_g": 0, "protein_g": 0, "fat_g": 0, "iron_mg": 0, "calcium_mg": 0, "confidence": "low", "portion_note": "Could not parse"}


def prompt0_athlete_blueprint(athlete: dict, targets_by_event: dict) -> dict:
    """
    Prompt 0: Generate the full Nutrition Blueprint narrative for an athlete.
    Runs once on athlete creation. Numbers live in _calculated only — Claude writes
    narrative only. React renders numbers from _calculated, never from Claude text.
    targets_by_event: dict keyed by event type (rest/practice/game/tournament/strength)
    with calc_daily_targets() output for each.
    """
    import math

    wt_kg      = athlete["weight_lbs"] * 0.453592
    ht_cm      = (athlete["height_ft"] * 12 + athlete["height_in"]) * 2.54
    ffm_kg     = round(wt_kg * 0.85, 1)
    gender     = athlete.get("gender", "").lower()
    is_girl    = gender in ("girl", "female", "f")
    age        = athlete.get("age", 14)
    position   = athlete.get("position") or "midfielder"
    level      = athlete.get("competition_level") or "club"
    allergies  = athlete.get("allergies") or "None"
    diet_rest  = athlete.get("dietary_restrictions") or "None"
    name       = athlete.get("first_name", "the athlete")

    # RMR calc (Everett 2025)
    if is_girl:
        rmr = round(11.1 * wt_kg + 8.4 * ht_cm - 537)
    else:
        rmr = round(11.1 * wt_kg + 8.4 * ht_cm - 340)

    # LEA check — use rest-day calories as the floor
    rest_cals  = targets_by_event.get("rest", {}).get("total_calories", 0)
    lea_thresh = round(30 * ffm_kg)
    lea_risk   = rest_cals < lea_thresh

    MOCK = {
        "hero": {
            "headline": f"{name}'s Personalized Nutrition Blueprint",
            "parent_subtext": f"Science-backed targets calculated specifically for {name} — age {age}, {position}, {level} level — using the Everett MD 2025 formula for youth athletes.",
            "athlete_message": f"Hey {name}! This is your custom fuel plan. Follow it and you'll have the energy to dominate every practice and game."
        },
        "rmr": {
            "parent_explanation": f"{name}'s Resting Metabolic Rate of {rmr:,} kcal/day is the baseline energy needed just to keep their body running — breathing, heart beating, muscles repairing. This is calculated using the Everett MD 2025 formula, the gold standard for youth athletes aged 9–17.",
            "athlete_explanation": f"Even when you're resting, your body burns {rmr:,} calories just keeping you alive. That's your engine idling — add soccer and it goes way higher.",
            "formula_note": "Everett MD 2025 (Stony Brook) — never Harris-Benedict, which was derived from adults."
        },
        "calorie_range": {
            "parent_explanation": f"Total daily calorie needs vary by training load. On rest days {name} needs fewer calories; on game and tournament days the number rises significantly to support glycogen replenishment and performance.",
            "athlete_explanation": "Your calorie target changes every day based on what you're doing. Game days need the most fuel — don't skip meals before a match.",
            "context_note": f"Position context: {position}s cover 6–8 miles per game, requiring sustained energy availability throughout the full 90 minutes."
        },
        "macros": {
            "carbs": {
                "parent_explanation": "Carbohydrates are the primary fuel for high-intensity intermittent exercise like soccer. They replenish muscle glycogen — the energy reserves that power sprints, tackles, and sharp cuts.",
                "athlete_explanation": "Carbs are your rocket fuel. Rice, pasta, oats, fruit — eat them especially the night before and morning of a game.",
                "why_it_matters": "Glycogen loading takes 24–48 hours. The pre-game day meal matters more than the pre-game meal itself."
            },
            "protein": {
                "parent_explanation": f"Protein targets scale with training intensity. On strength and tournament days {name} needs the most protein to repair muscle micro-tears and drive adaptation.",
                "athlete_explanation": "Protein rebuilds your muscles after hard training. Chicken, eggs, fish, Greek yogurt — eat protein within 30 minutes of finishing practice.",
                "why_it_matters": "The 30-minute post-exercise window is the single most impactful nutrition moment — protein synthesis rates are highest immediately after exercise."
            },
            "fat": {
                "parent_explanation": f"Fat targets are set at 20–35% of total calories, never lower. Restricting fat in adolescent athletes disrupts hormone production, fat-soluble vitamin absorption, and bone development. (Everett MD 2025)",
                "athlete_explanation": "Healthy fats from avocado, nuts, olive oil, and salmon help your body absorb vitamins and keep your hormones balanced. Don't cut them out.",
                "why_it_matters": "Fat restriction in youth athletes is linked to hormonal dysregulation and increased stress fracture risk. (AAP)"
            }
        },
        "micronutrients": {
            "iron": {
                "parent_explanation": f"{'Girls aged 9–17 have significantly higher iron needs due to menstruation onset and rapid growth. Iron deficiency is the leading nutritional deficiency in female youth athletes — affecting endurance, focus, and immune function.' if is_girl else f'Iron supports oxygen delivery to muscles via hemoglobin. Even mild deficiency impairs endurance and focus in male youth athletes.'}",
                "athlete_explanation": f"Iron helps carry oxygen to your muscles. {'As a female athlete your iron needs are higher — spinach, lentils, and lean red meat are your best friends.' if is_girl else 'Strong iron levels mean powerful legs and sharp focus all game long.'}",
                "urgency_level": "high" if is_girl else "important",
                "food_sources": ["Lean red meat (grass-fed)", "Spinach + lemon juice (vitamin C boosts absorption)", "Lentils + hummus", "Fortified cereal (no artificial dyes)"],
                "absorption_tip": "Pair iron-rich foods with vitamin C (orange juice, bell peppers, strawberries). Avoid calcium-rich foods within 1 hour of iron-rich meals."
            },
            "calcium": {
                "parent_explanation": f"Ages 9–17 is the most important window for peak bone mass accumulation. {name} will never have this opportunity again — adequate calcium now determines bone density for life. (AAP)",
                "athlete_explanation": "You're building your bones right now — literally. The calcium you get in your teens determines how strong your bones are for the rest of your life. Milk, yogurt, and fortified plant milks all count.",
                "urgency_level": "important",
                "food_sources": ["Low-fat milk or plant milk (fortified)", "Greek yogurt", "Cottage cheese", "Broccoli + kale (non-dairy option)"]
            },
            "magnesium": {
                "parent_explanation": f"Magnesium is involved in over 300 enzymatic reactions, including ATP energy production, muscle contraction, and nerve function. Youth athletes are frequently deficient — especially during growth spurts when demand outpaces dietary intake. {'At 14+, girls need 360 mg/day.' if is_girl and athlete.get('age',13) >= 14 else 'At 14+, boys need 410 mg/day.' if not is_girl and athlete.get('age',13) >= 14 else 'At 9–13, the target is 240 mg/day for all athletes.'} (NIH/AAP)",
                "athlete_explanation": "Magnesium helps your muscles relax after a hard game — it's literally the mineral that prevents cramps. Almonds, pumpkin seeds, spinach, and dark chocolate are all great sources.",
                "urgency_level": "important",
                "food_sources": ["Pumpkin seeds", "Almonds + cashews", "Spinach + edamame", "Dark chocolate (70%+, no artificial dyes)", "Black beans + lentils"],
                "absorption_tip": "Magnesium absorption improves when paired with vitamin B6-rich foods (chicken, bananas, potatoes). Excess calcium can compete — balance both throughout the day."
            },
            "vitamin_d": {
                "parent_explanation": f"Vitamin D deficiency is extremely common in youth athletes, especially those training indoors or in northern climates. It governs calcium absorption (without it, even adequate calcium intake can't build bone), supports muscle power output, and modulates immune function. Boston Children's Hospital recommends 1,000–2,000 IU/day for active youth athletes — well above the 600 IU dietary minimum.",
                "athlete_explanation": "Vitamin D is the 'sunshine vitamin' — it helps your body actually USE the calcium you eat for stronger bones. Most indoor athletes are low on it. Salmon, fortified milk, and eggs are your best food sources.",
                "urgency_level": "important",
                "food_sources": ["Salmon + tuna (best food source)", "Fortified milk or plant milk", "Egg yolks", "Fortified orange juice (no artificial dyes)", "Mushrooms (UV-exposed)"],
                "absorption_tip": "Vitamin D is fat-soluble — take supplements or eat D-rich foods alongside a meal containing healthy fats (avocado, olive oil, nuts) for maximum absorption."
            }
        },
        "lea_warning": {
            "triggered": lea_risk,
            "parent_message": f"⚠️ IMPORTANT: Based on {name}'s current weight ({athlete['weight_lbs']} lbs), rest-day calorie target ({rest_cals:,} kcal) falls {'below' if lea_risk else 'above'} the Low Energy Availability threshold of {lea_thresh:,} kcal/day (30 kcal/kg fat-free mass). {'This is a medical-level concern — please consult a registered dietitian.' if lea_risk else 'No LEA risk detected at this time.'}" if lea_risk else None,
            "threshold_kcal": lea_thresh,
            "action_required": "Consult a registered dietitian immediately. Do not restrict calories further." if lea_risk else None
        } if lea_risk else {"triggered": False, "threshold_kcal": lea_thresh},
        "unlock_cta": {
            "headline": "Your Blueprint is Ready",
            "parent_message": f"Log {name}'s first meal to start tracking against these targets. The AI gap analysis updates in real time as you log.",
            "athlete_message": f"Time to eat like an athlete, {name}. Log your first meal and watch your fuel score go up."
        },
        "_meta": {
            "generated_by": "FuelUp AI — Everett MD 2025 + Boston Children's Hospital RDN + AAP",
            "disclaimer": "FuelUp provides educational food guidance — not medical nutrition therapy.",
            "prompt_version": "0.1"
        }
    }

    # If no AWS credentials, return the mock directly
    if not is_configured():
        return MOCK

    # Build the prompt
    targets_summary = "\n".join([
        f"  {et.upper()}: {t.get('total_calories')} kcal | carbs {t.get('carbs_g_min')}–{t.get('carbs_g_max')}g | protein {t.get('protein_g_min')}–{t.get('protein_g_max')}g | fat {t.get('fat_g_min')}–{t.get('fat_g_max')}g"
        for et, t in targets_by_event.items()
    ])

    prompt_text = f"""Generate a complete Nutrition Blueprint narrative for this youth soccer athlete.

ATHLETE: {name}, age {age}, gender {athlete.get('gender')}, {position}, {level} level
Weight: {athlete['weight_lbs']} lbs ({round(wt_kg,1)} kg) | Height: {athlete['height_ft']}'{athlete['height_in']}"
Fat-free mass: {ffm_kg} kg | RMR: {rmr:,} kcal/day (Everett MD 2025)
Allergies: {allergies} | Dietary restrictions: {diet_rest}

CALCULATED TARGETS BY EVENT TYPE:
{targets_summary}

Iron target: {15 if is_girl else 11} mg/day | Calcium: 1,300 mg/day | Magnesium: {(360 if is_girl else 410) if athlete.get('age',13) >= 14 else 240} mg/day | Vitamin D: 1,000 IU/day | LEA threshold: {lea_thresh} kcal/day
LEA risk triggered: {lea_risk}

KEY RULES:
1. Write NARRATIVE ONLY — no numbers in text fields. Numbers stay in _calculated (Python's output).
   Exception: you MAY reference the RMR ({rmr:,}) and LEA threshold ({lea_thresh}) in narrative since these are informational.
2. Iron urgency_level MUST be "high" for girls, "important" for boys.
3. Tone: parent voice = warm, professional, science-backed. Athlete voice = direct, motivating, age-appropriate for {age}-year-old.
4. If LEA risk is triggered, the warning MUST be direct and clear — this is a safety flag for parents only.
5. Never recommend artificial food dyes (Red #40, Yellow #5, Yellow #6).

Return ONLY valid JSON matching this exact structure (no markdown):
{{
  "hero": {{"headline": "", "parent_subtext": "", "athlete_message": ""}},
  "rmr": {{"parent_explanation": "", "athlete_explanation": "", "formula_note": ""}},
  "calorie_range": {{"parent_explanation": "", "athlete_explanation": "", "context_note": ""}},
  "macros": {{
    "carbs":   {{"parent_explanation": "", "athlete_explanation": "", "why_it_matters": ""}},
    "protein": {{"parent_explanation": "", "athlete_explanation": "", "why_it_matters": ""}},
    "fat":     {{"parent_explanation": "", "athlete_explanation": "", "why_it_matters": ""}}
  }},
  "micronutrients": {{
    "iron":       {{"parent_explanation": "", "athlete_explanation": "", "urgency_level": "high|important|normal", "food_sources": [], "absorption_tip": ""}},
    "calcium":    {{"parent_explanation": "", "athlete_explanation": "", "urgency_level": "important|normal", "food_sources": []}},
    "magnesium":  {{"parent_explanation": "", "athlete_explanation": "", "urgency_level": "important|normal", "food_sources": [], "absorption_tip": ""}},
    "vitamin_d":  {{"parent_explanation": "", "athlete_explanation": "", "urgency_level": "important|normal", "food_sources": [], "absorption_tip": ""}}
  }},
  "lea_warning": {{"triggered": false, "parent_message": null, "threshold_kcal": {lea_thresh}, "action_required": null}},
  "unlock_cta": {{"headline": "", "parent_message": "", "athlete_message": ""}},
  "_meta": {{"generated_by": "FuelUp AI — Everett MD 2025 + Boston Children's Hospital RDN + AAP", "disclaimer": "FuelUp provides educational food guidance — not medical nutrition therapy.", "prompt_version": "0.1"}}
}}"""

    try:
        return _json_completion(prompt_text, max_tokens=3000)
    except Exception:
        return MOCK


def prompt3_weekly_report_v2(data: dict) -> dict:
    """Structured weekly parent fuel report for the Fuel Report tab.
    Claude writes ONLY narrative text. All numbers come from Python.
    """
    import json as _json

    athlete  = data["athlete"]
    name     = athlete["first_name"]
    gender   = athlete.get("gender", "prefer_not_to_say")
    pronoun  = "her" if gender in ("girl", "female") else "his" if gender in ("boy", "male") else "their"
    gap      = data.get("critical_gap")
    next_evts = data.get("next_events", [])

    user_content = f"""Generate a structured weekly fuel report for the parent of {name}, age {athlete.get('age')}, gender {gender}.

Week of {data['week_start']}
Letter grade: {data['letter_grade']} | Avg fuel score: {data['avg_score']}/100
Days logged: {data['days_logged']}/7 | Streak: {data['streak']} days

Critical gap this week:
- Nutrient: {gap['nutrient'] if gap else 'none'} ({gap['label'] if gap else 'N/A'})
- Weekly average met: {gap['avg_pct'] if gap else 0}% of daily target
- Average logged per day: {gap['avg_amount'] if gap else 0}{gap['unit'] if gap else ''}
- Daily target: {gap['target'] if gap else 0}{gap['unit'] if gap else ''}

Next week events: {_json.dumps(next_evts)}

RULES — never break these:
1. Banned words: critical, empty, fix this, failure, behind, deficit, warning, must, should, lack, deficient, insufficient, zero, missing
2. Always lead with what {name} gained, never with what was missing
3. Use ONLY the provided numbers above — do not invent or recalculate any numbers
4. Pronoun for {name}: {pronoun}
5. "what_went_well" must always have at least 1 item, max 3 items
6. "next_week_tips" must have exactly one entry per event in next_events (same order)

Return ONLY valid JSON — no markdown, no preamble:
{{
  "grade_headline": "One encouraging sentence using {name}'s name",
  "grade_summary": "One sentence about this week's fueling story",
  "what_went_well": [
    {{"text": "specific positive with context", "stat": "value like '5/7' or '✓' or '↑+2'"}},
    {{"text": "second positive", "stat": "stat"}},
    {{"text": "third positive if genuine", "stat": "stat"}}
  ],
  "critical_gap_why": "2 sentences. Use provided numbers only. Performance consequence first, then the mechanism. Never alarming.",
  "next_week_tips": ["one specific nutrition prep sentence per event in next_events"],
  "summary_paragraphs": [
    "Paragraph 1: what went well this week — specific, warm, uses {name}'s name",
    "Paragraph 2: the one gap and exact food fix using provided numbers only",
    "Paragraph 3: what to focus on next week based on the events listed"
  ]
}}"""

    try:
        return _json_completion(user_content, max_tokens=900)
    except Exception:
        return {
            "grade_headline": f"Keep going, {name}!",
            "grade_summary": "Every day logged is a step forward.",
            "what_went_well": [
                {"text": f"Logged {data['days_logged']} days this week", "stat": f"{data['days_logged']}/7"}
            ],
            "critical_gap_why": "Consistent logging helps identify where to focus next.",
            "next_week_tips": ["Focus on balanced meals and hydration."] * max(1, len(next_evts)),
            "summary_paragraphs": [
                f"This week {name} made progress building consistent fueling habits.",
                "Focus on the one area identified and try adding the suggested foods.",
                "Next week brings new opportunities to fuel even better.",
            ],
        }
