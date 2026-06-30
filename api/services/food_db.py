# food_db.py — GI-tiered food database + window filter
#
# gi_tier is an internal field — NEVER sent to the athlete.
# ui_icon (⚡) is shown on card for fast-absorbing options in Top-Up / Keep Going.
# Nutritional values are per typical youth-athlete serving size.
#
# Schema per record:
#   food_id       str   — stable unique key
#   name          str   — display name
#   cho_g         float — carbohydrates (g)
#   prot_g        float — protein (g)
#   fat_g         float — fat (g)
#   iron_mg       float — iron (mg); used only to sort iron_flag recharge window
#   gi_tier       str   — 'fast' | 'medium' | 'slow'  (internal only)
#   ui_icon       str   — '⚡' for fast; '' otherwise
#   allergens     list  — e.g. ['dairy','gluten','tree_nuts','eggs','soy','peanuts']
#   diet_tags     list  — 'vegan' | 'vegetarian' | 'gluten_free' | 'dairy_free'
#   role          str   — 'carb' | 'protein' | 'fat' | 'produce' | 'hydration'
#   purchase_unit str   — what a parent buys at the grocery store (e.g. "dozen", "32 oz tub")

FOOD_DATABASE: list[dict] = [

    # ── FAST (GI > 70) ────────────────────────────────────────────────────────
    {
        "food_id": "banana_ripe",
        "name": "Banana (ripe)",
        "cho_g": 27, "prot_g": 1, "fat_g": 0, "iron_mg": 0.3,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "bunch",
    },
    {
        "food_id": "white_rice_cooked",
        "name": "White rice (cooked, 1 cup)",
        "cho_g": 45, "prot_g": 4, "fat_g": 0, "iron_mg": 0.2,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "2 lb bag",
    },
    {
        "food_id": "sports_drink_8oz",
        "name": "Sports drink (8 oz)",
        "cho_g": 14, "prot_g": 0, "fat_g": 0, "iron_mg": 0.0,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "hydration", "purchase_unit": "12-pack (8 oz bottles)",
    },
    {
        "food_id": "rice_cakes_2",
        "name": "Rice cakes (2)",
        "cho_g": 14, "prot_g": 1, "fat_g": 0, "iron_mg": 0.1,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "4.9 oz bag",
    },
    {
        "food_id": "applesauce_pouch",
        "name": "Applesauce pouch (4 oz)",
        "cho_g": 14, "prot_g": 0, "fat_g": 0, "iron_mg": 0.2,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "pack of 4 pouches",
    },
    {
        "food_id": "honey_packet",
        "name": "Honey packet (1 tbsp)",
        "cho_g": 17, "prot_g": 0, "fat_g": 0, "iron_mg": 0.1,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "12 oz jar",
    },
    {
        "food_id": "energy_gel",
        "name": "Energy gel (1 packet)",
        "cho_g": 25, "prot_g": 0, "fat_g": 0, "iron_mg": 0.0,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "box of 12 packets",
    },
    {
        "food_id": "fruit_juice_8oz",
        "name": "Fruit juice (8 oz)",
        "cho_g": 29, "prot_g": 0, "fat_g": 0, "iron_mg": 0.3,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "hydration", "purchase_unit": "half gallon",
    },
    {
        "food_id": "white_bread_2sl",
        "name": "White bread (2 slices)",
        "cho_g": 26, "prot_g": 4, "fat_g": 2, "iron_mg": 1.8,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": ["gluten"], "diet_tags": ["vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "loaf",
    },
    {
        "food_id": "pretzels_1oz",
        "name": "Pretzels (1 oz)",
        "cho_g": 23, "prot_g": 3, "fat_g": 1, "iron_mg": 0.8,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "16 oz bag",
    },
    {
        "food_id": "watermelon_2cup",
        "name": "Watermelon (2 cups)",
        "cho_g": 23, "prot_g": 1, "fat_g": 0, "iron_mg": 0.4,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "produce", "purchase_unit": "1 whole watermelon",
    },
    {
        "food_id": "corn_flakes_1cup",
        "name": "Corn flakes (1 cup)",
        "cho_g": 25, "prot_g": 2, "fat_g": 0, "iron_mg": 4.5,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "18 oz box",
    },
    {
        "food_id": "dates_3",
        "name": "Dates (3)",
        "cho_g": 20, "prot_g": 0, "fat_g": 0, "iron_mg": 0.5,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "8 oz container",
    },
    {
        "food_id": "orange_juice_8oz",
        "name": "Orange juice (8 oz)",
        "cho_g": 26, "prot_g": 2, "fat_g": 0, "iron_mg": 0.3,
        "gi_tier": "fast", "ui_icon": "⚡",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "hydration", "purchase_unit": "half gallon",
    },

    # ── MEDIUM (GI 55–70) ─────────────────────────────────────────────────────
    {
        "food_id": "oatmeal_cooked",
        "name": "Oatmeal (cooked, 1 cup)",
        "cho_g": 27, "prot_g": 5, "fat_g": 3, "iron_mg": 2.1,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "18 oz canister",
    },
    {
        "food_id": "whole_wheat_bread_2sl",
        "name": "Whole wheat bread (2 slices)",
        "cho_g": 24, "prot_g": 8, "fat_g": 2, "iron_mg": 2.7,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "loaf",
    },
    {
        "food_id": "sweet_potato_baked",
        "name": "Sweet potato (baked, medium)",
        "cho_g": 26, "prot_g": 2, "fat_g": 0, "iron_mg": 0.7,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "3 lb bag",
    },
    {
        "food_id": "brown_rice_cooked",
        "name": "Brown rice (cooked, 1 cup)",
        "cho_g": 45, "prot_g": 5, "fat_g": 2, "iron_mg": 0.8,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "2 lb bag",
    },
    {
        "food_id": "yogurt_honey",
        "name": "Yogurt + honey (6 oz)",
        "cho_g": 28, "prot_g": 10, "fat_g": 3, "iron_mg": 0.1,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
        "role": "protein", "purchase_unit": "32 oz plain yogurt tub + 12 oz honey",
    },
    {
        "food_id": "whole_grain_pasta_cooked",
        "name": "Whole grain pasta (1 cup cooked)",
        "cho_g": 37, "prot_g": 7, "fat_g": 1, "iron_mg": 1.9,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "16 oz box",
    },
    {
        "food_id": "pita_small",
        "name": "Pita bread (1 small)",
        "cho_g": 33, "prot_g": 5, "fat_g": 1, "iron_mg": 1.5,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "pack of 6",
    },
    {
        "food_id": "corn_half_cup",
        "name": "Corn (1/2 cup)",
        "cho_g": 17, "prot_g": 3, "fat_g": 1, "iron_mg": 0.4,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "produce", "purchase_unit": "15 oz can",
    },
    {
        "food_id": "raisins_quarter_cup",
        "name": "Raisins (1/4 cup)",
        "cho_g": 33, "prot_g": 1, "fat_g": 0, "iron_mg": 0.9,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "12 oz box",
    },
    {
        "food_id": "bagel_plain",
        "name": "Plain bagel (1 small)",
        "cho_g": 38, "prot_g": 7, "fat_g": 1, "iron_mg": 2.7,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "pack of 6",
    },
    {
        "food_id": "granola_bar",
        "name": "Granola bar (1)",
        "cho_g": 29, "prot_g": 3, "fat_g": 4, "iron_mg": 0.8,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["gluten", "tree_nuts"], "diet_tags": ["vegetarian", "dairy_free"],
        "role": "carb", "purchase_unit": "box of 6",
    },
    {
        "food_id": "chocolate_milk_8oz",
        "name": "Chocolate milk (8 oz)",
        "cho_g": 26, "prot_g": 8, "fat_g": 5, "iron_mg": 0.2,
        "gi_tier": "medium", "ui_icon": "",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
        "role": "protein", "purchase_unit": "half gallon",
    },

    # ── SLOW (GI < 55) ────────────────────────────────────────────────────────
    {
        "food_id": "lentils_half_cup",
        "name": "Lentils (1/2 cup cooked)",
        "cho_g": 20, "prot_g": 9, "fat_g": 0, "iron_mg": 3.3,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "16 oz dry bag",
    },
    {
        "food_id": "chickpeas_half_cup",
        "name": "Chickpeas (1/2 cup)",
        "cho_g": 22, "prot_g": 7, "fat_g": 2, "iron_mg": 2.4,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "15 oz can",
    },
    {
        "food_id": "quinoa_half_cup",
        "name": "Quinoa (1/2 cup cooked)",
        "cho_g": 20, "prot_g": 4, "fat_g": 2, "iron_mg": 1.4,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "carb", "purchase_unit": "16 oz bag",
    },
    {
        "food_id": "apple_medium",
        "name": "Apple (medium)",
        "cho_g": 25, "prot_g": 0, "fat_g": 0, "iron_mg": 0.2,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "produce", "purchase_unit": "3 lb bag",
    },
    {
        "food_id": "milk_8oz",
        "name": "Milk (8 oz)",
        "cho_g": 12, "prot_g": 8, "fat_g": 5, "iron_mg": 0.1,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
        "role": "hydration", "purchase_unit": "gallon",
    },
    {
        "food_id": "greek_yogurt_plain",
        "name": "Plain Greek yogurt (6 oz)",
        "cho_g": 7, "prot_g": 17, "fat_g": 0, "iron_mg": 0.1,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
        "role": "protein", "purchase_unit": "32 oz tub",
    },
    {
        "food_id": "eggs_2",
        "name": "Eggs (2 large)",
        "cho_g": 0, "prot_g": 12, "fat_g": 10, "iron_mg": 1.8,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["eggs"], "diet_tags": ["vegetarian", "gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "dozen",
    },
    {
        "food_id": "almonds_1oz",
        "name": "Almonds (1 oz)",
        "cho_g": 6, "prot_g": 6, "fat_g": 14, "iron_mg": 1.0,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["tree_nuts"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "fat", "purchase_unit": "10 oz bag",
    },
    {
        "food_id": "mixed_vegetables_1cup",
        "name": "Mixed vegetables (1 cup)",
        "cho_g": 12, "prot_g": 2, "fat_g": 0, "iron_mg": 1.5,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "produce", "purchase_unit": "12 oz frozen bag",
    },
    {
        "food_id": "cottage_cheese_half_cup",
        "name": "Cottage cheese (1/2 cup)",
        "cho_g": 4, "prot_g": 14, "fat_g": 5, "iron_mg": 0.2,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
        "role": "protein", "purchase_unit": "16 oz tub",
    },
    {
        "food_id": "kidney_beans_half_cup",
        "name": "Kidney beans (1/2 cup)",
        "cho_g": 20, "prot_g": 8, "fat_g": 0, "iron_mg": 2.0,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "15 oz can",
    },
    {
        "food_id": "spinach_2cup",
        "name": "Spinach salad (2 cups)",
        "cho_g": 4, "prot_g": 2, "fat_g": 0, "iron_mg": 2.7,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "produce", "purchase_unit": "5 oz bag",
    },
    {
        "food_id": "pear_medium",
        "name": "Pear (medium)",
        "cho_g": 27, "prot_g": 0, "fat_g": 0, "iron_mg": 0.3,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "produce", "purchase_unit": "3 lb bag",
    },
    {
        "food_id": "tofu_half_cup",
        "name": "Tofu (1/2 cup firm)",
        "cho_g": 2, "prot_g": 10, "fat_g": 5, "iron_mg": 3.4,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["soy"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "14 oz block",
    },
    {
        "food_id": "peanut_butter_2tbsp",
        "name": "Peanut butter (2 tbsp)",
        "cho_g": 6, "prot_g": 8, "fat_g": 16, "iron_mg": 0.6,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["peanuts"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "role": "fat", "purchase_unit": "16 oz jar",
    },

    # ── OMNIVORE-ONLY (meat / poultry / fish) ─────────────────────────────────
    # No vegetarian or vegan tag — filtered out for plant-based athletes.
    {
        "food_id": "grilled_chicken_3oz",
        "name": "Grilled chicken (3 oz)",
        "cho_g": 0, "prot_g": 26, "fat_g": 3, "iron_mg": 0.9,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "1.5 lb pack",
    },
    {
        "food_id": "turkey_3oz",
        "name": "Turkey breast (3 oz)",
        "cho_g": 0, "prot_g": 25, "fat_g": 2, "iron_mg": 1.1,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "1 lb pack",
    },
    {
        "food_id": "salmon_3oz",
        "name": "Salmon (3 oz)",
        "cho_g": 0, "prot_g": 22, "fat_g": 7, "iron_mg": 0.5,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["fish"], "diet_tags": ["gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "1 lb fillet",
    },
    {
        "food_id": "tuna_can",
        "name": "Canned tuna (3 oz)",
        "cho_g": 0, "prot_g": 22, "fat_g": 1, "iron_mg": 1.3,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["fish"], "diet_tags": ["gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "5 oz can",
    },
    {
        "food_id": "ground_beef_3oz",
        "name": "Lean ground beef (3 oz)",
        "cho_g": 0, "prot_g": 22, "fat_g": 10, "iron_mg": 2.7,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": [], "diet_tags": ["gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "1 lb pack",
    },
    {
        "food_id": "shrimp_3oz",
        "name": "Shrimp (3 oz)",
        "cho_g": 0, "prot_g": 18, "fat_g": 1, "iron_mg": 2.6,
        "gi_tier": "slow", "ui_icon": "",
        "allergens": ["shellfish"], "diet_tags": ["gluten_free", "dairy_free"],
        "role": "protein", "purchase_unit": "12 oz bag (frozen)",
    },

    # ── South Asian ──────────────────────────────────────────────
    {
        "food_id": "dal_lentils", "name": "Red Lentils (Dal)",
        "cho_g": 20, "prot_g": 9, "fat_g": 0.4, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 3.3,
        "role": "protein", "purchase_unit": "1 lb bag",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "chapati_roti", "name": "Whole Wheat Roti / Chapati",
        "cho_g": 18, "prot_g": 3, "fat_g": 1, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 1.2,
        "role": "carb", "purchase_unit": "pack of 10",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
    },
    {
        "food_id": "paneer_100g", "name": "Paneer",
        "cho_g": 3, "prot_g": 18, "fat_g": 20, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 0.2,
        "role": "protein", "purchase_unit": "200g block",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
    },
    {
        "food_id": "mango_fresh", "name": "Fresh Mango",
        "cho_g": 25, "prot_g": 1, "fat_g": 0.4, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 0.2,
        "role": "produce", "purchase_unit": "2-pack",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "basmati_rice", "name": "Basmati Rice",
        "cho_g": 45, "prot_g": 4, "fat_g": 0.5, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 0.4,
        "role": "carb", "purchase_unit": "5 lb bag",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    # ── Latino / Hispanic ────────────────────────────────────────
    {
        "food_id": "black_beans_can", "name": "Black Beans (canned)",
        "cho_g": 22, "prot_g": 8, "fat_g": 0.5, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 2.0,
        "role": "protein", "purchase_unit": "15 oz can",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "corn_tortillas", "name": "Corn Tortillas",
        "cho_g": 24, "prot_g": 2, "fat_g": 1, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 0.6,
        "role": "carb", "purchase_unit": "pack of 30",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "plantain_ripe", "name": "Ripe Plantains",
        "cho_g": 31, "prot_g": 1, "fat_g": 0.3, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 0.5,
        "role": "carb", "purchase_unit": "2-pack",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "pinto_beans_can", "name": "Pinto Beans (canned)",
        "cho_g": 22, "prot_g": 7, "fat_g": 0.5, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 1.8,
        "role": "protein", "purchase_unit": "15 oz can",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    # ── East Asian ───────────────────────────────────────────────
    {
        "food_id": "edamame_frozen", "name": "Edamame (frozen shelled)",
        "cho_g": 9, "prot_g": 11, "fat_g": 5, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 2.3,
        "role": "protein", "purchase_unit": "12 oz bag",
        "allergens": ["soy"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "tofu_firm", "name": "Firm Tofu",
        "cho_g": 2, "prot_g": 17, "fat_g": 9, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 3.0,
        "role": "protein", "purchase_unit": "14 oz block",
        "allergens": ["soy"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "rice_noodles", "name": "Rice Noodles",
        "cho_g": 42, "prot_g": 3, "fat_g": 0.3, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 0.2,
        "role": "carb", "purchase_unit": "14 oz bag",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "bok_choy", "name": "Bok Choy",
        "cho_g": 2, "prot_g": 1.5, "fat_g": 0.2, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 0.8,
        "role": "produce", "purchase_unit": "bunch",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    # ── Middle Eastern ───────────────────────────────────────────
    {
        "food_id": "hummus_store", "name": "Hummus",
        "cho_g": 14, "prot_g": 5, "fat_g": 9, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 1.4,
        "role": "fat", "purchase_unit": "10 oz tub",
        "allergens": ["sesame"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "pita_bread", "name": "Whole Wheat Pita",
        "cho_g": 33, "prot_g": 5, "fat_g": 1, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 1.5,
        "role": "carb", "purchase_unit": "pack of 6",
        "allergens": ["gluten"], "diet_tags": ["vegan", "vegetarian", "dairy_free"],
    },
    {
        "food_id": "medjool_dates", "name": "Medjool Dates",
        "cho_g": 36, "prot_g": 1, "fat_g": 0.3, "gi_tier": "fast",
        "ui_icon": "⚡", "iron_mg": 0.9,
        "role": "carb", "purchase_unit": "10 oz bag",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "labneh", "name": "Labneh (strained yogurt)",
        "cho_g": 4, "prot_g": 9, "fat_g": 7, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 0.1,
        "role": "protein", "purchase_unit": "8 oz tub",
        "allergens": ["dairy"], "diet_tags": ["vegetarian", "gluten_free"],
    },
    # ── African ──────────────────────────────────────────────────
    {
        "food_id": "plantain_green", "name": "Green Plantains",
        "cho_g": 28, "prot_g": 1, "fat_g": 0.3, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 0.5,
        "role": "carb", "purchase_unit": "2-pack",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "groundnut_paste", "name": "Natural Peanut Butter",
        "cho_g": 7, "prot_g": 8, "fat_g": 16, "gi_tier": "low",
        "ui_icon": "", "iron_mg": 0.6,
        "role": "fat", "purchase_unit": "16 oz jar",
        "allergens": ["peanuts"], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
    {
        "food_id": "cassava_flour", "name": "Cassava / Yuca",
        "cho_g": 38, "prot_g": 1, "fat_g": 0.3, "gi_tier": "medium",
        "ui_icon": "", "iron_mg": 0.3,
        "role": "carb", "purchase_unit": "2 lb bag",
        "allergens": [], "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
    },
]

# ── Window → allowed GI tiers ─────────────────────────────────────────────────
# Maps the normalized window key to the GI tiers the Fuel Finder will show.
GI_WINDOW_FILTER: dict[str, list[str]] = {
    "top_up":       ["fast"],
    "keep_going":   ["fast"],
    "fuel_before":  ["fast", "medium"],
    "recharge":     ["fast"],
    "rebuild":      ["fast", "medium", "slow"],
    "everyday_meal":["fast", "medium", "slow"],
}

# Fallback when a slot doesn't map to a known key — show everything.
_DEFAULT_TIERS = ["fast", "medium", "slow"]

# ── Slot-name normalizer ──────────────────────────────────────────────────────
# Maps the engine's slot_name strings to GI_WINDOW_FILTER keys.
# Suffix-tolerant: top_up_snack_1, fuel_after_primary_2, etc.
_SLOT_PREFIX_MAP: list[tuple[str, str]] = [
    ("top_up",          "top_up"),
    ("keep_going",      "keep_going"),
    ("pre_event_meal",  "fuel_before"),
    ("quick_morning",   "fuel_before"),
    ("fuel_after_primary", "recharge"),
    ("fuel_after_secondary","rebuild"),
    ("between_games",   "rebuild"),
    ("between_sessions","rebuild"),
    ("everyday",        "everyday_meal"),
]

def _normalize_slot(slot_name: str) -> str:
    """Return the GI_WINDOW_FILTER key for a given slot_name."""
    lower = (slot_name or "").lower()
    for prefix, key in _SLOT_PREFIX_MAP:
        if lower.startswith(prefix):
            return key
    return ""   # caller falls back to _DEFAULT_TIERS


# ── Public API ────────────────────────────────────────────────────────────────

def get_fuel_finder_foods(
    window: str,
    allergies: list[str] | None = None,
    diet_pref: str = "omnivore",
    iron_flag: bool = False,
) -> list[dict]:
    """
    Return filtered foods for a Fuel Finder window.

    Args:
        window:     slot_name from the window engine (e.g. 'top_up_snack', 'everyday_breakfast').
        allergies:  list of allergen strings to exclude (e.g. ['dairy', 'gluten']).
        diet_pref:  'omnivore' | 'vegan' | 'vegetarian' | 'gluten_free' | 'dairy_free'.
        iron_flag:  when True and window resolves to 'recharge', sort by iron_mg descending.

    Returns:
        List of food dicts (gi_tier field omitted — never expose to athlete).
    """
    normalized_key = _normalize_slot(window)
    allowed_tiers = GI_WINDOW_FILTER.get(normalized_key, _DEFAULT_TIERS)
    safe_allergies = [a.lower().strip() for a in (allergies or [])]

    results = [
        f for f in FOOD_DATABASE
        if f["gi_tier"] in allowed_tiers
        and not any(a in f.get("allergens", []) for a in safe_allergies)
        and (diet_pref == "omnivore" or diet_pref in f.get("diet_tags", []))
    ]

    if iron_flag and normalized_key == "recharge":
        results = sorted(results, key=lambda f: f.get("iron_mg", 0), reverse=True)

    # Strip internal gi_tier before returning — athletes never see GI data.
    return [{k: v for k, v in f.items() if k != "gi_tier"} for f in results]


# O(1) lookup index — built once at import time
_FOOD_INDEX: dict[str, dict] = {f["food_id"]: f for f in FOOD_DATABASE}


def get_food_by_id(food_id: str) -> dict | None:
    """Look up a single food record by food_id (gi_tier included for internal use)."""
    return _FOOD_INDEX.get(food_id)
