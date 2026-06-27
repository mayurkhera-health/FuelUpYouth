"""
Deterministic test-data seeder for local/manual testing.

Solves the "which email is the parent and which is the athlete?" problem by
creating a fixed, role-named world every time you run it. The role is encoded
in the email itself via Gmail "+" aliasing, so a single inbox receives every
OTP while each alias is a distinct account to the app.

Usage
-----
    source venv/bin/activate
    python db/seed_test.py                       # uses SEED_EMAIL_BASE or the default below
    python db/seed_test.py --base you@gmail.com  # route every persona to your inbox
    SEED_EMAIL_BASE=you@gmail.com python db/seed_test.py

What you get (base = you@gmail.com)
-----------------------------------
    you+parent1@gmail.com    PARENT   -> sees 2 athletes (Alex, Sam)
    you+athlete1@gmail.com   ATHLETE  -> Alex   (has own login)
    (Sam has NO login)       --       -> only reachable via parent1
    you+parent2@gmail.com    PARENT   -> sees 1 athlete (Jordan) — isolation family
    you+athlete2@gmail.com   ATHLETE  -> Jordan (has own login)

The seeder is idempotent: it deletes any prior seed personas (matched by these
exact emails) and recreates them. It only touches seeded rows — your real data
and the test@gmail.com account are left alone.

Notes
-----
- Parents are created with consent_confirmed = TRUE, so athlete creation is
  allowed without the consent dance.
- No AI blueprints are generated (no LLM calls) — rows are inserted directly.
- In dev, login OTP codes are printed to the uvicorn console, so a placeholder
  base still works for clicking through the app. Use a real Gmail base only if
  you want to receive codes by email.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make the project root importable when run as `python db/seed_test.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.setup import init_db
from api.database import get_conn

try:
    # Apply runtime migrations (season_phase, coach_feedback, etc.) if available.
    from api.services.db_migrations import run_all as _run_migrations
except Exception:  # pragma: no cover - migrations module optional
    _run_migrations = None

DEFAULT_BASE = os.getenv("SEED_EMAIL_BASE", "test+seed@gmail.com")


def _alias(base: str, tag: str) -> str:
    """Turn `you@gmail.com` + `parent1` into `you+parent1@gmail.com`."""
    local, _, domain = base.partition("@")
    if not domain:
        raise SystemExit(f"--base must be a full email address, got: {base!r}")
    # Strip any existing +tag on the base so re-runs with `you+x@gmail.com` work.
    local = local.split("+", 1)[0]
    return f"{local}+{tag}@{domain}"


def _wipe(conn, emails: list[str]) -> None:
    """Delete seed parents (and their athletes + child rows) by email."""
    for email in emails:
        row = conn.execute("SELECT id FROM parents WHERE lower(email) = lower(?)", (email,)).fetchone()
        if not row:
            continue
        parent_id = row["id"]
        athlete_ids = [
            r["id"] for r in conn.execute("SELECT id FROM athletes WHERE parent_id = ?", (parent_id,)).fetchall()
        ]
        for aid in athlete_ids:
            conn.execute("DELETE FROM athlete_logins WHERE athlete_id = ?", (aid,))
            conn.execute("DELETE FROM events WHERE athlete_id = ?", (aid,))
            conn.execute("DELETE FROM meal_logs WHERE athlete_id = ?", (aid,))
            conn.execute("DELETE FROM daily_targets WHERE athlete_id = ?", (aid,))
        conn.execute("DELETE FROM athletes WHERE parent_id = ?", (parent_id,))
        conn.execute("DELETE FROM parents WHERE id = ?", (parent_id,))
    conn.commit()


def _add_parent(conn, full_name: str, email: str) -> int:
    ts = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO parents (full_name, email, consent_timestamp, consent_confirmed) VALUES (?, ?, ?, 1)",
        (full_name, email.lower(), ts),
    )
    conn.commit()
    return cur.lastrowid


def _add_athlete(conn, parent_id: int, **fields) -> int:
    cur = conn.execute(
        """INSERT INTO athletes
           (parent_id, first_name, age, gender, weight_lbs, height_ft, height_in,
            position, competition_level, sweat_profile)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            parent_id,
            fields["first_name"],
            fields["age"],
            fields["gender"],
            fields["weight_lbs"],
            fields["height_ft"],
            fields["height_in"],
            fields.get("position"),
            fields.get("competition_level", "competitive_club"),
            fields.get("sweat_profile", "Moderate"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _add_athlete_login(conn, athlete_id: int, email: str) -> None:
    conn.execute(
        "INSERT INTO athlete_logins (email, athlete_id) VALUES (?, ?)",
        (email.lower(), athlete_id),
    )
    conn.commit()


def _add_event(conn, athlete_id: int, name: str, etype: str, days_out: int, start_time: str, hours: float, city: str) -> None:
    event_date = (datetime.now() + timedelta(days=days_out)).strftime("%Y-%m-%d")
    conn.execute(
        """INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours, city)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (athlete_id, name, etype, event_date, start_time, hours, city),
    )
    conn.commit()


def seed(base: str) -> list[dict]:
    parent1_email = _alias(base, "parent1")
    athlete1_email = _alias(base, "athlete1")
    parent2_email = _alias(base, "parent2")
    athlete2_email = _alias(base, "athlete2")

    conn = get_conn()
    try:
        _wipe(conn, [parent1_email, parent2_email])

        # --- Family 1: parent with two athletes (one has a login, one does not) ---
        p1 = _add_parent(conn, "Parent One", parent1_email)
        alex = _add_athlete(
            conn, p1, first_name="Alex", age=14, gender="Boy",
            weight_lbs=120, height_ft=5, height_in=6, position="Midfielder",
        )
        _add_athlete_login(conn, alex, athlete1_email)
        sam = _add_athlete(
            conn, p1, first_name="Sam", age=11, gender="Girl",
            weight_lbs=85, height_ft=4, height_in=10, position="Forward",
        )
        _add_event(conn, alex, "League Game vs Rivals", "game", 1, "10:00", 1.5, "San Jose, CA")
        _add_event(conn, alex, "Club Tournament", "tournament", 4, "08:30", 6.0, "Sacramento, CA")

        # --- Family 2: isolation check — separate parent, separate athlete ---
        p2 = _add_parent(conn, "Parent Two", parent2_email)
        jordan = _add_athlete(
            conn, p2, first_name="Jordan", age=16, gender="Girl",
            weight_lbs=135, height_ft=5, height_in=7, position="Defender",
        )
        _add_athlete_login(conn, jordan, athlete2_email)

        return [
            {"email": parent1_email, "role": "PARENT", "name": "Parent One", "sees": "Alex (login) + Sam (no login)"},
            {"email": athlete1_email, "role": "ATHLETE", "name": "Alex", "sees": "self only — child of parent1"},
            {"email": "(none)", "role": "—", "name": "Sam", "sees": "no login; reach via parent1"},
            {"email": parent2_email, "role": "PARENT", "name": "Parent Two", "sees": "Jordan (login)"},
            {"email": athlete2_email, "role": "ATHLETE", "name": "Jordan", "sees": "self only — child of parent2"},
        ]
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed deterministic test accounts.")
    ap.add_argument("--base", default=DEFAULT_BASE,
                    help="Base email; personas become base+parent1@, base+athlete1@, etc. "
                         f"(default: {DEFAULT_BASE})")
    args = ap.parse_args()

    init_db()
    if _run_migrations:
        _run_migrations()

    rows = seed(args.base)

    width = max(len(r["email"]) for r in rows) + 2
    print("\nSeeded test accounts (passwordless email login):\n")
    print(f"  {'EMAIL'.ljust(width)}{'ROLE'.ljust(9)}{'NAME'.ljust(14)}WHAT THEY SEE")
    print(f"  {'-' * (width - 1)} {'-' * 7}  {'-' * 12} {'-' * 30}")
    for r in rows:
        print(f"  {r['email'].ljust(width)}{r['role'].ljust(9)}{r['name'].ljust(14)}{r['sees']}")
    print("\n  Tip: log in with the +parentN alias to act as a parent, +athleteN to act as that kid.")
    print("  In dev, OTP codes are printed to the uvicorn console.\n")


if __name__ == "__main__":
    main()
