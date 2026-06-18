"""Nutrition Coach — context assembly and AI call."""
import json

from api.database import get_conn
from api.services.weather import get_weather
from api.services.nutrition_calc import calc_daily_targets


# ── Safety filters ─────────────────────────────────────────────────────────────
# Two-layer architecture: input filter (before Bedrock) + output filter (after).
# Filters are the hard floor. Model prompt rules are a secondary reinforcement.
# Next step: evaluate a stronger model to raise the quality ceiling — but these
# filters stay regardless of which model is configured.

_WEIGHT_INPUT_TRIGGERS = [
    "lose weight", "losing weight", "lost weight",
    "need to lose", "want to lose", "trying to lose",
    "drop some weight", "drop a few pounds", "drop some pounds",
    "shed some pounds", "shed a few pounds",
    "lose a few pounds", "lose some pounds",
    "cut calories", "cutting calories", "calorie deficit", "calorie cut",
    "fewer calories", "less calories", "count calories",
    "eat less", "eating less", "eat lighter", "eat a little less",
    "too fat", "too heavy", "overweight",
    "slim down", "slimming down", "thinner", "skinnier",
    "body fat percent", "bmi",
    "go on a diet", "on a diet to lose", "diet to lose",
]

_MEDICAL_INPUT_TRIGGERS = [
    "strain", "sprain", "fracture", "stress fracture",
    "torn", "tear", "concussion",
    "shin splints", "tendinitis", "plantar fasciitis", "bursitis",
    "pulled muscle", "pulled my hamstring", "pulled my quad",
    "pulled my calf", "pulled my groin",
    "ligament", "tendon", "cartilage", "acl", "mcl", "pcl",
    "knee pain", "knee hurts", "knee aching", "knee clicking",
    "knee popping", "knee swollen",
    "hip pain", "hip hurts",
    "ankle pain", "ankle hurts", "ankle swollen",
    "shoulder pain", "shoulder hurts",
    "hamstring pain", "hamstring hurts", "hamstring sore for",
    "shin pain", "shin hurts",
    "back pain", "back hurts",
    "wrist pain", "wrist hurts",
    "elbow pain", "elbow hurts",
    "has been sore for", "been hurting for",
    "is it a strain", "is it a tear", "is it a sprain",
    "do i have a",
    "what's wrong with my", "what did i do to my",
    "swelling", "swollen",
    "diagnosis", "diagnose",
]

# Output triggers are wider and paraphrase-aware — over-firing is the safe
# direction when the output filter is the last line before a minor sees content.
_WEIGHT_OUTPUT_TRIGGERS = [
    "lose weight", "losing weight", "weight loss",
    "cut calories", "calorie deficit", "fewer calories", "less calories",
    "slim down", "slimming",
    "sustainable weight", "healthy weight loss",
    "help you lose", "talk about losing", "discuss losing",
]

_MEDICAL_OUTPUT_TRIGGERS = [
    # Diagnoses — naming, implying, or ruling out
    "sounds like a", "seems like a", "appears to be a",
    "probably a ", "likely a ", "might be a ", "could be a ",
    "it's more like", "it's probably a", "it's likely a",
    "that's a strain", "that's a sprain", "that's a tear", "that's a fracture",
    "you've strained", "you've torn", "you've sprained",
    "not a full tear", "not a tear", "not a fracture", "not a serious injury",
    "just a minor", "just a strain", "just a sprain",
    "overuse strain", "overuse injury", "muscle strain", "muscle tear",
    "microtear", "micro-tear",
    # Ice / cold protocols
    "ice it", "ice the", "apply ice", "put ice", "use ice", "try ice",
    "ice pack", "cold pack", "cold compress", "icing your",
    # Heat protocols
    "use heat", "try heat", "heat pack", "warm compress", "heating pad",
    # Rest / avoidance protocols
    "rest for", "rest your",
    "take a few days off", "take a day or two off",
    "avoid running", "avoid practice", "skip practice",
    "take it easy on your",
    # Compression / elevation / bracing
    "compression sleeve", "wrap it", "brace it", "athletic tape", "kinesio",
    "keep it elevated", "elevate your",
    # Medication
    "ibuprofen", "advil", "tylenol", "acetaminophen",
    "anti-inflammatory medication", "nsaid", "pain reliever", "pain medication",
    # Manual therapy protocols
    "gentle stretching", "light stretching", "stretch it out",
    "foam roll", "foam roller",
    # RICE protocol (not the food)
    "r.i.c.e", "rest, ice, compression",
    # Prognosis
    "should heal", "heal on its own", "you'll be fine in",
    "should be better in", "back to normal in",
    # Physical therapy (shouldn't be prescribing this)
    "physical therapy", "physiotherapist",
]

