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
    calculate_performance_forecast,
    get_mission_items,
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
                "first_name":        athlete["first_name"],
                "last_name":         athlete.get("last_name"),
                "gender":            gender,
                "position":          athlete.get("position"),
                "competition_level": athlete.get("competition_level"),
                "jersey_number":     athlete.get("jersey_number"),
                "team_name":         athlete.get("team_name"),
                "dietary_restrictions": athlete.get("dietary_restrictions"),
                "allergies":         athlete.get("allergies"),
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
            "performance_forecast": calculate_performance_forecast(tl),
            "mission_items": get_mission_items(event_type, events, tl, meal_logs, targets, water_cups, gender),
        }
    finally:
        conn.close()


@router.get("/{athlete_id}/weekly-summary")
def get_weekly_summary(athlete_id: int, week_start: str = None):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
        gender = athlete.get("gender", "boy")

        from api.services.nutrition_analysis import (
            get_week_start, get_week_dates, build_heatmap,
            calculate_weekly_traffic_light, rank_weekly_gaps, build_wins_list,
        )

        resolved_week_start = week_start or get_week_start()
        week_dates = get_week_dates(resolved_week_start)
        today_str = str(dt_date.today())
        DAY_ABBR = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

        week = []
        for i, date_str in enumerate(week_dates):
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
                "day_num": dt_date.fromisoformat(date_str).day,
                "score": score,
                "event_type": event_row["event_type"] if event_row else None,
                "is_today": date_str == today_str,
            })

        scores = [d["score"] for d in week if d["score"] is not None]
        week_fuel_score = round(sum(scores) / len(scores)) if scores else 0
        days_logged = len(scores)

        heatmap = build_heatmap(athlete_id, week_dates, conn)
        weekly_tl = calculate_weekly_traffic_light(athlete_id, week_dates, conn)
        ranked_gaps = rank_weekly_gaps(weekly_tl, gender)
        streak = get_athlete_streak(athlete_id, conn)
        wins = build_wins_list(weekly_tl, streak, athlete["first_name"])

        prev_start_date = dt_date.fromisoformat(resolved_week_start) - timedelta(days=7)
        prev_dates = [(prev_start_date + timedelta(days=i)).isoformat() for i in range(7)]
        prev_scores = []
        for date_str in prev_dates:
            t_row = conn.execute(
                "SELECT * FROM daily_targets WHERE athlete_id = ? AND target_date = ?",
                (athlete_id, date_str),
            ).fetchone()
            m_rows = conn.execute(
                "SELECT * FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ?",
                (athlete_id, date_str),
            ).fetchall()
            if t_row and m_rows:
                lg = compute_logged_totals([dict(m) for m in m_rows])
                tl = compute_traffic_light(dict(t_row), lg)
                prev_scores.append(tl["daily_fuel_score"])
        prev_week_score = round(sum(prev_scores) / len(prev_scores)) if prev_scores else None

        return {
            "week_start": resolved_week_start,
            "week_end": week_dates[-1],
            "days_logged": days_logged,
            "week_fuel_score": week_fuel_score,
            "prev_week_score": prev_week_score,
            "days": week,
            "heatmap": heatmap,
            "weekly_traffic_light": weekly_tl,
            "ranked_gaps": ranked_gaps,
            "wins": wins,
            "streak": streak,
            "letter_grade": calc_letter_grade(week_fuel_score),
        }
    finally:
        conn.close()
