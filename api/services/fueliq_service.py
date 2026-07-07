"""
Fuel IQ — gamified nutrition-education engine.

Score is earned-never-lost (no decay, no penalties — spec §5.1). Rank and
level-unlock are pure functions of score, derived on every read, the same way
streak_service never caches a derived value. `fueliq_athlete_progress` stores
only the non-derivable state (raw score, streak counters, freeze tokens).
"""

import os

_RANK_BANDS = [
    (550, "Pro"),
    (350, "Captain"),
    (200, "Varsity"),
    (100, "Starter"),
    (0, "Rookie"),
]

_LEVEL_THRESHOLDS = {1: 0, 2: 100, 3: 200, 4: 300}


def fueliq_enabled() -> bool:
    return os.environ.get("FUELIQ_ENABLED", "false").lower() == "true"


def rank_for_score(score: int) -> str:
    for threshold, rank in _RANK_BANDS:
        if score >= threshold:
            return rank
    return "Rookie"


def level_unlocked(score: int, level: int) -> bool:
    return score >= _LEVEL_THRESHOLDS[level]


def _ensure_progress_row(athlete_id: int, conn) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO fueliq_athlete_progress (athlete_id) VALUES (?)",
        (athlete_id,),
    )
    conn.commit()


def get_progress(athlete_id: int, conn) -> dict:
    """Read-path progress block for the Fuel IQ hub. Creates a default row
    (score 50, 'Rookie baseline') on an athlete's first-ever read."""
    _ensure_progress_row(athlete_id, conn)
    row = conn.execute(
        "SELECT score, current_streak, best_streak, freeze_tokens, last_activity_date "
        "FROM fueliq_athlete_progress WHERE athlete_id = ?",
        (athlete_id,),
    ).fetchone()
    return {
        "score": row["score"],
        "rank": rank_for_score(row["score"]),
        "current_streak": row["current_streak"],
        "best_streak": row["best_streak"],
        "freeze_tokens": row["freeze_tokens"],
        "last_activity_date": row["last_activity_date"],
    }


_PLACEHOLDER_LESSONS = [
    # (title, hook, fact_body, takeaway) — structural placeholders ONLY.
    # NOT RDN-approved copy (spec §11.1) — review_status stays 'draft' until a
    # dietitian signs off; do not flip to 'approved' as part of a content seed.
    (
        "Carbs Are Not the Enemy",
        "PLACEHOLDER HOOK — Your legs died in the 2nd half. Here's why.",
        "PLACEHOLDER FACT BODY — structural placeholder pending RDN-authored copy.",
        "PLACEHOLDER TAKEAWAY — structural placeholder pending RDN-authored copy.",
    ),
    (
        "The Palm & Fist Rule",
        "PLACEHOLDER HOOK — How much protein actually fits on your plate?",
        "PLACEHOLDER FACT BODY — structural placeholder pending RDN-authored copy.",
        "PLACEHOLDER TAKEAWAY — structural placeholder pending RDN-authored copy.",
    ),
]

_PLACEHOLDER_MYTH = (
    "Skip Breakfast to Get Lighter/Faster",
    "PLACEHOLDER HOOK — Some athletes skip breakfast to feel lighter on game day.",
    "myth",
    "PLACEHOLDER SCIENCE — structural placeholder pending RDN-authored copy.",
)


def seed_placeholder_content(conn) -> None:
    """Local-dev-only seed: enough draft content to exercise the hub/lesson/myth
    screens before real RDN-authored lessons exist. Never call this against a
    production DB — placeholder copy must never be athlete-visible there."""
    for title, hook, fact_body, takeaway in _PLACEHOLDER_LESSONS:
        exists = conn.execute(
            "SELECT 1 FROM fueliq_lessons WHERE title = ?", (title,)
        ).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO fueliq_lessons "
            "(level, order_in_level, is_myth, title, hook, fact_body, takeaway, "
            " source_citation, review_status) "
            "VALUES (1, 1, 0, ?, ?, ?, ?, 'PLACEHOLDER — no citation yet', 'draft')",
            (title, hook, fact_body, takeaway),
        )

    myth_title, myth_hook, verdict, science_text = _PLACEHOLDER_MYTH
    exists = conn.execute(
        "SELECT 1 FROM fueliq_lessons WHERE title = ?", (myth_title,)
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO fueliq_lessons "
            "(level, order_in_level, is_myth, title, hook, verdict, science_text, "
            " source_citation, review_status) "
            "VALUES (4, 1, 1, ?, ?, ?, ?, 'PLACEHOLDER — no citation yet', 'draft')",
            (myth_title, myth_hook, verdict, science_text),
        )
    conn.commit()
