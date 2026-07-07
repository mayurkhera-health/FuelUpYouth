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


def next_rank_threshold(score: int) -> int | None:
    """Score needed for the next rank tier, or None at the top (Pro)."""
    higher = sorted((t for t, _ in _RANK_BANDS if t > score))
    return higher[0] if higher else None


def _config_value(conn, key: str, default: float) -> float:
    row = conn.execute("SELECT value FROM report_config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


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
        "next_rank_threshold": next_rank_threshold(row["score"]),
        "current_streak": row["current_streak"],
        "best_streak": row["best_streak"],
        "freeze_tokens": row["freeze_tokens"],
        "last_activity_date": row["last_activity_date"],
    }


_PLACEHOLDER_LESSONS = [
    # (title, hook, fact_body, takeaway, questions) — EXAMPLE content for local
    # testing of the full lesson+quiz flow ONLY. NOT RDN-approved copy (spec
    # §11.1) — review_status stays 'draft' until a dietitian signs off; do not
    # flip to 'approved' as part of a content seed.
    #
    # questions: (question_text, option_a, option_b, option_c, correct_option,
    #             explanation, misconception_tag)
    (
        "Carbs Are Not the Enemy",
        "Your legs died in the 2nd half. Here's why.",
        "Carbs are stored in your muscles as glycogen — your body's fastest "
        "fuel source during exercise. When glycogen runs low, your legs feel "
        "heavy and slow, even if you're not tired everywhere else. That's "
        "called 'bonking,' and it has nothing to do with willpower.",
        "Rice, roti, pasta, oats — that's fuel, not cheat food.",
        [
            (
                "Your legs feel dead in the second half — most likely reason?",
                "You didn't eat enough protein", "You ran out of stored carbs (glycogen)",
                "You didn't stretch enough", "b",
                "Glycogen (stored carbs) fuels your muscles during exercise. When it "
                "runs low, your legs feel heavy and slow — that's 'bonking.'",
                "protein_fixes_everything",
            ),
            (
                "Which of these is a good pre-game carb source?",
                "Rice, pasta, or oats", "A plain protein shake",
                "Skipping the meal to feel lighter", "a",
                "Carbs are your body's fastest fuel source — rice, pasta, and oats "
                "top off your glycogen stores before you play.",
                "carbs_make_you_slow",
            ),
            (
                "True or false: eating carbs before a game makes you feel sluggish.",
                "True", "False", "Only if you eat too much", "b",
                "The right amount of carbs before a game gives you energy, not "
                "sluggishness — that myth keeps athletes underfueled.",
                "carbs_make_you_sluggish",
            ),
        ],
    ),
    (
        "The Palm & Fist Rule",
        "How much protein actually fits on your plate?",
        "You don't need a food scale to build a solid plate. A palm-sized "
        "portion of protein (chicken, fish, beans) plus a fist-sized portion "
        "of carbs (rice, potatoes, pasta) covers most meals — no measuring, "
        "no counting.",
        "One palm of protein, one fist of carbs, every meal — no scale required.",
        [
            (
                "Using the Palm & Fist Rule, how much protein fits on your plate?",
                "A portion the size of your palm", "As much as you can fit",
                "Half a protein shake", "a",
                "A palm-sized portion of protein is enough to support muscle "
                "recovery at most meals.",
                "more_protein_is_always_better",
            ),
            (
                "What does the 'fist' in Palm & Fist represent?",
                "Protein", "Carbs (like rice or potatoes)", "Vegetables", "b",
                "A fist-sized portion of carbs — rice, potatoes, pasta — fuels "
                "your muscles for the next practice or game.",
                "carbs_should_be_minimized",
            ),
            (
                "Why is a simple portion guide like Palm & Fist useful for athletes?",
                "It requires a food scale",
                "It gives a quick, no-measuring way to build a balanced plate",
                "It only works for adults", "b",
                "You don't need to weigh or count anything — your hand is a "
                "portion guide you always have with you.",
                "need_precise_tracking",
            ),
        ],
    ),
]

_PLACEHOLDER_MYTH = (
    "Skip Breakfast to Get Lighter/Faster",
    "PLACEHOLDER HOOK — Some athletes skip breakfast to feel lighter on game day.",
    "myth",
    "PLACEHOLDER SCIENCE — structural placeholder pending RDN-authored copy.",
)


