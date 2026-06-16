"""
RAG answer orchestration for the Nutrition Coach.
Bedrock answers ONLY from approved-organization knowledge excerpts.
"""

import logging
from typing import Optional

from api.services.bedrock_client import converse_text, is_configured, parse_json_from_llm
from api.services.knowledge.approved_sources import list_sources
from api.services.knowledge.retrieval import retrieve, KnowledgeChunk
from api.services.knowledge.calculations import (
    iron_rda, calcium_rda, protein_range, hydration_needs,
    pre_training_meal_window, post_training_recovery_window, calorie_estimate,
)

logger = logging.getLogger(__name__)

_FALLBACK = (
    "I don't have enough approved information from our trusted sports nutrition sources "
    "to answer that confidently. Please consult a registered sports dietitian or the "
    "athlete's physician for personalised guidance."
)

_SAFETY_TERMS = [
    "faint", "fainting", "unconscious", "chest pain", "can't breathe",
    "eating disorder", "purge", "starving", "stop eating", "lose weight fast",
    "anorexia", "bulimia", "binge", "severe dehydration", "seizure",
    "vomiting blood", "not eating",
]


_CLASSIFIER_SYSTEM = """You route Nutrition Coach questions for youth soccer athletes ages 9-17.

Choose exactly ONE path:
- "knowledge" — sports nutrition education, timing guidance, hydration advice, micronutrients, what types of foods to eat (without requesting a full recipe with ingredients), calculations, safety.
- "recipe" — user wants a concrete meal or snack recipe with ingredients and preparation steps, or asks to generate, create, make, build, or suggest a specific dish.

If path is "recipe", set recipe_category to the best match:
halftime | pre_game | post_game | breakfast | lunch | dinner | snack | hydration

Examples:
- "What should I eat before a game?" → knowledge
- "How much water on practice days?" → knowledge
- "Generate a halftime snack recipe" → recipe, halftime
- "Give me something to eat after the game" → recipe, post_game
- "Recipe for breakfast" → recipe, breakfast
- Recipe request with unclear timing → recipe, snack

Return ONLY valid JSON, no markdown:
{"path": "knowledge" | "recipe", "recipe_category": null | "category_key"}"""

_CALC_KEYWORDS = {
    "iron": lambda q, a: iron_rda(a.get("age", 14), a.get("gender", "female")),
    "calcium": lambda q, a: calcium_rda(a.get("age", 14)),
    "protein": lambda q, a: protein_range(a.get("weight_lbs", 120), a.get("event_type", "rest")),
    "hydration": lambda q, a: hydration_needs(a.get("weight_lbs", 120), a.get("event_type", "rest")),
    "water": lambda q, a: hydration_needs(a.get("weight_lbs", 120), a.get("event_type", "rest")),
    "calorie": lambda q, a: calorie_estimate(a.get("weight_lbs", 120), a.get("age", 14), a.get("gender", "female"), a.get("event_type", "rest")),
    "calories": lambda q, a: calorie_estimate(a.get("weight_lbs", 120), a.get("age", 14), a.get("gender", "female"), a.get("event_type", "rest")),
}


def _detect_safety_flag(question: str) -> bool:
    q = question.lower()
    return any(term in q for term in _SAFETY_TERMS)


def _classify_coach_path(question: str, athlete: dict) -> dict:
    """
    LLM router: choose knowledge RAG vs recipe generation.
    Returns {"path": "knowledge"|"recipe", "recipe_category": str|None}.
    """
    if not is_configured():
        return {"path": "knowledge", "recipe_category": None}

    first = athlete.get("first_name", "athlete")
    age = athlete.get("age", "unknown")
    user = f"Athlete: {first}, age {age}.\nQuestion: {question.strip()}"

    try:
        text = converse_text(
            system=_CLASSIFIER_SYSTEM,
            user=user,
            max_tokens=80,
            temperature=0.1,
        )
        parsed = parse_json_from_llm(text)
    except Exception:
        logger.exception("Coach path classification failed for question=%r", question[:80])
        return {"path": "knowledge", "recipe_category": None}

    path = parsed.get("path", "knowledge")
    if path not in ("knowledge", "recipe"):
        path = "knowledge"

    category = parsed.get("recipe_category")
    if path != "recipe":
        return {"path": "knowledge", "recipe_category": None}

    from api.services.recipe_categories import resolve_category

    try:
        resolved = resolve_category(category or "snack")
        return {"path": "recipe", "recipe_category": resolved["key"]}
    except ValueError:
        return {"path": "recipe", "recipe_category": "snack"}


