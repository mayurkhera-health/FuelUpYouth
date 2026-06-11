from api.services.nutrition_analysis import (
    get_week_start,
    get_week_dates,
    calculate_weekly_traffic_light,
    rank_weekly_gaps,
)

GAP_TO_CAT = {
    "iron_mg": "iron",
    "calcium_mg": "calcium",
    "carbs_g": "carbs",
    "water_oz": "hydration",
}

EVENT_TO_CAT = {
    "game": "gameday",
    "tournament": "gameday",
    "strength": "recovery",
}


def generate_weekly_picks(athlete_id: int, conn) -> None:
    """Select up to 2 articles for the athlete based on current nutrient gaps."""
    week_start = get_week_start()

    existing = conn.execute("""
        SELECT COUNT(*) AS cnt FROM athlete_article_picks
        WHERE athlete_id = ? AND week_start = ?
    """, (athlete_id, week_start)).fetchone()
    if existing["cnt"] > 0:
        return

    athlete_row = conn.execute(
        "SELECT * FROM athletes WHERE id = ?", (athlete_id,)
    ).fetchone()
    if not athlete_row:
        return
    athlete = dict(athlete_row)
    gender = athlete.get("gender", "boy")

    week_dates = get_week_dates(week_start)
    weekly_tl = calculate_weekly_traffic_light(athlete_id, week_dates, conn)
    gaps = rank_weekly_gaps(weekly_tl, gender)

    next_event_row = conn.execute("""
        SELECT event_type FROM events
        WHERE athlete_id = ? AND event_date >= date('now')
        ORDER BY event_date ASC LIMIT 1
    """, (athlete_id,)).fetchone()

    selected = []
    used_cats = set()

    for gap in gaps[:2]:
        cat = GAP_TO_CAT.get(gap["nutrient"])
        if cat and cat not in used_cats:
            article = _get_unread_article(athlete_id, cat, conn)
            if article:
                reason = _build_reason(gap)
                selected.append((article, reason))
                used_cats.add(cat)

    if next_event_row and len(selected) < 2:
        cat = EVENT_TO_CAT.get(next_event_row["event_type"])
        if cat and cat not in used_cats:
            article = _get_unread_article(athlete_id, cat, conn)
            if article:
                reason = f"Upcoming {next_event_row['event_type']} — read this first"
                selected.append((article, reason))

    if not selected:
        row = conn.execute("""
            SELECT a.* FROM articles a WHERE a.is_active = 1
            AND a.id NOT IN (
                SELECT article_id FROM athlete_article_picks WHERE athlete_id = ?
            )
            ORDER BY a.published_date DESC LIMIT 1
        """, (athlete_id,)).fetchone()
        if row:
            selected.append((dict(row), "New this week — worth a read"))

    for article, reason in selected[:2]:
        conn.execute("""
            INSERT OR IGNORE INTO athlete_article_picks
                (athlete_id, article_id, week_start, alex_reason)
            VALUES (?, ?, ?, ?)
        """, (athlete_id, article["id"], week_start, reason))


def _build_reason(gap: dict) -> str:
    names = {
        "iron_mg": "iron", "calcium_mg": "calcium",
        "carbs_g": "carbs", "water_oz": "hydration",
    }
    name = names.get(gap["nutrient"], gap["nutrient"])
    days = gap.get("days_below", 0)
    logged = gap.get("days_logged", 1)
    return f"Because {name} has been low {days} of {logged} days this week"


def _get_unread_article(athlete_id: int, category: str, conn):
    row = conn.execute("""
        SELECT a.* FROM articles a
        WHERE a.category = ? AND a.is_active = 1
        AND a.id NOT IN (
            SELECT article_id FROM athlete_article_picks WHERE athlete_id = ?
        )
        ORDER BY a.published_date DESC LIMIT 1
    """, (category, athlete_id)).fetchone()
    return dict(row) if row else None
