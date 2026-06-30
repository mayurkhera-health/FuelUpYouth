import api.services.claude_ai as ai

ATHLETE = {"first_name": "A", "age": 15, "gender": "girl", "season_phase": "in_season", "food_preferences": "loves rice"}
SLOT_PLAN = {"week_summary": {"game_days": 1}, "slots": [
    {"meal_context": "pre_training_fuel", "count": 1, "roles": ["carb"], "gi_tier": "fast", "must_have": True},
]}
SAFE = [{"food_id": "rice", "name": "Rice", "role": "carb", "gi_tier": "fast", "purchase_unit": "bag", "diet_tags": [], "allergens": []}]

def test_prompt8_parses_valid_ai_json(monkeypatch):
    monkeypatch.setattr(ai, "converse_text", lambda **k: '{"items":[{"food_id":"rice","meal_context":"pre_training_fuel","must_have":true}],"reasoning":"Game week."}')
    monkeypatch.setattr(ai, "extract_json", lambda s: s)
    out = ai.prompt8_pantry_plan(ATHLETE, [], SLOT_PLAN, SAFE)
    assert out["items"][0]["food_id"] == "rice"
    assert out["reasoning"] == "Game week."

def test_prompt8_junk_returns_empty_fallback(monkeypatch):
    monkeypatch.setattr(ai, "converse_text", lambda **k: "not json")
    out = ai.prompt8_pantry_plan(ATHLETE, [], SLOT_PLAN, SAFE)
    assert out == {"items": [], "reasoning": ""}