def seed_placeholder_content(conn) -> None:
    """Local-dev-only seed: enough draft content — including a full 3-question
    quiz per lesson — to exercise the hub/lesson/myth screens end to end
    before real RDN-authored lessons exist. Never call this against a
    production DB — placeholder copy must never be athlete-visible there."""
    for order_in_level, (title, hook, fact_body, takeaway, questions) in enumerate(
        _PLACEHOLDER_LESSONS, start=1
    ):
        exists = conn.execute(
            "SELECT 1 FROM fueliq_lessons WHERE title = ?", (title,)
        ).fetchone()
        if exists:
            continue
        lesson_id = conn.execute(
            "INSERT INTO fueliq_lessons "
            "(level, order_in_level, is_myth, title, hook, fact_body, takeaway, "
            " source_citation, review_status) "
            "VALUES (1, ?, 0, ?, ?, ?, ?, 'EXAMPLE — no citation yet', 'draft')",
            (order_in_level, title, hook, fact_body, takeaway),
        ).lastrowid
        for q_order, (q_text, opt_a, opt_b, opt_c, correct, explanation, tag) in enumerate(
            questions, start=1
        ):
            conn.execute(
                "INSERT INTO fueliq_questions "
                "(lesson_id, question_text, option_a, option_b, option_c, correct_option, "
                " explanation, misconception_tag, order_in_lesson) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (lesson_id, q_text, opt_a, opt_b, opt_c, correct, explanation, tag, q_order),
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


def _award_points(athlete_id: int, points: int, conn) -> None:
    """Score is earned-never-lost — always additive, never set/decremented."""
    _ensure_progress_row(athlete_id, conn)
    conn.execute(
        "UPDATE fueliq_athlete_progress SET score = score + ?, updated_at = datetime('now') "
        "WHERE athlete_id = ?",
        (points, athlete_id),
    )
    conn.commit()


def complete_lesson(athlete_id: int, lesson_id: int, conn, perfect_quiz: bool = False) -> dict:
    """Write path for finishing a lesson's reward screen. Idempotent per
    (athlete_id, lesson_id) — replaying a completion (e.g. a retried request)
    never double-awards points."""
    existing = conn.execute(
        "SELECT 1 FROM fueliq_lesson_completions WHERE athlete_id = ? AND lesson_id = ?",
        (athlete_id, lesson_id),
    ).fetchone()
    if existing:
        return {
            "already_completed": True,
            "points_earned": 0,
            "progress": get_progress(athlete_id, conn),
            "newly_earned_badges": [],
        }

    lesson_points = int(
        conn.execute("SELECT points FROM fueliq_lessons WHERE id = ?", (lesson_id,)).fetchone()["points"]
    )
    points_earned = lesson_points
    if perfect_quiz:
        points_earned += int(_config_value(conn, "fueliq_perfect_quiz_bonus", 5))

    conn.execute(
        "INSERT INTO fueliq_lesson_completions (athlete_id, lesson_id, perfect_quiz, points_earned) "
        "VALUES (?, ?, ?, ?)",
        (athlete_id, lesson_id, int(perfect_quiz), points_earned),
    )
    conn.commit()
    _award_points(athlete_id, points_earned, conn)
    from api.services import fueliq_streak  # local import — avoids a circular import
    streak = fueliq_streak.register_activity(athlete_id, conn)
    return {
        "already_completed": False,
        "points_earned": points_earned,
        "progress": get_progress(athlete_id, conn),
        "newly_earned_badges": check_and_award_badges(athlete_id, conn),
        "streak": streak,
    }


def submit_myth_verdict(athlete_id: int, lesson_id: int, guess: str, conn) -> dict:
    """Write path for a Myth Buster REAL/MYTH tap. Points are awarded for
    completing the myth, correct or not (spec §3.5 — failure must be cheap),
    and only once per athlete per myth."""
    existing = conn.execute(
        "SELECT correct FROM fueliq_myth_verdicts WHERE athlete_id = ? AND lesson_id = ?",
        (athlete_id, lesson_id),
    ).fetchone()
    if existing:
        return {
            "already_answered": True,
            "correct": bool(existing["correct"]),
            "points_earned": 0,
            "progress": get_progress(athlete_id, conn),
            "newly_earned_badges": [],
        }

    lesson = conn.execute(
        "SELECT verdict, science_text FROM fueliq_lessons WHERE id = ?", (lesson_id,)
    ).fetchone()
    correct = guess == lesson["verdict"]
    points_earned = int(_config_value(conn, "fueliq_myth_points", 10))

    conn.execute(
        "INSERT INTO fueliq_myth_verdicts (athlete_id, lesson_id, guess, correct) VALUES (?, ?, ?, ?)",
        (athlete_id, lesson_id, guess, int(correct)),
    )
    conn.commit()
    _award_points(athlete_id, points_earned, conn)
    from api.services import fueliq_streak  # local import — avoids a circular import
    streak = fueliq_streak.register_activity(athlete_id, conn)
    return {
        "already_answered": False,
        "correct": correct,
        "science_text": lesson["science_text"],
        "points_earned": points_earned,
        "progress": get_progress(athlete_id, conn),
        "newly_earned_badges": check_and_award_badges(athlete_id, conn),
        "streak": streak,
    }


def submit_quiz_answer(athlete_id: int, question_id: int, selected_option: str, conn) -> dict:
    """Write path for a single quiz question. No score effect — quiz answers
    only unlock the lesson-complete points via `perfect_quiz`; wrong answers
    are logged for the misconception-tag analytics (spec §6.3), never penalized."""
    question = conn.execute(
        "SELECT correct_option, explanation, misconception_tag FROM fueliq_questions WHERE id = ?",
        (question_id,),
    ).fetchone()
    correct = selected_option == question["correct_option"]
    conn.execute(
        "INSERT INTO fueliq_quiz_attempts "
        "(athlete_id, question_id, selected_option, correct, misconception_tag) "
        "VALUES (?, ?, ?, ?, ?)",
        (athlete_id, question_id, selected_option, int(correct), question["misconception_tag"]),
    )
    conn.commit()
    return {
        "correct": correct,
        "explanation": question["explanation"],
        "misconception_tag": question["misconception_tag"],
    }


# ── Badges (spec §7.1) ───────────────────────────────────────────────────────
# Collect-don't-grind: small, permanent set. Earned-never-lost, same as score.

def _has_first_whistle(athlete_id: int, conn) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_lesson_completions WHERE athlete_id = ?",
        (athlete_id,),
    ).fetchone()
    return row["c"] >= 1


