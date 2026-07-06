#!/usr/bin/env python3
"""
build_recipes.py — LOCAL, ZERO-TOKEN converter.

Reads the curated recipe markdown in  recipes/*.md  and regenerates
api/data/recipes.json  (the artifact the app actually serves).

No network, no Bedrock, no LLM. Pure markdown parsing + deterministic
keyword tagging. Run it on your laptop any time the .md set changes:

    python scripts/build_recipes.py

It backs up the previous recipes.json to recipes.json.bak, then prints a
review report (counts + a sample of the inferred allergen tags, which are
the one safety-critical field and should be spot-checked by the RDN).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "recipes"
OUT = ROOT / "api" / "data" / "recipes.json"

# ── Allergen inversion (FREE FROM → CONTAINS) ────────────────────────────────
# The .md tags what a dish is FREE FROM; the app filters on what it CONTAINS.
# contains = (FDA big-9) − (free-from set). Erring toward "contains" is the
# SAFE direction for allergic minors (over-filtering, never under-filtering).
BIG9 = ["dairy", "egg", "fish", "shellfish", "tree nuts", "peanut", "gluten", "soy", "sesame"]
FREE_TOKEN_TO_ALLERGEN = {
    "dairy-free": "dairy", "df": "dairy",
    "egg-free": "egg", "ef": "egg",
    "fish-free": "fish", "ff": "fish",
    "shellfish-free": "shellfish", "shf": "shellfish",
    "tree nut-free": "tree nuts", "tnf": "tree nuts",
    "peanut-free": "peanut", "pf": "peanut",
    "gluten-free": "gluten", "gf": "gluten", "wf": "gluten",
    "soy-free": "soy", "soyf": "soy",
    "sesame-free": "sesame", "sesf": "sesame",
}

# ── Plate-section tagging (drives the Performance Plate color dots) ───────────
# Keyword scan over the FULL ingredient text. A dish can fill multiple sections.
# Heuristic + RDN-tunable — not a nutrition calculation.
PLATE_KEYWORDS = {
    "carbs": ["rice", "pasta", "noodle", "bread", "roti", "naan", "chapati", "tortilla",
              "quinoa", "oat", "potato", "bagel", "toast", "congee", "arepa", "wrap",
              "bun", "granola", "honey", "banana", "fruit", "poha", "couscous", "udon",
              "soba", "corn", "masa", "cereal", "pancake", "waffle", "rice cake"],
    "protein": ["chicken", "beef", "pork", "turkey", "fish", "salmon", "tuna", "egg",
                "tofu", "paneer", "dal", "lentil", "bean", "chickpea", "yogurt", "cheese",
                "cottage cheese", "milk", "edamame", "shrimp", "tempeh", "sirloin",
                "ground beef", "katsu", "bulgogi", "chana", "besan", "salmon", "sardine"],
    "veg": ["spinach", "broccoli", "carrot", "pepper", "tomato", "onion", "kale",
            "lettuce", "cucumber", "asparagus", "cabbage", "kimchi", "sprout", "greens",
            "vegetable", "mushroom", "zucchini", "cauliflower", "gobi", "pea", "salsa",
            "pico", "guacamole", "avocado", "beet", "squash", "eggplant"],
    "fat": ["ghee", "oil", "butter", "avocado", "nut", "almond", "walnut", "peanut",
            "sesame", "tahini", "coconut milk", "guacamole", "cheese"],
}

MEAL_CANON = {
    "pre-game fueling": "Pre-Game Fueling",
    "post-game recovery": "Post-Game Recovery",
    "mid-day snacks": "Mid-Day Snacks",
    "mid-day snack": "Mid-Day Snacks",
    "breakfast": "Breakfast",
    "lunch": "Lunch",
    "dinner": "Dinner",
}
TIMING = {
    "Pre-Game Fueling": "2–3 hrs before activity",
    "Post-Game Recovery": "within 30–60 min after",
    "Mid-Day Snacks": "anytime snack",
    "Breakfast": "morning",
    "Lunch": "midday",
    "Dinner": "evening",
}

_UNIT = (r"cups?|tbsp|tsp|oz|lbs?|lb|g|kg|ml|cloves?|cans?|medium|large|small|"
         r"slices?|handful|pinch|bunch|package|pkg|scoops?|sprigs?|stalks?")


def _unescape(raw: str) -> str:
    for a, b in [("\\#", "#"), ("\\|", "|"), ("\\[", "["), ("\\]", "]"),
                 ("\\*", "*"), ("\\'", "'"), ("\\-", "-")]:
        raw = raw.replace(a, b)
    return raw


def _cells(raw: str) -> list[str]:
    """Flatten a pandoc grid-table file into logical cells (split on rules)."""
    out, marker = [], "\x00"
    for line in raw.splitlines():
        s = line.strip()
        if re.fullmatch(r"[+][-=+ ]*", s):
            out.append(marker)
            continue
        s = re.sub(r"^\s*\|", "", s)
        s = re.sub(r"\|\s*$", "", s).strip()
        s = re.sub(r"^>\s*", "", s).strip()
        out.append(s)
    joined = "\n".join(out)
    cells = [re.sub(r"\s+", " ", c.replace("\n", " ")).strip() for c in joined.split(marker)]
    return [c for c in cells if c]


def _short_ingredient(s: str) -> str:
    s = s.replace(">", " ").replace("*", " ").strip().lstrip("•").strip()
    s = re.sub(r"^[\d¼½¾⅓⅔⅛⅜⅝⅞().,/\s-]*", "", s)
    for _ in range(2):
        s = re.sub(rf"^({_UNIT})\b\.?\s*", "", s, flags=re.I)
    s = s.split(",")[0].strip()
    s = re.sub(r"\s*\([^)]*\)", "", s).strip()
    return s


# Athlete-facing combo label (e.g. "Greek yogurt + granola + berries"). Derived
# from the recipe name — parentheticals + filler words dropped, joins → " + ".
# This is the ONLY recipe text the athlete sees on the plate; the rest of the
# recipe stays behind the scenes (allergy filter, plate dots). RDN-polishable.
_LABEL_FILLER = (r"\b(recovery|post-game|pre-game|game-day|style|homemade|athlete|"
                 r"custom|power|energy|mini|bites|box|snack|-style)\b")


def _short_label(name: str) -> str:
    s = re.sub(r"\s*\([^)]*\)", "", name)          # drop parentheticals (keeps dish name)
    s = re.sub(_LABEL_FILLER, "", s, flags=re.I)
    s = re.sub(r"\s+with\s+", " + ", s, flags=re.I)
    s = re.sub(r"\s*&\s*", " + ", s)
    s = re.sub(r"\s+and\s+", " + ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" +")
    return (s[0].upper() + s[1:].lower()) if s else name


def _plate_sections(ingredient_text: str) -> list[str]:
    t = ingredient_text.lower()
    return [sec for sec, kws in PLATE_KEYWORDS.items() if any(k in t for k in kws)]


def parse_recipe(path: Path) -> tuple[dict | None, list[str]]:
    warns: list[str] = []
    cells = _cells(_unescape(path.read_text(encoding="utf-8")))

    def find(substr):
        return next((c for c in cells if substr in c), "")

    header = find("#")
    m = re.search(r"#(\d+)\s+\*{0,2}(.+?)\*{0,2}\s*\|\s*([A-Za-z]+)\s*[··]\s*([A-Za-z -]+)", header)
    if not m:
        return None, [f"{path.name}: header unparseable"]
    num, name, cuisine, meal = m.group(1), m.group(2).strip(" *"), m.group(3).strip(), m.group(4).strip()
    category = MEAL_CANON.get(meal.lower(), meal.title())

    nutri = find("NUTRITION PER SERVING")
    macros = {}
    for key, col in [("calories", "Calories"), ("carbs_g", "Carbs"),
                     ("protein_g", "Protein"), ("fat_g", "Fat")]:
        mm = re.search(rf"{col}\s*:?\s*(\d+)", nutri)
        macros[key] = int(mm.group(1)) if mm else None
        if mm is None:
            warns.append(f"{path.name}: missing macro {col}")

    ing_cell = find("INGREDIENTS").split("INSTRUCTIONS")[0]
    ing_cell = re.sub(r".*INGREDIENTS\**", "", ing_cell, count=1)
    raw_items = [i for i in re.split(r"•", ing_cell) if i.strip() and set(i.strip()) - set("> *")]
    ingredients = [x for x in (_short_ingredient(i) for i in raw_items) if x]
    plate = _plate_sections(" ".join(raw_items))
    if not plate:
        warns.append(f"{path.name}: no plate section matched")

    tags = find("FREE FROM")
    ff_sec = re.search(r"FREE FROM(.*?)(?:DIETARY|NUTRIENT FOCUS|$)", tags)
    di_sec = re.search(r"DIETARY(.*?)(?:NUTRIENT FOCUS|$)", tags)
    nf_sec = re.search(r"NUTRIENT FOCUS(.*)$", tags)
    free_tokens = re.findall(r"\[([^]]+)\]", ff_sec.group(1)) if ff_sec else []
    free_norm = {FREE_TOKEN_TO_ALLERGEN[t.strip().lower()]
                 for t in free_tokens if t.strip().lower() in FREE_TOKEN_TO_ALLERGEN}
    allergens = [a for a in BIG9 if a not in free_norm]
    dietary = [t.strip().lower() for t in re.findall(r"\[([^]]+)\]", di_sec.group(1))] if di_sec else []
    nutrient_focus = [t.strip() for t in re.findall(r"\[([^]]+)\]", nf_sec.group(1))] if nf_sec else []

    tip_cell = find("TIP / SWAP")
    tip = re.sub(r".*TIP / SWAP:?\s*", "", tip_cell).strip(" *")

    recipe = {
        "id": f"R{int(num):03d}",
        "name": name,
        "short_label": _short_label(name),
        "cuisine": cuisine,
        "category": category,
        "meal_type": meal,
        "timing": TIMING.get(category, meal),
        "ingredients": ", ".join(ingredients),
        "macros": macros,
        "plate_sections": plate,
        "dietary": dietary,
        "allergens": allergens,
        "nutrient_focus": nutrient_focus,
        "tip": tip,
        "source_file": path.name,
    }
    return recipe, warns


def main():
    files = sorted(SRC_DIR.glob("*.md"))
    if not files:
        sys.exit(f"No .md files in {SRC_DIR}")

    recipes, all_warns, failures = [], [], []
    ids_seen = {}
    for f in files:
        rec, warns = parse_recipe(f)
        all_warns += warns
        if rec is None:
            failures.append(f.name)
            continue
        if rec["id"] in ids_seen:
            failures.append(f"{f.name}: duplicate id {rec['id']} (also {ids_seen[rec['id']]})")
            continue
        ids_seen[rec["id"]] = f.name
        recipes.append(rec)
    recipes.sort(key=lambda r: r["id"])

    if OUT.exists():
        bak = OUT.with_suffix(".json.bak")
        bak.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")

    OUT.write_text(json.dumps(recipes, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Review report ────────────────────────────────────────────────────────
    def dist(key):
        d = {}
        for r in recipes:
            d[r[key]] = d.get(r[key], 0) + 1
        return dict(sorted(d.items(), key=lambda x: -x[1]))

    print(f"\nParsed {len(recipes)}/{len(files)} recipes -> {OUT}")
    print(f"Backup: {OUT.with_suffix('.json.bak')}")
    print(f"\nBy cuisine:  {dist('cuisine')}")
    print(f"By category: {dist('category')}")
    ps = {}
    for r in recipes:
        ps[len(r["plate_sections"])] = ps.get(len(r["plate_sections"]), 0) + 1
    print(f"Plate-section coverage (sections per dish): {dict(sorted(ps.items()))}")

    print("\nALLERGEN SPOT-CHECK (inferred 'contains' — RDN please verify):")
    for r in recipes[:8]:
        print(f"  {r['id']} {r['name'][:42]:42} contains: {', '.join(r['allergens']) or '(none)'}")

    if failures:
        print(f"\n!! {len(failures)} FAILURES:")
        for x in failures:
            print(f"   {x}")
    if all_warns:
        print(f"\n{len(all_warns)} warnings (first 12):")
        for w in all_warns[:12]:
            print(f"   {w}")


if __name__ == "__main__":
    main()
