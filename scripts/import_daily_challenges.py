#!/usr/bin/env python3
"""
Import a batch of Fuel IQ Daily Challenge questions from a JSON file.

Each item in the JSON array must have:
  title            (str, required, used for idempotency — re-importing the
                    same title is a no-op)
  hook             (str, required — the claim shown before the guess)
  verdict          (str, required — "real" or "myth")
  science_text     (str, required — the explanation shown after the guess)
  source_citation  (str, optional)

Challenges are assigned sequential calendar dates automatically, starting
the day after whatever's already scheduled furthest out (or today, PST, if
nothing is scheduled yet).

Usage (from repo root):
    python -m scripts.import_daily_challenges --file daily_challenges.json
"""

import argparse
import json

from api.database import get_conn
from api.services.fueliq_daily_challenge_service import import_daily_challenges


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Fuel IQ Daily Challenge content")
    parser.add_argument("--file", required=True, help="Path to a JSON file with an array of challenge items")
    args = parser.parse_args()

    with open(args.file) as f:
        items = json.load(f)

    conn = get_conn()
    try:
        inserted = import_daily_challenges(conn, items)
    finally:
        conn.close()

    skipped = len(items) - len(inserted)
    print(f"Imported {len(inserted)} new challenge(s), skipped {skipped} already-imported title(s).")
    for row in inserted:
        print(f"  {row['challenge_date']} — {row['title']}")


if __name__ == "__main__":
    main()