def _has_hydration_hero(athlete_id: int, conn) -> bool:
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_lessons "
        "WHERE is_myth = 0 AND review_status = 'approved' AND category = 'hydration'"
    ).fetchone()["c"]
    if total == 0:
        return False
    done = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_lesson_completions lc "
        "JOIN fueliq_lessons l ON l.id = lc.lesson_id "
        "WHERE lc.athlete_id = ? AND l.category = 'hydration'",
        (athlete_id,),
    ).fetchone()["c"]
    return done >= total


def _has_myth_slayer(athlete_id: int, conn) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_myth_verdicts WHERE athlete_id = ?",
        (athlete_id,),
    ).fetchone()
    return row["c"] >= 5


def _has_perfect_week(athlete_id: int, conn) -> bool:
    row = conn.execute(
        "SELECT best_streak FROM fueliq_athlete_progress WHERE athlete_id = ?",
        (athlete_id,),
    ).fetchone()
    return bool(row) and row["best_streak"] >= 7


def _level_complete(athlete_id: int, level: int, conn) -> bool:
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_lessons WHERE is_myth = 0 AND review_status = 'approved' AND level = ?",
        (level,),
    ).fetchone()["c"]
    if total == 0:
        return False
    done = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_lesson_completions lc "
        "JOIN fueliq_lessons l ON l.id = lc.lesson_id "
        "WHERE lc.athlete_id = ? AND l.level = ?",
        (athlete_id, level),
    ).fetchone()["c"]
    return done >= total


def _has_game_day_ready(athlete_id: int, conn) -> bool:
    return _level_complete(athlete_id, 2, conn)


def _has_full_tank(athlete_id: int, conn) -> bool:
    for level in _LEVEL_THRESHOLDS:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM fueliq_lessons WHERE is_myth = 0 AND review_status = 'approved' AND level = ?",
            (level,),
        ).fetchone()["c"]
        if total == 0:
            continue
        perfect = conn.execute(
            "SELECT COUNT(*) AS c FROM fueliq_lesson_completions lc "
            "JOIN fueliq_lessons l ON l.id = lc.lesson_id "
            "WHERE lc.athlete_id = ? AND l.level = ? AND lc.perfect_quiz = 1",
            (athlete_id, level),
        ).fetchone()["c"]
        if perfect >= total:
            return True
    return False