# Fixed responses — not model-generated, guaranteed safe.
_WEIGHT_INPUT_RESPONSE = (
    "Fueling well is what makes you fast — your body needs energy to perform "
    "at its best, not less food. If you have questions about your body, your "
    "team's dietitian or a trusted adult is the right person to talk to. "
    "I'm here for fueling questions whenever you're ready."
)
_MEDICAL_INPUT_RESPONSE = (
    "That's outside what I can help with — please talk to your coach or a "
    "sports-medicine doctor, they're the right people for that. I'm here for "
    "nutrition and fueling questions whenever you're ready."
)
# Output weight response is warmer — the model volunteering body-image content
# unprompted is a vulnerable moment, not a direct ask.
_WEIGHT_OUTPUT_RESPONSE = (
    "I hear you, and those feelings are real. This is worth talking through "
    "with someone who really knows you — a parent, trusted adult, or your "
    "team's dietitian. I'm here for fueling and game-day questions whenever "
    "you need me."
)
_MEDICAL_OUTPUT_RESPONSE = (
    "That's outside what I can help with — please talk to your coach or a "
    "sports-medicine doctor, they're the right people for that. I'm here for "
    "nutrition and fueling questions whenever you're ready."
)


def _check_input_safe(message: str) -> str | None:
    msg = message.lower()
    if any(p in msg for p in _WEIGHT_INPUT_TRIGGERS):
        return _WEIGHT_INPUT_RESPONSE
    if any(p in msg for p in _MEDICAL_INPUT_TRIGGERS):
        return _MEDICAL_INPUT_RESPONSE
    return None


def _check_output_safe(response: str) -> str | None:
    resp = response.lower()
    if any(p in resp for p in _WEIGHT_OUTPUT_TRIGGERS):
        return _WEIGHT_OUTPUT_RESPONSE
    if any(p in resp for p in _MEDICAL_OUTPUT_TRIGGERS):
        return _MEDICAL_OUTPUT_RESPONSE
    return None


def _heat_flag(temp_f: float, humidity: int) -> tuple[bool, str]:
    effective = temp_f + (5 if humidity > 70 else 0)
    if effective >= 95:
        return True, "very_hot"
    if effective >= 85:
        return True, "hot"
    if effective >= 78:
        return True, "warm"
    return False, "none"