def _parse_allergies(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return [a.strip() for a in raw if a and str(a).strip().lower() != "none"]
    return [a.strip() for a in str(raw).split(",") if a.strip().lower() != "none"]


def _parse_dietary(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return [d.strip() for d in raw if d and str(d).strip().lower() != "none"]
    return [d.strip() for d in str(raw).split(",") if d.strip().lower() != "none"]


def _answer_with_recipe(question: str, athlete: dict, category: str) -> dict:
    from api.services import recipe_generator
    from api.services.recipe_categories import resolve_category

    allergies = _parse_allergies(athlete.get("allergies"))
    dietary = _parse_dietary(athlete.get("dietary_restrictions"))

    try:
        result = recipe_generator.generate_recipe(
            category,
            allergies=allergies,
            dietary_restrictions=dietary,
            athlete=athlete,
        )
    except ValueError as e:
        return {
            "answer": f"I couldn't build a recipe for that category: {e}",
            "format": "markdown",
            "intent": "recipe",
            "recipe": None,
            "source_ingredients": [],
            "citations": [],
            "calculation": None,
            "sources": list_sources(),
        }
    except Exception:
        logger.exception("Recipe generation failed for category=%s", category)
        return {
            "answer": (
                "Sorry, I couldn't generate a recipe right now. "
                "Try again in a moment or ask a general fueling question."
            ),
            "format": "markdown",
            "intent": "recipe",
            "recipe": None,
            "source_ingredients": [],
            "citations": [],
            "calculation": None,
            "sources": list_sources(),
        }

    profile = resolve_category(category)
    first_name = athlete.get("first_name", "athlete")
    restriction_note = ""
    if allergies:
        restriction_note = f" It's free of your listed allergens ({', '.join(allergies)})."
    answer = (
        f"Here's a **{profile['label']}** recipe for {first_name} — "
        f"built from USDA-verified ingredients.{restriction_note}"
    )

    return {
        "answer": answer,
        "format": "markdown",
        "intent": "recipe",
        "recipe": result["recipe"],
        "source_ingredients": result.get("source_ingredients", []),
        "citations": [],
        "calculation": None,
        "sources": list_sources(),
    }


def _maybe_calculate(question: str, athlete: dict) -> Optional[dict]:
    q = question.lower()
    for keyword, fn in _CALC_KEYWORDS.items():
        if keyword in q:
            try:
                return fn(q, athlete)
            except Exception:
                return None
    return None


def _build_system_prompt(chunks: list, calc_result: Optional[dict]) -> str:
    chunks_text = ""
    if chunks:
        for i, c in enumerate(chunks, 1):
            heading = f" — {c.heading}" if c.heading else ""
            org = c.organization_name or c.source
            chunks_text += (
                f"\n[{i}] {c.title}{heading}\n"
                f"Organization: {org}\n"
                f"{c.content}\n"
            )
    else:
        chunks_text = "(No relevant knowledge excerpts found)"

    calc_text = ""
    if calc_result and "error" not in calc_result:
        calc_text = (
            f"\n\nCALCULATION RESULT (use this exact value — do not invent numbers):\n"
            f"{calc_result.get('explanation_hint', str(calc_result))}\n"
            f"Source: {calc_result.get('source', '')}"
        )

    return f"""You are FuelUp's Nutrition Coach for youth soccer athletes ages 9-17.

STRICT RULES — follow these exactly:
1. Answer ONLY from the knowledge excerpts provided below (from trusted sports nutrition organizations and live approved-site web results). Never invent nutritional values, formulas, or dosages.
2. If the excerpts do not contain enough information to answer, respond with exactly: "{_FALLBACK}"
3. Do NOT include inline source citations in your answer text — sources are shown separately in the app.
4. Write for a youth athlete aged 9-17 — keep language simple, supportive, and practical.
5. Whenever possible, give "what to do today" guidance.
6. NEVER provide medical diagnosis, treatment advice, or supplement dosing.
7. Never recommend supplements for athletes under 18.
8. For ANY of these situations — injury, fainting, chest pain, eating disorder, severe dehydration, signs of anorexia or bulimia, extreme restriction, unintentional weight loss — respond with: "This sounds like something important to discuss with a doctor or qualified sports dietitian. Please reach out to a professional right away."
9. Format your answer as **Markdown**:
   - Use **bold** for the main takeaway or action step
   - Use bullet lists (`- item`) when giving 2–4 practical tips
   - Keep paragraphs short (2–3 sentences max)
   - Do NOT use headings (`#`), code blocks, tables, or inline source citations
   - Plain sentences are fine when a list is not needed

KNOWLEDGE EXCERPTS:
{chunks_text}
{calc_text}"""


def _call_bedrock(system_prompt: str, user_question: str) -> str:
    if not is_configured():
        raise RuntimeError(
            "AWS Bedrock is not configured. Set AWS_REGION, AWS_ACCESS_KEY_ID, "
            "AWS_SECRET_ACCESS_KEY, and BEDROCK_MODEL_ID on the server."
        )
    return converse_text(system=system_prompt, user=user_question, max_tokens=512, temperature=0.3)


def _citations_from_chunks(chunks: list[KnowledgeChunk]) -> list[dict]:
    citations = []
    seen: set[str] = set()
    for c in chunks:
        key = f"{c.organization_id}:{c.title}"
        if key in seen:
            continue
        seen.add(key)
        page_url = c.source_urls[0] if c.source_urls else c.organization_url
        citations.append({
            "title": c.title,
            "source": c.organization_name or c.source,
            "organization_id": c.organization_id,
            "organization_name": c.organization_name,
            "organization_url": c.organization_url,
            "url": page_url,
            "heading": c.heading,
        })
    return citations


def answer_with_knowledge(question: str, athlete: dict) -> dict:
    """
    Main RAG entry point for the Nutrition Coach.
    Returns {"answer", "citations", "calculation", "sources"}.
    """
    if _detect_safety_flag(question):
        return {
            "answer": (
                "This sounds like something important to discuss with a doctor or "
                "qualified sports dietitian. Please reach out to a professional right away."
            ),
            "format": "markdown",
            "citations": [],
            "calculation": None,
            "safety_flag": True,
            "sources": list_sources(),
        }

    route = _classify_coach_path(question, athlete)
    if route["path"] == "recipe" and route["recipe_category"]:
        return _answer_with_recipe(question, athlete, route["recipe_category"])

    calc_result = _maybe_calculate(question, athlete)

    try:
        chunks = retrieve(question, top_n=5)
    except Exception:
        logger.exception("Knowledge retrieval failed for question=%r", question[:80])
        return {
            "answer": _FALLBACK,
            "format": "markdown",
            "citations": [],
            "calculation": calc_result,
            "sources": list_sources(),
        }

    if not chunks:
        return {
            "answer": _FALLBACK,
            "format": "markdown",
            "citations": [],
            "calculation": calc_result,
            "sources": list_sources(),
        }

    system_prompt = _build_system_prompt(chunks, calc_result)
    try:
        answer_text = _call_bedrock(system_prompt, question)
    except Exception:
        logger.exception("Bedrock call failed for Nutrition Coach")
        return {
            "answer": _FALLBACK,
            "format": "markdown",
            "citations": _citations_from_chunks(chunks),
            "calculation": calc_result,
            "sources": list_sources(),
        }

    return {
        "answer": answer_text,
        "format": "markdown",
        "citations": _citations_from_chunks(chunks),
        "calculation": calc_result,
        "sources": list_sources(),
    }
