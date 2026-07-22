"""
Migrate recipes.json: parse each recipe's comma-separated ingredients string into
a structured array of { name, quantity, unit } objects using Claude.

Reads:  api/data/recipes.json
Writes: api/data/recipes_migrated.json
        api/data/migration_qa.json
"""

import json
import os
import time
import sys
import anthropic
from dotenv import load_dotenv

# Load .env from the project root (one level above scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Error: ANTHROPIC_API_KEY not found. Add it to .env in the project root.")
    sys.exit(1)

INPUT_PATH  = os.path.join(os.path.dirname(__file__), "../api/data/recipes.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../api/data/recipes_migrated.json")
QA_PATH     = os.path.join(os.path.dirname(__file__), "../api/data/migration_qa.json")

BATCH_SIZE   = 10
BATCH_DELAY  = 1  # seconds between batches
MODEL        = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a structured data parser for recipe ingredients.
Given a raw ingredient string, return ONLY a valid JSON array.
Each element must be: { "name": string, "quantity": number | null, "unit": string | null }
Rules:
- "to taste" ingredients: set quantity to null, unit to "to taste"
- Ranges like "2-3 cups": use the lower bound, flag in a separate "ambiguous" field set to true
- Fractions like "¼ cup": convert to decimal (0.25)
- If no unit is implied (e.g. "2 eggs"): use "whole" as the unit
- Never return anything outside the JSON array. No preamble, no explanation."""


def parse_ingredients(client: anthropic.Anthropic, raw: str) -> list[dict]:
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw}],
    )
    text = message.content[0].text.strip()
    # Strip markdown code fences if Claude wraps anyway
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def qa_flags(recipe: dict, ingredients: list[dict]) -> list[dict]:
    """Return QA entries for ambiguous, unexpected-null, or other flags."""
    flags = []
    for ing in ingredients:
        flag = None
        if ing.get("ambiguous"):
            flag = "ambiguous"
        elif ing.get("quantity") is None and ing.get("unit") != "to taste":
            flag = "null_quantity"
        if flag:
            flags.append({
                "recipe_id":       recipe["id"],
                "recipe_name":     recipe["name"],
                "raw_ingredient":  recipe["ingredients"],
                "parsed_result":   ing,
                "flag":            flag,
            })
    return flags


def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    with open(INPUT_PATH, encoding="utf-8") as f:
        recipes: list[dict] = json.load(f)

    migrated    = []
    qa_entries  = []
    total_ingredients = 0
    total_flags       = 0
    error_count       = 0

    total = len(recipes)
    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(batch_count):
        start = batch_idx * BATCH_SIZE
        batch = recipes[start : start + BATCH_SIZE]
        print(f"Batch {batch_idx + 1}/{batch_count} — recipes {start + 1}–{min(start + BATCH_SIZE, total)}")

        for recipe in batch:
            raw = recipe.get("ingredients", "")
            recipe_out = {k: v for k, v in recipe.items() if k != "ingredients"}

            if not raw or not raw.strip():
                recipe_out["ingredients"] = []
                migrated.append(recipe_out)
                continue

            try:
                parsed = parse_ingredients(client, raw)
                recipe_out["ingredients"] = parsed
                total_ingredients += len(parsed)

                flags = qa_flags(recipe, parsed)
                if flags:
                    qa_entries.extend(flags)
                    total_flags += len(flags)

            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON parse error on {recipe['id']} ({recipe['name']}): {e}")
                recipe_out["ingredients_raw"] = raw
                error_count += 1
                qa_entries.append({
                    "recipe_id":      recipe["id"],
                    "recipe_name":    recipe["name"],
                    "raw_ingredient": raw,
                    "parsed_result":  None,
                    "flag":           "json_parse_error",
                    "error":          str(e),
                })

            except anthropic.APIError as e:
                print(f"  [ERROR] API failure on {recipe['id']} ({recipe['name']}): {e}")
                recipe_out["ingredients_raw"] = raw
                error_count += 1
                qa_entries.append({
                    "recipe_id":      recipe["id"],
                    "recipe_name":    recipe["name"],
                    "raw_ingredient": raw,
                    "parsed_result":  None,
                    "flag":           "api_error",
                    "error":          str(e),
                })

            migrated.append(recipe_out)

        if batch_idx < batch_count - 1:
            time.sleep(BATCH_DELAY)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)

    with open(QA_PATH, "w", encoding="utf-8") as f:
        json.dump(qa_entries, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 50)
    print(f"Recipes processed:    {total}")
    print(f"Ingredients parsed:   {total_ingredients}")
    print(f"QA flags raised:      {total_flags}")
    print(f"API/parse errors:     {error_count}")
    print(f"Output:               {OUTPUT_PATH}")
    print(f"QA report:            {QA_PATH}")
    print("=" * 50)

    if error_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
