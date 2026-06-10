"""
RAG answer orchestration.
Claude receives retrieved knowledge chunks + optional calculation result.
Claude answers ONLY from the provided context.
"""

from typing import Optional

import anthropic

from api.services.knowledge.retrieval import retrieve, KnowledgeChunk
from api.services.knowledge.calculations import (
    iron_rda, calcium_rda, protein_range, hydration_needs,
    pre_training_meal_window, post_training_recovery_window, calorie_estimate,
)

_FALLBACK = "I don't have enough approved information to answer that confidently. Please consult a registered sports dietitian or the athlete's physician for personalised guidance."

_SAFETY_TERMS = [
    "faint", "fainting", "unconscious", "chest pain", "can't breathe",
    "eating disorder", "purge", "starving", "stop eating", "lose weight fast",
    "anorexia", "bulimia", "binge", "severe dehydration", "seizure",
    "vomiting blood", "not eating",
]

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
            chunks_text += f"\n[{i}] {c.title}{heading} (Source: {c.source})\n{c.content}\n"
    else:
        chunks_text = "(No relevant knowledge excerpts found)"

    calc_text = ""
    if calc_result and "error" not in calc_result:
        calc_text = (
            f"\n\nCALCULATION RESULT (use this exact value — do not invent numbers):\n"
            f"{calc_result.get('explanation_hint', str(calc_result))}\n"
            f"Source: {calc_result.get('source', '')}"
        )

    return f"""You are FuelUp's nutrition assistant for youth soccer athletes ages 9-17.

STRICT RULES — follow these exactly:
1. Answer ONLY from the knowledge excerpts provided below. Never invent nutritional values, formulas, or dosages not present in the excerpts.
2. If the excerpts do not contain enough information to answer, respond with exactly: "{_FALLBACK}"
3. End every answer with: "Source: [title of the knowledge item you used]"
4. Write for a youth athlete aged 9-17 — keep language simple, supportive, and practical.
5. Whenever possible, give "what to do today" guidance.
6. NEVER provide medical diagnosis, treatment advice, or supplement dosing.
7. For ANY of these situations — injury, fainting, chest pain, eating disorder, severe dehydration, signs of anorexia or bulimia, extreme restriction, unintentional weight loss — respond with: "This sounds like something important to discuss with a doctor or qualified sports dietitian. Please reach out to a professional right away."

KNOWLEDGE EXCERPTS:
{chunks_text}
{calc_text}"""


def _call_claude(system_prompt: str, user_question: str) -> str:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_question}],
    )
    return message.content[0].text


def answer_with_knowledge(question: str, athlete: dict) -> dict:
    """
    Main RAG entry point.
    Returns {"answer": str, "citations": list, "calculation": dict|None}.
    """
    if _detect_safety_flag(question):
        return {
            "answer": "This sounds like something important to discuss with a doctor or qualified sports dietitian. Please reach out to a professional right away.",
            "citations": [],
            "calculation": None,
            "safety_flag": True,
        }

    calc_result = _maybe_calculate(question, athlete)
    chunks = retrieve(question, top_n=5)

    if not chunks:
        return {
            "answer": _FALLBACK,
            "citations": [],
            "calculation": calc_result,
        }

    system_prompt = _build_system_prompt(chunks, calc_result)
    answer_text = _call_claude(system_prompt, question)

    citations = [
        {
            "title": c.title,
            "source": c.source,
            "url": c.source_urls[0] if c.source_urls else None,
            "heading": c.heading,
        }
        for c in chunks
    ]
    seen = set()
    unique_citations = []
    for cit in citations:
        if cit["title"] not in seen:
            seen.add(cit["title"])
            unique_citations.append(cit)

    return {
        "answer": answer_text,
        "citations": unique_citations,
        "calculation": calc_result,
    }
