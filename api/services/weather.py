import os
import time

import requests


def derive_sweat_profile(athlete: dict) -> str:
    """Auto-derive sweat profile from age, gender, and competition level."""
    age = athlete.get("age") or 13
    gender = (athlete.get("gender") or "").lower()
    level = (athlete.get("competition_level") or athlete.get("level") or "").lower()

    # Base profile by age (children sweat less efficiently; puberty increases output)
    if age <= 11:
        profile = "light"
    elif age <= 13:
        profile = "moderate"
    elif age <= 15:
        profile = "heavy"
    else:
        profile = "heavy"

    # Post-puberty males (16-17) skew higher
    if age >= 16 and "boy" in gender:
        profile = "very heavy"

    # Elite/competitive athletes have higher sweat rates due to training adaptation
    if level in ("elite", "competitive"):
        bump = {"light": "moderate", "moderate": "heavy", "heavy": "very heavy", "very heavy": "very heavy"}
        profile = bump.get(profile, profile)

    return profile


_WEATHER_TTL_SECONDS = 1800  # 30 minutes
_weather_cache: dict[str, tuple[float, dict]] = {}  # city(lower) -> (fetched_at, result)


def _now() -> float:
    return time.monotonic()


def _fetch_weather(city: str) -> dict:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "No API key configured"}
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if resp.status_code != 200:
            return {"temp_f": None, "humidity": None, "description": "unknown", "error": data.get("message", "API error")}
        return {
            "temp_f": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "error": None,
        }
    except Exception as e:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": str(e)}


def get_weather(city: str) -> dict:
    """Cached weather lookup. Successful results are cached per city for the TTL;
    error results are never cached (so a transient failure self-heals next call).
    In-memory, per-process — correct for the single-VM deployment."""
    key = (city or "").strip().lower()
    cached = _weather_cache.get(key)
    if cached and (_now() - cached[0]) < _WEATHER_TTL_SECONDS:
        return cached[1]
    result = _fetch_weather(city)
    if not result.get("error"):
        _weather_cache[key] = (_now(), result)
    return result


def calc_sweat_output(athlete: dict, event: dict, weather: dict) -> dict:
    wt_kg = athlete["weight_lbs"] * 0.453592
    event_type = (event.get("event_type") or "").lower()

    if any(x in event_type for x in ["game", "tournament"]):
        base_rate = 1.2
    elif any(x in event_type for x in ["practice", "training", "strength"]):
        base_rate = 1.0
    else:
        base_rate = 0.5

    sweat_multipliers = {"light": 0.7, "moderate": 1.0, "heavy": 1.3, "very heavy": 1.6}
    profile_mult = sweat_multipliers.get(derive_sweat_profile(athlete), 1.0)

    temp_f = weather.get("temp_f")
    humidity = weather.get("humidity")
    temp_mult = 1.0
    humidity_mult = 1.0

    if temp_f:
        if temp_f > 95:
            temp_mult = 1.40
        elif temp_f > 85:
            temp_mult = 1.25
        elif temp_f > 75:
            temp_mult = 1.10

    if humidity:
        if humidity > 80:
            humidity_mult = 1.30
        elif humidity > 60:
            humidity_mult = 1.15

    duration = event.get("duration_hours") or 1.5
    sweat_rate = base_rate * profile_mult * temp_mult * humidity_mult
    total_loss_liters = sweat_rate * duration
    hydration_oz_during = int(total_loss_liters * 33.8)

    electrolytes_needed = False
    reasons = []

    if temp_f and temp_f > 80:
        electrolytes_needed = True
        reasons.append(f"Temperature {temp_f:.0f}°F")
    if humidity and humidity > 70:
        electrolytes_needed = True
        reasons.append(f"Humidity {humidity}%")
    if duration > 1.0:
        electrolytes_needed = True
        reasons.append(f"Event duration {duration}hrs")
    if "tournament" in event_type:
        electrolytes_needed = True
        reasons.append("Tournament day")
    if "strength" in event_type and duration > 0.75:
        electrolytes_needed = True
        reasons.append("Strength training")

    recommendations = []
    if electrolytes_needed:
        recommendations.append("Natural sports drink — NO artificial dyes (Red #40, Yellow #5, Yellow #6 linked to behavioral changes in adolescents — Everett MD 2025)")
        if temp_f and temp_f > 80:
            recommendations.append("Add a pinch of salt to your pre-event meal")
        if "tournament" in event_type:
            recommendations.append("Sodium + potassium priority between games")
    else:
        recommendations.append("Plain water is sufficient — no sports drink needed")
    recommendations.append("Drink 6-8oz every 20 minutes during activity")

    return {
        "sweat_loss_liters": round(total_loss_liters, 2),
        "hydration_oz_during": hydration_oz_during,
        "electrolytes_needed": electrolytes_needed,
        "electrolyte_reason": ", ".join(reasons) if reasons else None,
        "weather_temp_f": temp_f,
        "weather_humidity": humidity,
        "recommendations": recommendations,
    }
