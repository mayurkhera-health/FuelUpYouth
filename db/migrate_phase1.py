#!/usr/bin/env python3
"""
Phase 1 migration: schedule_reminder_dismissed flag.

Adds one column to parents and one to athletes. Additive only — no data dropped.

Usage:
  python db/migrate_phase1.py              # Dry-run against /tmp copy
  python db/migrate_phase1.py --apply      # Apply to production DB
  python db/migrate_phase1.py --db PATH   # Target a specific DB file
"""
import argparse
import shutil
import sqlite3
from pathlib import Path

DB_PATH   = Path(__file__).resolve().parent.parent / "fuelup.db"
TEST_PATH = Path("/tmp/fuelup_phase1_test.db")


def _cols(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def run_schema(conn):
    print("\n── Schema changes ──")

    if "schedule_reminder_dismissed" not in _cols(conn, "parents"):
        conn.execute(
            "ALTER TABLE parents ADD COLUMN schedule_reminder_dismissed INTEGER DEFAULT 0"
        )
        print("  + parents.schedule_reminder_dismissed")
    else:
        print("  · parents.schedule_reminder_dismissed  (already exists)")

    if "schedule_reminder_dismissed" not in _cols(conn, "athletes"):
        conn.execute(
            "ALTER TABLE athletes ADD COLUMN schedule_reminder_dismissed INTEGER DEFAULT 0"
        )
        print("  + athletes.schedule_reminder_dismissed")
    else:
        print("  · athletes.schedule_reminder_dismissed  (already exists)")

    conn.commit()
    print("\n  Schema committed.")


def verify(conn) -> bool:
    print("\n── Verification ──")
    issues = []

    for table in ("parents", "athletes"):
        cols = _cols(conn, table)
        if "schedule_reminder_dismissed" in cols:
            print(f"  ✓ {table}.schedule_reminder_dismissed present")
        else:
            issues.append(f"FAIL: {table}.schedule_reminder_dismissed missing")

    # Idempotency: run again, must not raise
    try:
        run_schema(conn)
        print("  ✓ idempotency: re-run produced no errors")
    except Exception as e:
        issues.append(f"FAIL idempotency: {e}")

    if issues:
        print("\nVERIFICATION FAILED:")
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("\n  VERIFICATION PASSED")
    return len(issues) == 0


def main():
    parser = argparse.ArgumentParser(description="Phase 1 migration: schedule_reminder_dismissed")
    parser.add_argument("--apply", action="store_true", help="Apply to production DB")
    parser.add_argument("--db",    type=str,            help="Target a specific DB file")
    args = parser.parse_args()

    if args.db:
        target = Path(args.db)
    elif args.apply:
        target = DB_PATH
        print(f"⚠  PRODUCTION MODE — target: {target}")
    else:
        print(f"DRY-RUN — copying {DB_PATH.name} to {TEST_PATH}")
        shutil.copy2(str(DB_PATH), str(TEST_PATH))
        target = TEST_PATH
        print(f"Target: {target}")

    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    run_schema(conn)
    ok = verify(conn)
    conn.close()

    if not ok:
        print("\nAborting — verification failed.")
        return

    if not args.apply and not args.db:
        print(f"\nDRY-RUN complete. Re-run with --apply to apply to production DB.")


if __name__ == "__main__":
    main()
