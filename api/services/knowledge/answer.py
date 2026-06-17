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

_COACH_CAPABILITIES = """
WHAT YOU CAN HELP WITH:
- **Knowledge answers** — youth soccer sports nutrition from trusted organizations: fueling timing (pre-game, halftime, post-game, practice days), hydration, carbs/protein/recovery, iron and calcium for athletes, what *types* of foods fit a fueling window, and safe fueling habits. You can also use pre-calculated numbers when provided (iron, protein, hydration, calories).
- **Recipe recommendations** — suggest a science-backed meal or snack from FuelUp's curated recipe library for a fueling window: halftime, pre-game, post-game, breakfast, lunch, dinner, snack, or hydration. Valid library recipes are filtered for the athlete's allergies and dietary restrictions, then the best match is selected for what they asked.

WHAT YOU CANNOT DO:
- You do not invent new recipes — recommendations come only from FuelUp's curated recipe library.
- You do not know what is on the shelf at a specific store (Trader Joe's, Costco, etc.), a restaurant menu, or what is in someone's fridge unless they tell you.
- You do not have real-time or personal data (today's weather, their game schedule, their weight history).
- You are not a doctor — no diagnosis, treatment, or supplement recommendations for athletes under 18.
- You do not help with weight loss, calorie restriction, or non-nutrition topics.
""".strip()

_SAFETY_TERMS = [
    "faint", "fainting", "unconscious", "chest pain", "can't breathe",
    "eating disorder", "purge", "starving", "stop eating", "lose weight fast",
    "anorexia", "bulimia", "binge", "severe dehydration", "seizure",
    "vomiting blood", "not eating",
]


_CLASSIFIER_SYSTEM = f"""You route Nutrition Coach questions for youth soccer athletes ages 9-17.

Choose exactly ONE path:

- "knowledge" — Sports nutrition education: fueling timing, hydration, micronutrients, what *types* of foods fit a window, recovery, calculations, general fueling guidance. Use when the user asks WHY/WHEN/HOW MUCH or what to eat without asking for a full recipe with ingredients and steps.

- "recipe" — User wants a concrete meal or snack recommendation with ingredients, or asks to suggest, recommend, pick, find, or get a specific dish from our recipe library. If path is "recipe", set recipe_category to the best match:
  halftime | pre_game | post_game | breakfast | lunch | dinner | snack | hydration

- "out_of_scope" — The question cannot be answered by knowledge or recipe selection alone. Route here when:
  • Asking what to buy/eat at a specific store or restaurant WITHOUT listing what's available ("what should I get at Trader Joe's", "best things at Chipotle")
  • Real-time or personal info you don't have (weather, their schedule, what's in their pantry/fridge)
  • Non-nutrition topics (homework, sports scores, general chat)
  • Medical diagnosis, treatment, supplements for under-18, or weight-loss/dieting requests

  NOT out_of_scope if the user lists options and asks you to choose ("I have bananas and pretzels at home — which is better pre-game?") → knowledge
  NOT out_of_scope if they want a recipe from our library → recipe

{_COACH_CAPABILITIES}

Examples:
- "What should I eat before a game?" → knowledge
- "How much water on practice days?" → knowledge
- "Suggest a halftime snack" → recipe, halftime
- "Give me something to eat after the game" → recipe, post_game
- "What can I eat at Trader Joe's?" → out_of_scope
- "What's the best thing on the McDonald's menu?" → out_of_scope
- "I grabbed yogurt and a granola bar at Target — which for after practice?" → knowledge
- "Recommend a breakfast recipe" → recipe, breakfast

Return ONLY valid JSON, no markdown:
{{"path": "knowledge" | "recipe" | "out_of_scope", "recipe_category": null | "category_key"}}"""

