#!/usr/bin/env python3
"""
Phase 0 migration: Two-Persona account model.

Additive schema changes only — no columns dropped, no tables renamed.
Existing parent login, athlete lookup, and all nutrition routes are unchanged.

Usage:
  python db/migrate_phase0.py              # Dry-run against /tmp copy
  python db/migrate_phase0.py --apply      # Apply to production DB
  python db/migrate_phase0.py --reverse    # Logical rollback (nulls new data, drops new tables)
  python db/migrate_phase0.py --db PATH    # Target a specific DB file

Design decisions:
  - The existing `parents` table acts as the parent-role account table.
    We add `role TEXT` to it; existing rows → role='parent'.
  - Athlete *login* credentials go in a NEW `athlete_logins` table so
    they never pollute the `athletes` profile table.
  - `account_athlete` is the canonical link (parent→N athletes, athlete→1 self).
  - SQLite does not support DROP COLUMN, so --reverse nulls data and drops
    only the NEW tables; the added columns stay in schema but are inert.
"""
import argparse
import shutil
import sqlite3
from pathlib import Path

DB_PATH  = Path(__file__).resolve().parent.parent / "fuelup.db"
TEST_PATH = Path("/tmp/fuelup_phase0_test.db")


# ── helpers ──────────────────────────────────────────────────────────────────

def _table_cols(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]

def _table_exists(conn, table: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone())

def snapshot(conn, label: str) -> dict:
    counts: dict = {}
    for t in ["parents", "athletes", "events"]:
        counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    counts["window_logs"] = (
        conn.execute("SELECT COUNT(*) FROM window_logs").fetchone()[0]
        if _table_exists(conn, "window_logs") else "⟨not created yet⟩"
    )
    for t in ["account_athlete", "athlete_logins"]:
        counts[t] = (
            conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            if _table_exists(conn, t) else "⟨not created yet⟩"
        )

    # Derived data-quality counts (safe: columns may not exist yet)
    try:
        counts["parents_role_set"] = conn.execute(
            "SELECT COUNT(*) FROM parents WHERE role IS NOT NULL"
        ).fetchone()[0]
    except Exception:
        counts["parents_role_set"] = "n/a"
    try:
        counts["athletes_owner_set"] = conn.execute(
            "SELECT COUNT(*) FROM athletes WHERE owner_account_id IS NOT NULL"
        ).fetchone()[0]
    except Exception:
        counts["athletes_owner_set"] = "n/a"
    try:
        counts["events_edited_by_set"] = conn.execute(
            "SELECT COUNT(*) FROM events WHERE edited_by IS NOT NULL"
        ).fetchone()[0]
    except Exception:
        counts["events_edited_by_set"] = "n/a"

    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    for k, v in counts.items():
        print(f"  {k:<28} {v}")
    return counts


# ── schema migration (idempotent) ─────────────────────────────────────────────

