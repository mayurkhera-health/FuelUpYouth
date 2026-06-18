"""Nutrition Coach — context assembly and AI call."""
import json

from api.database import get_conn
from api.services.weather import get_weather
from api.services.nutrition_calc import calc_daily_targets


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
5. If they ask about a medical condition, injury, or disordered eating pattern: acknowledge briefly and refer them to a registered sports dietitian or their physician.
6. You are educational food guidance — NOT medical nutrition therapy. Never diagnose or prescribe.
7. Stay focused on {sch['window_label']}. Briefly answer questions about other windows, then redirect.

TONE: A knowledgeable coach who celebrates small wins, not a nutrition textbook."""


def call_coach_api(context: dict, messages: list[dict], persona: str) -> str:
    from api.services.bedrock_client import converse_multi_turn, is_configured
    if not is_configured():
        return (
            "The Nutrition Coach isn't available right now — "
            "please check back shortly or ask your team's dietitian."
        )
    system = build_system_prompt(context, persona)
    try:
        return converse_multi_turn(
            messages=messages,
            system=system,
            max_tokens=600,
            temperature=0.7,
        )
    except Exception:
        return "Sorry, I'm having trouble right now. Try asking again in a moment."