def assemble_context(
    *,
    athlete_id: int,
    window_key: str,
    window_label: str,
    window_time: str,
    category_key: str,
    category_label: str,
    plan_date: str,
    conn,
) -> dict:
    athlete = conn.execute(
        "SELECT * FROM athletes WHERE id = ?", (athlete_id,)
    ).fetchone()
    if not athlete:
        raise ValueError(f"Athlete {athlete_id} not found")
    athlete = dict(athlete)

    blueprint: dict = {}
    if athlete.get("blueprint_json"):
        try:
            blueprint = json.loads(athlete["blueprint_json"])
        except Exception:
            pass

    event = conn.execute(
        "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time LIMIT 1",
        (athlete_id, plan_date),
    ).fetchone()
    event = dict(event) if event else None

    weather: dict | None = None
    if event and event.get("city"):
        raw = get_weather(event["city"])
        if not raw.get("error") and raw.get("temp_f") is not None:
            heat_flag, heat_level = _heat_flag(
                float(raw["temp_f"]),
                int(raw.get("humidity", 50)),
            )
            weather = {
                "temp_f": raw["temp_f"],
                "humidity": raw.get("humidity"),
                "description": raw.get("description", ""),
                "heat_flag": heat_flag,
                "heat_level": heat_level,
            }

    event_type = (event or {}).get("event_type", "rest") or "rest"
    targets = calc_daily_targets(athlete, event_type)

    return {
        "blueprint": {
            "name": athlete.get("first_name", "Athlete"),
            "age": athlete.get("age"),
            "gender": athlete.get("gender"),
            "allergies": athlete.get("allergies", ""),
            "dietary_restrictions": athlete.get("dietary_restrictions", ""),
            "supplement_use": athlete.get("supplement_use", ""),
            "sweat_profile": athlete.get("sweat_profile", ""),
            "blueprint_summary": blueprint.get("headline", ""),
            "carb_category": blueprint.get("carb_category", ""),
        },
        "schedule": {
            "window_key": window_key,
            "window_label": window_label,
            "window_time": window_time,
            "category_key": category_key,
            "category_label": category_label,
            "plan_date": plan_date,
            "event_name": event.get("event_name") if event else None,
            "event_type": event_type,
            "event_start_time": event.get("start_time") if event else None,
            "event_city": event.get("city") if event else None,
        },
        "weather": weather,
        "baseline": {
            "carbs_g_min": targets["carbs_g_min"],
            "carbs_g_max": targets["carbs_g_max"],
            "protein_g_min": targets["protein_g_min"],
            "protein_g_max": targets["protein_g_max"],
            "hydration_oz_min": targets["hydration_oz_min"],
            "hydration_oz_max": targets["hydration_oz_max"],
            "lea_alert": targets["lea_alert"],
        },
    }


