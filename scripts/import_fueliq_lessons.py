#!/usr/bin/env python3
"""
Import a batch of Fuel IQ lessons (each carrying its own quiz questions)
from a JSON file, e.g. content/fueliq_lessons_proposed.json.

Each item in the JSON array must have:
  level            (int, required)
  order_in_level   (int, required)
  title            (str, required, used for idempotency — re-importing the
                    same title is a no-op)
  hook             (str, required)
  fact_body        (str, optional)
  takeaway         (str, optional)
  category         (str, optional)
  source_citation  (str, required)
  points           (int, optional — defaults to the fueliq_lesson_points config)
  questions        (list, required — each with question_text, option_a,
                    option_b, option_c, correct_option, explanation,
                    misconception_tag [optional])

review_status defaults to 'draft' (spec §11.1 — RDN sign-off must be a
deliberate, explicit flag, not an accident of import). Pass --approve to
mark content as reviewed.

Usage (from repo root):
    python -m scripts.import_fueliq_lessons --file content/fueliq_lessons_proposed.json
    python -m scripts.import_fueliq_lessons --file content/fueliq_lessons_proposed.json \\
        --approve --reviewed-by "RDN-sourced content (FuelUp_FuelIQ_Review.xlsx)"
"""

import argparse
import json

from api.database import get_conn
from api.services.fueliq_service import import_lessons


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Fuel IQ lesson content")
    parser.add_argument("--file", required=True, help="Path to a JSON file with an array of lesson items")
    parser.add_argument("--approve", action="store_true", help="Mark imported lessons as review_status='approved'")
    parser.add_argument("--reviewed-by", default=None, help="Attribution stamped on approved lessons")
    args = parser.parse_args()

    with open(args.file) as f:
        items = json.load(f)

    review_status = "approved" if args.approve else "draft"

    conn = get_conn()
    try:
        inserted = import_lessons(conn, items, review_status=review_status, reviewed_by=args.reviewed_by)
    finally:
        conn.close()

    skipped = len(items) - len(inserted)
    print(f"Imported {len(inserted)} new lesson(s) as '{review_status}', skipped {skipped} already-imported title(s).")
    for row in inserted:
        print(f"  level {row['level']} — {row['title']}")


if __name__ == "__main__":
    main()
