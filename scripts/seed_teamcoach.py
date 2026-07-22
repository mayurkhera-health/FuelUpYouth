#!/usr/bin/env python3
"""
Seed TeamCoach dashboard with demo data for local testing.

Usage:
    python scripts/seed_teamcoach.py

Creates:
  - 1 coach account: coach@demo.com / Demo1234!
  - 1 team: "U16 Girls Demo", season "Fall 2026", threshold 80%
  - Coach gets access to the team
  - First 6 athletes in the DB added to roster (consent_flag=1)
  - 3 weeks of fueling_window_log with varied completion rates
  - Snapshots generated for all 3 weeks

Safe to re-run: INSERT OR IGNORE throughout.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("DB_PATH", str(Path(__file__).parent.parent / "fuelup.db"))

from api.database import get_conn
from api.services.teamcoach_auth_service import hash_password
from api.services.snapshot_job import generate_snapshot
from datetime import date, timedelta

COACH_EMAIL = "coach@demo.com"
COACH_PASSWORD = "Demo1234!"
TEAM_NAME = "U16 Girls Demo"
TEAM_SEASON = "Fall 2026"
SLOTS = ["everyday", "fuel_before", "top_up", "during", "recharge", "rebuild"]
RATES = [1.0, 0.833, 0.667, 0.500, 0.333, 0.167]


def main():
    conn = get_conn()

    pw_hash, salt = hash_password(COACH_PASSWORD)
    conn.execute(
        "INSERT OR IGNORE INTO coaches (name,email,password_hash,salt) VALUES (?,?,?,?)",
        ("Demo Coach", COACH_EMAIL, pw_hash, salt),
    )
    coach_id = conn.execute(
        "SELECT id FROM coaches WHERE email=?", (COACH_EMAIL,)
    ).fetchone()["id"]
    print(f"Coach id={coach_id}  {COACH_EMAIL} / {COACH_PASSWORD}")

    conn.execute(
        "INSERT OR IGNORE INTO teams (name,season,threshold_pct) VALUES (?,?,80)",
        (TEAM_NAME, TEAM_SEASON),
    )
    team_id = conn.execute(
        "SELECT id FROM teams WHERE name=? AND season=?", (TEAM_NAME, TEAM_SEASON)
    ).fetchone()["id"]
    print(f"Team id={team_id}  {TEAM_NAME}")

    conn.execute(
        "INSERT OR IGNORE INTO coach_team_access (coach_id,team_id) VALUES (?,?)",
        (coach_id, team_id),
    )

    athletes = conn.execute("SELECT id, first_name FROM athletes LIMIT 6").fetchall()
    if not athletes:
        print("No athletes in DB. Onboard some athletes via the mobile app first.")
        conn.close()
        return
    for a in athletes:
        conn.execute(
            "INSERT OR IGNORE INTO roster_membership "
            "(athlete_id,team_id,parent_consent_flag) VALUES (?,?,1)",
            (a["id"], team_id),
        )
        print(f"  Rostered: {a['first_name']} (athlete_id={a['id']})")

    conn.commit()

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    weeks = [
        (monday - timedelta(weeks=2)).isoformat(),
        (monday - timedelta(weeks=1)).isoformat(),
        monday.isoformat(),
    ]
    for week_start in weeks:
        for i, a in enumerate(athletes):
            rate = RATES[i % len(RATES)]
            n_complete = round(rate * len(SLOTS))
            for j, slot in enumerate(SLOTS):
                conn.execute(
                    "INSERT OR IGNORE INTO fueling_window_log "
                    "(athlete_id,date,window_slot,applicable,completed) VALUES (?,?,?,1,?)",
                    (a["id"], week_start, slot, 1 if j < n_complete else 0),
                )
        conn.commit()
        result = generate_snapshot(team_id, week_start=week_start)
        print(f"  Snapshot {week_start}: "
              f"{result['players_above_threshold']}/{result['roster_count']} above threshold")

    conn.close()
    print(f"\nDone. Go to /coach/ and log in as {COACH_EMAIL} / {COACH_PASSWORD}")


if __name__ == "__main__":
    main()