def _has_team_player(athlete_id: int, conn) -> bool:
    """Team Challenges are Post-MVP (spec §12) — no data source exists yet, so
    this badge is defined but permanently unearnable until that feature ships."""
    return False


BADGE_CHECKS = {
    "first_whistle": _has_first_whistle,
    "hydration_hero": _has_hydration_hero,
    "myth_slayer": _has_myth_slayer,
    "perfect_week": _has_perfect_week,
    "game_day_ready": _has_game_day_ready,
    "full_tank": _has_full_tank,
    "team_player": _has_team_player,
}

# Display metadata for the Badge Gallery — order matches spec §7.1.
BADGE_DEFINITIONS = [
    {"key": "first_whistle", "name": "First Whistle", "hint": "Complete your first lesson"},
    {"key": "hydration_hero", "name": "Hydration Hero", "hint": "Complete all water lessons"},
    {"key": "myth_slayer", "name": "Myth Slayer", "hint": "Bust 5 myths"},
    {"key": "perfect_week", "name": "Perfect Week", "hint": "Hit a 7-day streak"},
    {"key": "game_day_ready", "name": "Game Day Ready", "hint": "Complete Level 2"},
    {"key": "team_player", "name": "Team Player", "hint": "Complete your first Team Challenge"},
    {"key": "full_tank", "name": "Full Tank", "hint": "100% of a level with perfect quizzes"},
]


def list_badges(athlete_id: int, conn) -> list[dict]:
    """Badge Gallery read path — every defined badge, earned or locked."""
    earned_at = {
        r["badge_key"]: r["earned_at"]
        for r in conn.execute(
            "SELECT badge_key, earned_at FROM fueliq_badges_earned WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchall()
    }
    return [
        {**b, "earned": b["key"] in earned_at, "earned_at": earned_at.get(b["key"])}
        for b in BADGE_DEFINITIONS
    ]


def check_and_award_badges(athlete_id: int, conn) -> list[str]:
    """Runs every badge check and awards any newly-qualifying badge. Idempotent
    — a badge already in fueliq_badges_earned is never re-awarded or re-returned."""
    already = {
        r["badge_key"]
        for r in conn.execute(
            "SELECT badge_key FROM fueliq_badges_earned WHERE athlete_id = ?", (athlete_id,)
        ).fetchall()
    }
    newly_earned = [
        key for key, check in BADGE_CHECKS.items() if key not in already and check(athlete_id, conn)
    ]
    for key in newly_earned:
        conn.execute(
            "INSERT OR IGNORE INTO fueliq_badges_earned (athlete_id, badge_key) VALUES (?, ?)",
            (athlete_id, key),
        )
    if newly_earned:
        conn.commit()
    return newly_earned


DEFAULT_MIN_COHORT = 5


def compute_percentile(athlete_id: int, conn, min_cohort: int = DEFAULT_MIN_COHORT) -> dict:
    """Solo-athlete percentile vs. anonymized same-age cohort (spec §7.2,
    §12). With a small early user base, "beats 72% of 16-year-olds" is
    numerically absurd for a cohort of 1 or 2 — suppress the percentile
    below `min_cohort` and report insufficient_data instead of a misleading
    number. An athlete with no fueliq_athlete_progress row hasn't engaged
    yet and counts at the Rookie baseline (50), not as absent — otherwise a
    cohort of mostly-unengaged peers would inflate everyone's percentile."""
    row = conn.execute("SELECT age FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
    if not row or row["age"] is None:
        return {"percentile": None, "cohort_size": 0, "insufficient_data": True}

    age = row["age"]
    cohort_ids = [r["id"] for r in conn.execute("SELECT id FROM athletes WHERE age = ?", (age,)).fetchall()]
    scores = {}
    for aid in cohort_ids:
        prog = conn.execute(
            "SELECT score FROM fueliq_athlete_progress WHERE athlete_id = ?", (aid,)
        ).fetchone()
        scores[aid] = prog["score"] if prog else 50
    cohort_size = len(scores)

    if cohort_size < min_cohort:
        return {"percentile": None, "cohort_size": cohort_size, "insufficient_data": True}

    my_score = scores[athlete_id]
    beaten = sum(1 for s in scores.values() if s < my_score)
    percentile = round(100 * beaten / (cohort_size - 1)) if cohort_size > 1 else 100
    return {"percentile": percentile, "cohort_size": cohort_size, "insufficient_data": False}
