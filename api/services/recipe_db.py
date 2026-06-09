RECIPES = [
    # Pre-game meals (3hrs before) — R001-R005
    {"id": "R001", "name": "Power Pasta Bowl", "category": "pre-game", "timing": "3hrs before game", "ingredients": "Pasta, tomato sauce, grilled chicken, parmesan, spinach, milk", "macros": {"calories": 650, "carbs_g": 85, "protein_g": 45, "fat_g": 12}, "dietary": ["halal-adaptable"], "allergens": ["gluten", "dairy"]},
    {"id": "R002", "name": "Brown Rice Salmon Bowl", "category": "pre-game", "timing": "3hrs before game", "ingredients": "Brown rice, grilled salmon, edamame, avocado, cucumber, soy sauce", "macros": {"calories": 580, "carbs_g": 72, "protein_g": 38, "fat_g": 18}, "dietary": ["gluten-free-adaptable"], "allergens": ["fish", "soy"]},
    {"id": "R003", "name": "Turkey Wrap", "category": "pre-game", "timing": "3hrs before game", "ingredients": "Whole wheat tortilla, turkey breast, hummus, lettuce, tomato, low-fat cheese", "macros": {"calories": 520, "carbs_g": 65, "protein_g": 38, "fat_g": 14}, "dietary": [], "allergens": ["gluten", "dairy"]},
    {"id": "R004", "name": "Vegan Power Pasta", "category": "pre-game", "timing": "3hrs before game", "ingredients": "Pasta, marinara, white beans, nutritional yeast, spinach, olive oil", "macros": {"calories": 600, "carbs_g": 90, "protein_g": 28, "fat_g": 10}, "dietary": ["vegan", "vegetarian"], "allergens": ["gluten"]},
    {"id": "R005", "name": "Egg + Sweet Potato Bowl", "category": "pre-game", "timing": "3hrs before game", "ingredients": "Sweet potato, scrambled eggs, spinach, whole grain toast, OJ", "macros": {"calories": 540, "carbs_g": 70, "protein_g": 28, "fat_g": 16}, "dietary": ["vegetarian", "gluten-free-adaptable"], "allergens": ["eggs", "gluten"]},
    # Pre-game snacks (30-60min) — R006-R009
    {"id": "R006", "name": "Banana + PB", "category": "pre-game-snack", "timing": "30-60min before", "ingredients": "1 large banana, 2 tbsp peanut butter", "macros": {"calories": 280, "carbs_g": 36, "protein_g": 8, "fat_g": 12}, "dietary": ["vegan", "gluten-free"], "allergens": ["peanuts"]},
    {"id": "R007", "name": "Toast + Honey + Milk", "category": "pre-game-snack", "timing": "30-60min before", "ingredients": "2 slices whole grain toast, 2 tbsp honey, 8oz low-fat milk", "macros": {"calories": 310, "carbs_g": 55, "protein_g": 12, "fat_g": 4}, "dietary": ["vegetarian"], "allergens": ["gluten", "dairy"]},
    {"id": "R008", "name": "Greek Yogurt Parfait", "category": "pre-game-snack", "timing": "60min before", "ingredients": "Greek yogurt, granola, banana, honey", "macros": {"calories": 320, "carbs_g": 52, "protein_g": 16, "fat_g": 6}, "dietary": ["vegetarian", "gluten-free-adaptable"], "allergens": ["dairy", "gluten"]},
    {"id": "R009", "name": "Rice Cakes + Almond Butter", "category": "pre-game-snack", "timing": "30-60min before", "ingredients": "3 rice cakes, 2 tbsp almond butter, drizzle honey", "macros": {"calories": 270, "carbs_g": 38, "protein_g": 6, "fat_g": 11}, "dietary": ["vegan", "gluten-free"], "allergens": ["tree nuts"]},
    # Halftime quick fuel — R010-R012
    {"id": "R010", "name": "Orange Slices + Water", "category": "halftime", "timing": "Halftime", "ingredients": "2 oranges (sliced), 16oz cold water", "macros": {"calories": 85, "carbs_g": 22, "protein_g": 1, "fat_g": 0}, "dietary": ["vegan", "gluten-free"], "allergens": []},
    {"id": "R011", "name": "Banana + Natural Sports Drink", "category": "halftime", "timing": "Halftime", "ingredients": "1 banana, 16oz natural sports drink (no artificial dyes)", "macros": {"calories": 180, "carbs_g": 44, "protein_g": 1, "fat_g": 0}, "dietary": ["vegan", "gluten-free"], "allergens": []},
    {"id": "R012", "name": "Medjool Dates + Water", "category": "halftime", "timing": "Halftime", "ingredients": "4 Medjool dates, 16oz water", "macros": {"calories": 240, "carbs_g": 64, "protein_g": 2, "fat_g": 0}, "dietary": ["vegan", "gluten-free", "halal"], "allergens": []},
    # Post-game recovery (within 30min) — R013-R017
    {"id": "R013", "name": "Chocolate Milk Recovery", "category": "post-game-recovery", "timing": "Within 30min", "ingredients": "16oz low-fat chocolate milk, 1 banana", "macros": {"calories": 340, "carbs_g": 58, "protein_g": 16, "fat_g": 5}, "dietary": ["vegetarian", "gluten-free"], "allergens": ["dairy"]},
    {"id": "R014", "name": "PB&J + Milk", "category": "post-game-recovery", "timing": "Within 30min", "ingredients": "PB&J sandwich on whole grain, 8oz milk", "macros": {"calories": 420, "carbs_g": 52, "protein_g": 16, "fat_g": 16}, "dietary": ["vegetarian"], "allergens": ["gluten", "dairy", "peanuts"]},
    {"id": "R015", "name": "Tuna + Crackers", "category": "post-game-recovery", "timing": "Within 30min", "ingredients": "1 can tuna, whole grain crackers, 8oz milk", "macros": {"calories": 350, "carbs_g": 38, "protein_g": 32, "fat_g": 6}, "dietary": ["gluten-free-adaptable"], "allergens": ["fish", "gluten", "dairy"]},
    {"id": "R016", "name": "Vegan Recovery Smoothie", "category": "post-game-recovery", "timing": "Within 30min", "ingredients": "Plant protein powder, banana, oat milk, frozen berries, flaxseed", "macros": {"calories": 380, "carbs_g": 52, "protein_g": 24, "fat_g": 8}, "dietary": ["vegan", "gluten-free"], "allergens": []},
    {"id": "R017", "name": "Cottage Cheese + Pineapple", "category": "post-game-recovery", "timing": "Bedtime casein snack", "ingredients": "1 cup cottage cheese, 1/2 cup pineapple, drizzle honey", "macros": {"calories": 250, "carbs_g": 28, "protein_g": 28, "fat_g": 4}, "dietary": ["vegetarian", "gluten-free"], "allergens": ["dairy"]},
    # Practice day meals — R018-R022
    {"id": "R018", "name": "Pre-Practice Oatmeal Bowl", "category": "practice", "timing": "2-3hrs before practice", "ingredients": "Rolled oats, banana, peanut butter, honey, milk, chia seeds", "macros": {"calories": 480, "carbs_g": 68, "protein_g": 18, "fat_g": 14}, "dietary": ["vegetarian", "gluten-free-adaptable"], "allergens": ["dairy", "peanuts", "gluten"]},
    {"id": "R019", "name": "Post-Practice Rebuild Plate", "category": "practice", "timing": "Within 30min after practice", "ingredients": "Chicken breast, brown rice, roasted broccoli, low-fat milk, olive oil", "macros": {"calories": 580, "carbs_g": 62, "protein_g": 46, "fat_g": 14}, "dietary": ["gluten-free", "halal"], "allergens": ["dairy"]},
    {"id": "R020", "name": "Iron-Boost Hummus Plate", "category": "practice", "timing": "Lunch or snack", "ingredients": "Hummus, spinach, lentils, pita, bell peppers, lemon juice", "macros": {"calories": 420, "carbs_g": 52, "protein_g": 18, "fat_g": 14, "iron_mg": 8}, "dietary": ["vegan", "vegetarian", "halal"], "allergens": ["gluten", "sesame"]},
    {"id": "R021", "name": "Salmon Fried Rice", "category": "practice", "timing": "Dinner", "ingredients": "Brown rice, salmon, eggs, edamame, carrots, soy sauce, sesame oil", "macros": {"calories": 620, "carbs_g": 58, "protein_g": 42, "fat_g": 18}, "dietary": ["gluten-free-adaptable"], "allergens": ["fish", "eggs", "soy"]},
    {"id": "R022", "name": "Strength Day Protein Plate", "category": "strength", "timing": "Post-strength training", "ingredients": "Grilled chicken, quinoa, roasted sweet potato, Greek yogurt dip, spinach", "macros": {"calories": 640, "carbs_g": 60, "protein_g": 52, "fat_g": 12}, "dietary": ["gluten-free"], "allergens": ["dairy"]},
    # Tournament multi-day — R023-R026
    {"id": "R023", "name": "Tournament Morning Plate", "category": "tournament", "timing": "2-3hrs before first game", "ingredients": "Oatmeal pancakes, scrambled eggs, OJ, banana, honey", "macros": {"calories": 680, "carbs_g": 95, "protein_g": 28, "fat_g": 14}, "dietary": ["vegetarian"], "allergens": ["gluten", "eggs", "dairy"]},
    {"id": "R024", "name": "Between-Games Refuel", "category": "tournament", "timing": "Between tournament games", "ingredients": "Banana, natural sports drink, whole grain crackers, peanut butter", "macros": {"calories": 380, "carbs_g": 62, "protein_g": 10, "fat_g": 10}, "dietary": ["vegan"], "allergens": ["gluten", "peanuts"]},
    {"id": "R025", "name": "Tournament Recovery Dinner", "category": "tournament", "timing": "Tournament evening", "ingredients": "Pasta, ground turkey, marinara, parmesan, side salad, milk", "macros": {"calories": 720, "carbs_g": 82, "protein_g": 48, "fat_g": 16}, "dietary": ["halal-adaptable"], "allergens": ["gluten", "dairy"]},
    {"id": "R026", "name": "Bedtime Casein Snack", "category": "tournament", "timing": "Bedtime", "ingredients": "Greek yogurt, granola, honey, walnuts", "macros": {"calories": 320, "carbs_g": 38, "protein_g": 20, "fat_g": 10}, "dietary": ["vegetarian"], "allergens": ["dairy", "gluten", "tree nuts"]},
    # Meal prep — R027-R028
    {"id": "R027", "name": "Batch Chicken + Rice + Veggies", "category": "meal-prep", "timing": "Meal prep — 6 servings", "ingredients": "Chicken breast, brown rice, broccoli, bell peppers, olive oil, garlic, lemon", "macros": {"calories": 480, "carbs_g": 48, "protein_g": 42, "fat_g": 10}, "dietary": ["gluten-free", "halal"], "allergens": []},
    {"id": "R028", "name": "Tournament Week Prep Bowl", "category": "meal-prep", "timing": "Meal prep — tournament week", "ingredients": "Quinoa, black beans, corn, chicken, avocado, lime, cilantro", "macros": {"calories": 520, "carbs_g": 58, "protein_g": 36, "fat_g": 16}, "dietary": ["gluten-free", "halal"], "allergens": []},
]

TIMING_CATEGORIES = ["pre-game", "pre-game-snack", "halftime", "post-game-recovery", "practice", "strength", "tournament", "meal-prep"]


def get_recipes(category: str = None, dietary: list = None, allergens_to_avoid: list = None) -> list:
    results = RECIPES
    if category:
        results = [r for r in results if r["category"] == category]
    if dietary:
        results = [r for r in results if any(d in r["dietary"] for d in dietary)]
    if allergens_to_avoid:
        results = [r for r in results if not any(a in r["allergens"] for a in allergens_to_avoid)]
    return results


def get_recipe_by_id(recipe_id: str) -> dict:
    return next((r for r in RECIPES if r["id"] == recipe_id), None)