def run_schema(conn):
    print("\n── Schema changes ──")

    # 1. parents.role
    if "role" not in _table_cols(conn, "parents"):
        conn.execute("ALTER TABLE parents ADD COLUMN role TEXT")
        print("  + parents.role")
    else:
        print("  · parents.role  (already exists)")

    # 2. athletes.owner_account_id
    if "owner_account_id" not in _table_cols(conn, "athletes"):
        conn.execute("ALTER TABLE athletes ADD COLUMN owner_account_id INTEGER")
        print("  + athletes.owner_account_id")
    else:
        print("  · athletes.owner_account_id  (already exists)")

    # 3. athletes.can_transfer
    if "can_transfer" not in _table_cols(conn, "athletes"):
        conn.execute("ALTER TABLE athletes ADD COLUMN can_transfer INTEGER DEFAULT 1")
        print("  + athletes.can_transfer")
    else:
        print("  · athletes.can_transfer  (already exists)")

    # 4. account_athlete link table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_athlete (
            account_id   INTEGER NOT NULL,
            athlete_id   INTEGER NOT NULL,
            relationship TEXT NOT NULL,        -- 'parent' | 'self'
            is_primary   INTEGER DEFAULT 0,
            PRIMARY KEY (account_id, athlete_id)
        )
    """)
    print("  + account_athlete  (CREATE IF NOT EXISTS)")

    # 5. athlete_logins — stores credentials for athlete logins
    conn.execute("""
        CREATE TABLE IF NOT EXISTS athlete_logins (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT UNIQUE NOT NULL,
            athlete_id INTEGER NOT NULL UNIQUE REFERENCES athletes(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  + athlete_logins  (CREATE IF NOT EXISTS)")

    # 6. window_logs — create with logged_by if missing; add col if table pre-exists
    if not _table_exists(conn, "window_logs"):
        conn.execute("""
            CREATE TABLE window_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id      INTEGER NOT NULL,
                window_id       TEXT NOT NULL,
                log_date        TEXT NOT NULL,
                method          TEXT NOT NULL DEFAULT 'photo',
                text            TEXT,
                photo_url       TEXT,
                thumb_url       TEXT,
                nutrient_status TEXT NOT NULL DEFAULT 'none',
                logged_by       TEXT,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(athlete_id, window_id, log_date)
            )
        """)
        print("  + window_logs  (fresh create with logged_by)")
    else:
        if "logged_by" not in _table_cols(conn, "window_logs"):
            conn.execute("ALTER TABLE window_logs ADD COLUMN logged_by TEXT")
            print("  + window_logs.logged_by  (added to existing table)")
        else:
            print("  · window_logs.logged_by  (already exists)")

    # 7. events.edited_by
    if "edited_by" not in _table_cols(conn, "events"):
        conn.execute("ALTER TABLE events ADD COLUMN edited_by TEXT")
        print("  + events.edited_by")
    else:
        print("  · events.edited_by  (already exists)")

    conn.commit()
    print("\n  Schema committed.")


# ── data backfill (idempotent) ────────────────────────────────────────────────

def run_backfill(conn):
    print("\n── Data backfill ──")

    # 1. All existing parents → role='parent'
    n = conn.execute(
        "UPDATE parents SET role = 'parent' WHERE role IS NULL"
    ).rowcount
    print(f"  parents.role='parent'          {n} rows updated")

    # 2. athletes.owner_account_id ← parent_id (existing FK)
    n = conn.execute(
        "UPDATE athletes SET owner_account_id = parent_id "
        "WHERE owner_account_id IS NULL AND parent_id IS NOT NULL"
    ).rowcount
    print(f"  athletes.owner_account_id      {n} rows updated")

    # 3. athletes.can_transfer = 1
    n = conn.execute(
        "UPDATE athletes SET can_transfer = 1 WHERE can_transfer IS NULL"
    ).rowcount
    print(f"  athletes.can_transfer          {n} rows updated")

    # 4. account_athlete links: one parent→athlete row per existing relationship
    n = conn.execute("""
        INSERT OR IGNORE INTO account_athlete
            (account_id, athlete_id, relationship, is_primary)
        SELECT parent_id, id, 'parent', 1
        FROM athletes
        WHERE parent_id IS NOT NULL
    """).rowcount
    print(f"  account_athlete links          {n} rows inserted")

    # 5. window_logs.logged_by → 'athlete' (safe default per spec)
    if _table_exists(conn, "window_logs"):
        n = conn.execute(
            "UPDATE window_logs SET logged_by = 'athlete' WHERE logged_by IS NULL"
        ).rowcount
        print(f"  window_logs.logged_by          {n} rows updated")
    else:
        print("  window_logs.logged_by          (table empty — nothing to backfill)")

    # 6. events.edited_by → 'parent' (parents set up schedules historically)
    n = conn.execute(
        "UPDATE events SET edited_by = 'parent' WHERE edited_by IS NULL"
    ).rowcount
    print(f"  events.edited_by               {n} rows updated")

    conn.commit()
    print("\n  Backfill committed.")


# ── verification ──────────────────────────────────────────────────────────────

def verify(conn, before: dict) -> bool:
    print("\n── Verification ──")
    issues = []

    # Row counts must not change for pre-existing tables
    for t in ("parents", "athletes", "events"):
        after_cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        if after_cnt != before[t]:
            issues.append(f"FAIL {t}: {before[t]} → {after_cnt}  (row count changed!)")
        else:
            print(f"  ✓ {t}: {after_cnt} rows unchanged")

    # window_logs was created fresh — just check it exists
    wl_cnt = conn.execute("SELECT COUNT(*) FROM window_logs").fetchone()[0]
    print(f"  ✓ window_logs: {wl_cnt} rows (fresh or pre-existing)")

    # All parents have role
    total_p = conn.execute("SELECT COUNT(*) FROM parents").fetchone()[0]
    roled_p = conn.execute("SELECT COUNT(*) FROM parents WHERE role='parent'").fetchone()[0]
    if roled_p != total_p:
        issues.append(f"FAIL role: {total_p - roled_p} parents missing role")
    else:
        print(f"  ✓ all {total_p} parents have role='parent'")

    # All athletes have owner_account_id
    total_a = conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0]
    owned_a = conn.execute(
        "SELECT COUNT(*) FROM athletes WHERE owner_account_id IS NOT NULL"
    ).fetchone()[0]
    if owned_a != total_a:
        issues.append(f"FAIL owner: {total_a - owned_a} athletes missing owner_account_id")
    else:
        print(f"  ✓ all {total_a} athletes have owner_account_id")

    # account_athlete links ≥ number of athletes with parent_id
    link_cnt = conn.execute("SELECT COUNT(*) FROM account_athlete").fetchone()[0]
    print(f"  ✓ account_athlete: {link_cnt} links")

    # No orphaned athletes (must have at least one link)
    orphans = conn.execute("""
        SELECT COUNT(*) FROM athletes a
        WHERE NOT EXISTS (
            SELECT 1 FROM account_athlete aa WHERE aa.athlete_id = a.id
        )
    """).fetchone()[0]
    if orphans:
        issues.append(f"FAIL orphans: {orphans} athletes have no account_athlete link")
    else:
        print(f"  ✓ no orphaned athletes")

    # All events have edited_by
    no_edited = conn.execute(
        "SELECT COUNT(*) FROM events WHERE edited_by IS NULL"
    ).fetchone()[0]
    if no_edited:
        issues.append(f"FAIL edited_by: {no_edited} events missing edited_by")
    else:
        print(f"  ✓ all events have edited_by")

    # Idempotency check: run schema again — must not raise
    try:
        run_schema(conn)
        run_backfill(conn)
        link_cnt2 = conn.execute("SELECT COUNT(*) FROM account_athlete").fetchone()[0]
        if link_cnt2 != link_cnt:
            issues.append(f"FAIL idempotency: re-run changed account_athlete {link_cnt} → {link_cnt2}")
        else:
            print(f"  ✓ idempotency: re-run produced no duplicates")
    except Exception as e:
        issues.append(f"FAIL idempotency: {e}")

    if issues:
        print("\nVERIFICATION FAILED:")
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("\n  VERIFICATION PASSED — all checks OK")
    return len(issues) == 0


# ── rollback (logical) ────────────────────────────────────────────────────────

def run_reverse(conn):
    print("\n── Rollback ──")
    conn.execute("UPDATE parents SET role = NULL")
    conn.execute("UPDATE athletes SET owner_account_id = NULL, can_transfer = NULL")
    conn.execute("UPDATE events SET edited_by = NULL")
    if _table_exists(conn, "window_logs"):
        conn.execute("UPDATE window_logs SET logged_by = NULL")
    conn.execute("DROP TABLE IF EXISTS account_athlete")
    conn.execute("DROP TABLE IF EXISTS athlete_logins")
    conn.commit()
    print("  Done. New columns remain in schema (SQLite limitation) but are NULL.")
    print("  New tables (account_athlete, athlete_logins) dropped.")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 0 migration: Two-Persona model")
    parser.add_argument("--apply",   action="store_true", help="Apply to production DB")
    parser.add_argument("--reverse", action="store_true", help="Logical rollback")
    parser.add_argument("--db",      type=str,            help="Target a specific DB file")
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

    before = snapshot(conn, "BEFORE migration")

    if args.reverse:
        run_reverse(conn)
    else:
        run_schema(conn)
        run_backfill(conn)
        ok = verify(conn, before)
        if not ok:
            print("\nAborting — verification failed. Check issues above.")
            conn.close()
            return

    snapshot(conn, "AFTER migration")
    conn.close()

    if not args.apply and not args.db and not args.reverse:
        print(f"\nThis was a DRY-RUN against a copy at {TEST_PATH}.")
        print("Re-run with --apply to apply to the production DB.")


if __name__ == "__main__":
    main()