_OUT_OF_SCOPE_SYSTEM = f"""You are FuelUp's Nutrition Coach for youth soccer athletes ages 9-17.

The athlete asked something outside what you can answer directly. Respond in a warm, conversational tone — never dismissive or rude. Briefly explain the limit in plain language, then invite them to rephrase or share details so you CAN help.

{_COACH_CAPABILITIES}

RESPONSE RULES:
1. Keep it to 2–4 short sentences. Use **bold** once for the key invite or next step.
2. Match the situation:
   - Store/restaurant without a menu list → say you don't know what's on their shelves or menu; ask them to tell you what's available and you'll help them pick the best fueling option.
   - Fridge/pantry unknown → ask what they have on hand.
   - Non-nutrition topic → gently say you're here for sports fueling questions and offer to help with food for their next practice or game.
   - Medical/weight-loss/supplements → encourage talking with a doctor or sports dietitian; do not give medical advice.
3. End with a friendly, specific invitation — not "I can't help."
4. Format as Markdown (bold + short paragraphs). No headings, lists, or citations.
5. Do NOT invent store inventory, menus, or personal data."""

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
    LLM router: choose knowledge RAG vs recipe library selection vs out-of-scope redirect.
    Returns {"path": "knowledge"|"recipe"|"out_of_scope", "recipe_category": str|None}.
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
    if path not in ("knowledge", "recipe", "out_of_scope"):
        path = "knowledge"

    if path == "out_of_scope":
        return {"path": "out_of_scope", "recipe_category": None}

    category = parsed.get("recipe_category")
    if path != "recipe":
        return {"path": "knowledge", "recipe_category": None}

    from api.services.recipe_categories import resolve_category

    try:
        resolved = resolve_category(category or "snack")
        return {"path": "recipe", "recipe_category": resolved["key"]}
    except ValueError:
        return {"path": "recipe", "recipe_category": "snack"}


def _answer_out_of_scope(question: str, athlete: dict) -> dict:
    """Friendly redirect when the question is outside knowledge/recipe capabilities."""
    first_name = athlete.get("first_name", "there")

    if not is_configured():
        return {
            "answer": (
                f"**I'm not sure I can answer that one directly, {first_name}.** "
                "I'm best at sports fueling questions and recommending recipes from our "
                "science-backed library for your practice and game windows. Try asking about "
                "what to eat before a game, how much water you need, or ask me to suggest "
                "a snack for halftime."
            ),
            "format": "markdown",
            "intent": "knowledge",
            "citations": [],
            "calculation": None,
            "sources": list_sources(),
        }

    user = f"Athlete's first name: {first_name}\nQuestion: {question.strip()}"
    try:
        answer_text = converse_text(
            system=_OUT_OF_SCOPE_SYSTEM,
            user=user,
            max_tokens=256,
            temperature=0.4,
        )
    except Exception:
        logger.exception("Out-of-scope response failed for question=%r", question[:80])
        answer_text = (
            f"**I can't see inside a specific store or menu, {first_name}** — but if you "
            "tell me what's available, I can help you pick the best fueling option. "
            "Or ask me about timing, hydration, or request a recipe recommendation "
            "for your next window."
        )

    return {
        "answer": answer_text,
        "format": "markdown",
        "intent": "knowledge",
        "citations": [],
        "calculation": None,
        "sources": list_sources(),
    }


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
            question=question,
        )
    except ValueError as e:
        return {
            "answer": f"I couldn't find a matching library recipe for that category: {e}",
            "format": "markdown",
            "intent": "recipe",
            "recipe": None,
            "source_ingredients": [],
            "citations": [],
            "calculation": None,
            "sources": list_sources(),
        }
    except Exception:
        logger.exception("Recipe selection failed for category=%s", category)
        return {
            "answer": (
                "Sorry, I couldn't recommend a recipe right now. "
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
        f"Here's a **{profile['label']}** pick for {first_name} — "
        f"from our science-backed recipe library.{restriction_note}"
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

YOUR CAPABILITIES:
{_COACH_CAPABILITIES}

STRICT RULES — follow these exactly:
1. Answer ONLY from the knowledge excerpts provided below (from trusted sports nutrition organizations and live approved-site web results). Never invent nutritional values, formulas, or dosages.
2. If the excerpts do not contain enough information to answer an in-scope sports nutrition question, respond with exactly: "{_FALLBACK}"
3. If the question asks about a specific store, restaurant, or menu without the athlete listing what's available, do NOT guess. Respond conversationally: say you don't know what's on their shelves or menu, ask them to share what's available, and offer to help them choose the best fueling option.
4. Do NOT include inline source citations in your answer text — sources are shown separately in the app.
5. Write for a youth athlete aged 9-17 — keep language simple, supportive, and practical. Be warm, never dismissive.
6. Whenever possible, give "what to do today" guidance.
7. NEVER provide medical diagnosis, treatment advice, or supplement dosing.
8. Never recommend supplements for athletes under 18.
9. For ANY of these situations — injury, fainting, chest pain, eating disorder, severe dehydration, signs of anorexia or bulimia, extreme restriction, unintentional weight loss — respond with: "This sounds like something important to discuss with a doctor or qualified sports dietitian. Please reach out to a professional right away."
10. Format your answer as **Markdown**:
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
    if route["path"] == "out_of_scope":
        return _answer_out_of_scope(question, athlete)
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
