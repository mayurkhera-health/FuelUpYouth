import os
import time

import requests

from api.services.nutrition_calc import calc_age


def derive_sweat_profile(athlete: dict) -> str:
    """Auto-derive sweat profile from age, gender, and competition level."""
    age = int(calc_age(
        dob_str=athlete.get("date_of_birth"),
        age_fallback=athlete.get("age") or 13,
    ))
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

    # Elite/competitive athletes have higher sweat rates due to training adaptation.
    # Substring match tolerates both legacy values ("elite", "competitive") and the
    # current 3-level labels ("elite_club", "competitive_club").
    if "elite" in level or "competitive" in level:
        bump = {"light": "moderate", "moderate": "heavy", "heavy": "very heavy", "very heavy": "very heavy"}
        profile = bump.get(profile, profile)

    return profile


_WEATHER_TTL_SECONDS = 1800       # 30 minutes for successful results
_WEATHER_ERROR_TTL_SECONDS = 60   # 1 minute for error results (self-heals quickly)
_weather_cache: dict[str, tuple[float, dict]] = {}  # key -> (fetched_at, result)


def _now() -> float:
    return time.monotonic()


def _fetch_weather(city: str | None = None, lat: float | None = None, lon: float | None = None) -> dict:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "No API key configured"}
    # Prefer precise coordinates (venue lat/lon) over a coarse city-name query.
    if lat is not None and lon is not None:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
    elif city:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"
    else:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "No location provided"}
    try:
        resp = requests.get(url, timeout=3)
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


def get_weather(city: str | None = None, lat: float | None = None, lon: float | None = None) -> dict:
    """Cached weather lookup. Prefers precise coordinates (lat/lon) when BOTH are
    provided; otherwise falls back to a city-name query. Returns an error result if
    neither is given. Successful results are cached per location for the TTL; error
    results are never cached (so a transient failure self-heals next call).
    In-memory, per-process — correct for the single-VM deployment."""
    use_coords = lat is not None and lon is not None
    key = (
        f"coord:{round(float(lat), 3)},{round(float(lon), 3)}"
        if use_coords
        else (city or "").strip().lower()
    )
    if not key:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "No location provided"}
    cached = _weather_cache.get(key)
    if cached:
        ttl = _WEATHER_ERROR_TTL_SECONDS if cached[1].get("error") else _WEATHER_TTL_SECONDS
        if (_now() - cached[0]) < ttl:
            return cached[1]
    result = _fetch_weather(city=city, lat=lat, lon=lon)
    _weather_cache[key] = (_now(), result)  # cache both successes and errors
    return result


_GEOCODE_TTL_SECONDS = 86400  # a coordinate's city doesn't change — cache a full day
_geocode_cache: dict[str, tuple[float, str | None]] = {}


def reverse_geocode_city(lat: float, lon: float) -> str | None:
    """Coordinates -> a human-readable city string ("San Jose, CA"), for
    location-flavored search queries. Reuses OPENWEATHERMAP_API_KEY (already
    configured) via their free geocoding endpoint — no new vendor. Returns
    None on any failure; callers should degrade gracefully, not block on it."""
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return None

    key = f"{round(float(lat), 2)},{round(float(lon), 2)}"
    cached = _geocode_cache.get(key)
    if cached and (_now() - cached[0]) < _GEOCODE_TTL_SECONDS:
        return cached[1]

    try:
        resp = requests.get(
            "http://api.openweathermap.org/geo/1.0/reverse",
            params={"lat": lat, "lon": lon, "limit": 1, "appid": api_key},
            timeout=3,
        )
        data = resp.json()
        if resp.status_code != 200 or not data:
            _geocode_cache[key] = (_now(), None)
            return None
        place = data[0]
        name = place.get("name")
        state = place.get("state")
        city = f"{name}, {state}" if name and state else name
        _geocode_cache[key] = (_now(), city)
        return city
    except Exception:
        _geocode_cache[key] = (_now(), None)
        return None


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
