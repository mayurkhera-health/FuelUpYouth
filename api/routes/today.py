from datetime import date as dt_date, timedelta
from fastapi import APIRouter, HTTPException
from api.database import get_conn
from api.services import nutrition_calc
from api.services.today_service import (
    compute_logged_totals,
    compute_traffic_light,
    calc_letter_grade,
    get_positive_rows,
    get_gap_rows,
    get_athlete_streak,
    get_urgent_action,
)

router = APIRouter()


@router.get("/{athlete_id}/daily-summary")
def get_daily_summary(athlete_id: int, date: str = None):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
        target_date = date or str(dt_date.today())

        events = [dict(e) for e in conn.execute(
            "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
            (athlete_id, target_date),
        ).fetchall()]
        event_type = events[0]["event_type"] if events else "rest"

        targets_row = conn.execute(
            "SELECT * FROM daily_targets WHERE athlete_id = ? AND target_date = ?",
            (athlete_id, target_date),
        ).fetchone()
        targets = dict(targets_row) if targets_row else nutrition_calc.calc_daily_targets(athlete, event_type)

        meal_rows = conn.execute(
            "SELECT * FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ? ORDER BY logged_at",
            (athlete_id, target_date),
        ).fetchall()
        meal_logs = [dict(m) for m in meal_rows]

        water_row = conn.execute(
            "SELECT cups FROM water_logs WHERE athlete_id = ? AND log_date = ?",
            (athlete_id, target_date),
        ).fetchone()
        water_cups = water_row["cups"] if water_row else 0

        logged = compute_logged_totals(meal_logs)
        logged["water_oz"] = round((logged.get("water_oz") or 0) + water_cups * 8, 1)

        tl = compute_traffic_light(targets, logged)
        score = tl["daily_fuel_score"]
        gender = athlete.get("gender", "boy")

        tomorrow = (dt_date.fromisoformat(target_date) + timedelta(days=1)).isoformat()
        tomorrow_row = conn.execute(
            "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time LIMIT 1",
            (athlete_id, tomorrow),
        ).fetchone()

        return {
            "athlete": {
                "first_name": athlete["first_name"],
                "gender": gender,
                "dietary_restrictions": athlete.get("dietary_restrictions"),
                "allergies": athlete.get("allergies"),
            },
            "date": target_date,
            "event_type": event_type,
            "events": events,
            "targets": targets,
            "logged": logged,
            "traffic_light": tl,
            "meal_logs": meal_logs,
            "letter_grade": calc_letter_grade(score),
            "positive_rows": get_positive_rows(tl, event_type, gender),
            "gap_rows": get_gap_rows(tl, gender, event_type),
            "urgent_action": get_urgent_action(events, tl, meal_logs),
            "streak": get_athlete_streak(athlete_id, conn),
            "tomorrow_event": dict(tomorrow_row) if tomorrow_row else None,
            "water_cups": water_cups,
            "lea_alert": targets.get("lea_alert", False),
        }
    finally:
        conn.close()


@router.get("/{athlete_id}/weekly-summary")
def get_weekly_summary(athlete_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)

        today = dt_date.today()
        week_start = today - timedelta(days=today.weekday())
        DAY_ABBR = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        week = []

        for i in range(7):
            d = week_start + timedelta(days=i)
            date_str = d.isoformat()

            targets_row = conn.execute(
                "SELECT * FROM daily_targets WHERE athlete_id = ? AND target_date = ?",
                (athlete_id, date_str),
            ).fetchone()
            event_row = conn.execute(
                "SELECT event_type FROM events WHERE athlete_id = ? AND event_date = ? LIMIT 1",
                (athlete_id, date_str),
            ).fetchone()
            meal_rows = conn.execute(
                "SELECT * FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ?",
                (athlete_id, date_str),
            ).fetchall()
            meal_logs = [dict(m) for m in meal_rows]

            score = None
            if targets_row and meal_logs:
                water_row = conn.execute(
                    "SELECT cups FROM water_logs WHERE athlete_id = ? AND log_date = ?",
                    (athlete_id, date_str),
                ).fetchone()
                water_cups = water_row["cups"] if water_row else 0
                logged = compute_logged_totals(meal_logs)
                logged["water_oz"] = round((logged.get("water_oz") or 0) + water_cups * 8, 1)
                tl = compute_traffic_light(dict(targets_row), logged)
                score = tl["daily_fuel_score"]

            week.append({
                "date": date_str,
                "day_abbr": DAY_ABBR[i],
                "day_num": d.day,
                "score": score,
                "event_type": event_row["event_type"] if event_row else None,
                "is_today": d == today,
            })

        scores = [d["score"] for d in week if d["score"] is not None]
        return {"week": week, "avg_score": round(sum(scores) / len(scores)) if scores else None}
    finally:
        conn.close()