def build_system_prompt(context: dict, persona: str) -> str:
    bp = context["blueprint"]
    sch = context["schedule"]
    base = context["baseline"]
    weather = context.get("weather") or {}

    name = bp.get("name", "the athlete")
    allergies = (bp.get("allergies") or "").strip()
    restrictions = (bp.get("dietary_restrictions") or "").strip()

    allergy_block = ""
    if allergies:
        allergy_block += f"\n⚠️  ALLERGY ALERT — NEVER suggest these: {allergies}. Hard stop."
    if restrictions:
        allergy_block += f"\nDietary restrictions (always respect): {restrictions}."

    heat_block = ""
    if weather.get("heat_flag"):
        temp = weather.get("temp_f", "")
        city = sch.get("event_city", "their area")
        heat_block = (
            f"\n🌡️  HEAT ADVISORY: It is {temp}°F in {city} today "
            f"({weather.get('heat_level', 'hot')} conditions). "
            "Emphasize extra hydration — 8-12 oz more fluid per hour of activity. "
            "Mention electrolytes for any activity over 60 minutes."
        )

    event_block = ""
    if sch.get("event_name"):
        event_block = f"\nToday's event: {sch['event_name']} ({sch.get('event_type', 'activity')}"
        if sch.get("event_start_time"):
            event_block += f" at {sch['event_start_time']}"
        event_block += ")."

    if persona == "parent":
        audience = (
            f"You are speaking to {name}'s parent/guardian. "
            "Help them understand what to prepare for their athlete. "
            "Use a supportive, parent-educator tone."
        )
    else:
        audience = (
            f"You are speaking directly to {name}, a youth athlete (age {bp.get('age', '13–17')}). "
            "Use encouraging, age-appropriate language — like a knowledgeable coach, not a textbook."
        )

    return f"""You are FuelUp Nutrition Coach — a knowledgeable, warm youth sports nutrition assistant built on evidence-based pediatric sports nutrition science (Everett MD 2025, Boston Children's Hospital RDN, AAP, ACSM 2016).

{audience}

CURRENT FUELING WINDOW: {sch['window_label']} ({sch['window_time']})
Focus area: {sch.get('category_label', 'balanced fueling')}
{event_block}

ATHLETE PROFILE — internal calibration only, DO NOT quote these numbers:
- Carbohydrate target today: {base['carbs_g_min']}–{base['carbs_g_max']} g ({sch.get('event_type', 'rest')} day)
- Protein target: {base['protein_g_min']}–{base['protein_g_max']} g
- Hydration target: {base['hydration_oz_min']}–{base['hydration_oz_max']} oz
- Blueprint summary: {bp.get('blueprint_summary') or 'balanced youth athlete'}
- Sweat profile: {bp.get('sweat_profile') or 'average'}
{allergy_block}
{heat_block}

MANDATORY RULES:
1. NEVER quote specific calorie, carb, protein, or iron numbers to the athlete or parent. Use food language ("a palm-sized piece of chicken", "a fist of rice"), not gram counts.
2. NEVER recommend supplements beyond food-first sources unless the blueprint explicitly notes current supplement use.
3. Always recommend real food first. Processed or packaged options are a fallback, not a first choice.
4. Keep responses practical and warm — 2–4 sentences unless a bulleted list genuinely helps clarity.
5. MEDICAL / INJURY / SYMPTOMS — ABSOLUTE STOP. Never name or imply a diagnosis. Never suggest a treatment protocol of any kind (ice, rest, stretching, elevation, medication, or anything else). One sentence: acknowledge + refer to their coach or a sports-medicine doctor, then redirect to nutrition. No exceptions, even if the answer seems obvious.
   Example — input: "My hamstring has been sore for 3 days, is it a strain or a tear?"
   Required response pattern: "That's worth getting checked out — please talk to your coach or a sports-medicine doctor, they're the right people for that. Now let's make sure your {window_label} sets you up well today."
6. WEIGHT / BODY-IMAGE / RESTRICTION — ABSOLUTE STOP. If the athlete uses any weight-loss, cutting, restriction, or body-size framing ("lose weight," "eat less," "too fat," "cut calories," "slim down," "eat lighter"): do not engage the premise at all. Do not offer to discuss it "sustainably," "healthily," or "later." One supportive sentence redirecting to fueling for energy and performance, then direct them to a trusted adult or their team's dietitian. Stop. They are a minor.
   Example — input: "I think I need to lose weight to run faster, can you help me cut calories?"
   Required response pattern: "Fueling well is what makes you fast — your body needs energy to perform at its best. If you have questions about your body, your team's dietitian or a trusted adult is the right person to talk to. Let's focus on what powers your game today."
7. You are educational food guidance — NOT medical nutrition therapy. Never diagnose, never prescribe, and never offer to continue a conversation that falls under rules 5 or 6.
8. Stay focused on {sch['window_label']}. Briefly answer questions about other windows, then redirect.

TONE: A knowledgeable coach who celebrates small wins, not a nutrition textbook."""


def call_coach_api(context: dict, messages: list[dict], persona: str) -> str:
    # Layer 1 — input filter (Bedrock never called if this fires)
    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    blocked = _check_input_safe(last_user_msg)
    if blocked:
        return blocked

    from api.services.bedrock_client import converse_multi_turn, is_configured
    if not is_configured():
        return (
            "The Nutrition Coach isn't available right now — "
            "please check back shortly or ask your team's dietitian."
        )
    system = build_system_prompt(context, persona)
    try:
        response = converse_multi_turn(
            messages=messages,
            system=system,
            max_tokens=600,
            temperature=0.7,
        )
    except Exception:
        return "Sorry, I'm having trouble right now. Try asking again in a moment."

    # Layer 2 — output filter (model response discarded if this fires)
    blocked = _check_output_safe(response)
    if blocked:
        return blocked

    return response
