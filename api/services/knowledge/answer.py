"""
RAG answer orchestration.
Bedrock receives retrieved knowledge chunks + optional calculation result.
Answers ONLY from the provided context.
"""

import json
from typing import Optional

from api.services.bedrock_client import converse_text, is_configured
from api.services.knowledge.retrieval import retrieve, KnowledgeChunk
from api.services.safety_filters import check_input_safe, check_output_safe
from api.services.knowledge.calculations import (
    iron_rda, calcium_rda, protein_range, hydration_needs,
    pre_training_meal_window, post_training_recovery_window, calorie_estimate,
)

_FALLBACK = (
    "That's a great question — honestly, I don't have enough information in my knowledge base right now to give "
    "you a confident answer on that one, and I'd rather be upfront with you than guess! "
    "For the most accurate guidance, please check with a registered sports dietitian or your team's medical staff. "
    "Every recommendation on FuelUp has been reviewed by registered dietitians, so if it's not in my knowledge "
    "base yet, a qualified professional will be your best next step. You deserve real answers, not guesses!"
)

_CALC_KEYWORDS = {
    "iron": lambda q, a: iron_rda(a.get("age", 14), a.get("gender", "female")),
    "calcium": lambda q, a: calcium_rda(a.get("age", 14)),
    "protein": lambda q, a: protein_range(a.get("weight_lbs", 120), a.get("event_type", "rest")),
    "hydration": lambda q, a: hydration_needs(a.get("weight_lbs", 120), a.get("event_type", "rest")),
    "water": lambda q, a: hydration_needs(a.get("weight_lbs", 120), a.get("event_type", "rest")),
    "calorie": lambda q, a: calorie_estimate(a.get("weight_lbs", 120), a.get("age", 14), a.get("gender", "female"), a.get("event_type", "rest")),
    "calories": lambda q, a: calorie_estimate(a.get("weight_lbs", 120), a.get("age", 14), a.get("gender", "female"), a.get("event_type", "rest")),
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


def _build_athlete_safety_block(athlete: dict) -> str:
    """
    Returns a hard-constraint block describing the athlete's profile.
    Claude must check every recommendation against this before answering.
    """
    name = athlete.get("first_name", "this athlete")
    age = athlete.get("age") or "unknown"
    gender = athlete.get("gender") or "unknown"
    weight = athlete.get("weight_lbs")
    position = athlete.get("position") or "soccer player"
    level = athlete.get("competition_level") or "youth"

    # Allergies stored as JSON array string e.g. '["peanuts","tree nuts"]'
    raw_allergies = athlete.get("allergies") or "[]"
    try:
        allergy_list = json.loads(raw_allergies) if isinstance(raw_allergies, str) else (raw_allergies or [])
    except Exception:
        allergy_list = []
    allergies_str = ", ".join(allergy_list) if allergy_list else "none reported"

    restrictions = (athlete.get("dietary_restrictions") or "").strip() or "none reported"
    supplements = (athlete.get("supplement_use") or "").strip() or "none"

    # Pull key baseline numbers from blueprint if available
    blueprint_note = ""
    raw_bp = athlete.get("blueprint_json")
    if raw_bp:
        try:
            bp = json.loads(raw_bp) if isinstance(raw_bp, str) else raw_bp
            rmr_text = bp.get("rmr", {}).get("athlete_explanation", "")
            macro_carbs = bp.get("macros", {}).get("carbs", {}).get("athlete_explanation", "")
            if rmr_text or macro_carbs:
                blueprint_note = (
                    "\nBLUEPRINT BASELINE:\n"
                    + (f"- RMR context: {rmr_text[:200]}\n" if rmr_text else "")
                    + (f"- Carb guidance: {macro_carbs[:200]}\n" if macro_carbs else "")
                )
        except Exception:
            pass

    weight_str = f"{weight} lbs" if weight else "unknown"

    return f"""ATHLETE PROFILE — CHECK EVERY RECOMMENDATION AGAINST THIS BEFORE ANSWERING:
Athlete: {name}, age {age}, {gender}, {weight_str}, {level} {position}
Confirmed allergies: {allergies_str}
Dietary restrictions: {restrictions}
Supplement use: {supplements}
{blueprint_note}
HARD CONSTRAINTS (non-negotiable):
- NEVER suggest any food or ingredient that matches the athlete's confirmed allergies. If the question or answer involves those ingredients, explicitly warn that they must be avoided and suggest a safe alternative.
- NEVER suggest anything that conflicts with the athlete's dietary restrictions.
- NEVER recommend supplements, powders, or performance-enhancing products — this athlete is under 18.
- Tailor quantities and timing to this athlete's age, weight, and competition level.
- If you cannot give safe advice given these constraints, say so clearly and recommend consulting a registered sports dietitian."""


def _build_personalization_block(athlete: dict) -> str:
    """
    Extracts blueprint-backed macro/micro focus points to give Claude
    enough context to open with one personalised sentence.
    Only injected on the first message of a thread.
    """
    name = athlete.get("first_name", "this athlete")
    position = athlete.get("position") or "soccer player"
    level = athlete.get("competition_level") or "youth"

    carb_line = protein_line = ""
    priority_micros: list[str] = []

    raw_bp = athlete.get("blueprint_json")
    if raw_bp:
        try:
            bp = json.loads(raw_bp) if isinstance(raw_bp, str) else raw_bp
            macros = bp.get("macros", {})
            carb_line = macros.get("carbs", {}).get("athlete_explanation", "")[:180]
            protein_line = macros.get("protein", {}).get("athlete_explanation", "")[:180]
            micros = bp.get("micronutrients", {})
            # Surface only the critical/important micros so the opener is relevant
            for micro, data in micros.items():
                if isinstance(data, dict) and data.get("urgency_level") in ("critical", "important"):
                    priority_micros.append(micro)
        except Exception:
            pass

    micro_note = f"Priority micronutrients for this athlete: {', '.join(priority_micros)}." if priority_micros else ""

    return (
        f"FIRST MESSAGE PERSONALISATION:\n"
        f"This is the first question {name} has asked in this conversation. "
        f"Begin your response with exactly ONE warm, personal sentence that references their "
        f"specific profile — they are a {level} {position}. "
        f"Draw on whichever of the following blueprint points is most relevant to the question:\n"
        f"- Carbs: {carb_line}\n"
        f"- Protein: {protein_line}\n"
        f"- {micro_note}\n"
        f"Rules for the opening sentence: use {name}'s name, reference their role (position/level), "
        f"and connect their specific nutritional focus to the question topic. "
        f"Do NOT mention raw numbers, grams, or calories. One sentence only — then answer the question normally."
    )


def _build_system_prompt(
    chunks: list,
    calc_result: Optional[dict],
    athlete: dict,
    is_first_message: bool = False,
) -> str:
    athlete_block = _build_athlete_safety_block(athlete)
    personalization_block = _build_personalization_block(athlete) if is_first_message else ""

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

    personalization_section = f"\n{personalization_block}\n" if personalization_block else ""

    return f"""You are FuelUp's nutrition coach for young soccer athletes ages 9–17.
Your job is to be their most encouraging, knowledgeable, and trustworthy guide on the field of nutrition.

{athlete_block}
{personalization_section}
TONE AND BEHAVIOR — these rules apply to every single response, no exceptions:
- You are speaking to a young teenager who is working hard at their sport. Always be warm, positive, and genuinely encouraging. Celebrate their effort and curiosity.
- If the athlete uses angry, frustrated, or inappropriate language — do NOT mirror it. Stay calm, kind, and professional at all times. Gently redirect the conversation back to how you can help them. Never lecture them about their language; simply model the right tone.
- Keep language simple, energetic, and relatable for a 13–17-year-old athlete. Avoid clinical or overly technical phrasing.
- Whenever possible, frame guidance as a "win" — what they CAN do, not what they can't.

CREDIBILITY — state this naturally when relevant, not robotically on every message:
- All FuelUp nutrition recommendations and recipes are reviewed and approved by registered dietitians. When an athlete asks whether the advice is trustworthy or AI-generated, reassure them clearly: "Everything you see on FuelUp is reviewed by registered dietitians — this isn't random AI advice, it's real sports nutrition guidance you can trust."

STRICT RULES — follow these exactly:
1. Answer ONLY from the knowledge excerpts provided below. Never invent nutritional values, formulas, or dosages not present in the excerpts.
2. HONESTY OVER GUESSING — If the excerpts do not contain enough information to answer confidently, do NOT guess or hallucinate an answer. Instead say warmly but clearly: "Honestly, I don't have a confident answer for that one in my knowledge base right now, and I'd rather be upfront than guess! All FuelUp guidance is reviewed by registered dietitians — for this specific question, your best move is to check with a qualified sports dietitian or your team's medical staff. You deserve a real answer, not a guess!"
3. End every answer with: "Source: [title of the knowledge item you used]"
4. Whenever possible, give "what to do today" guidance — make it practical and actionable.
5. NEVER provide medical diagnosis, treatment advice, or supplement dosing.
6. For ANY of these situations — injury, fainting, chest pain, eating disorder, severe dehydration, signs of anorexia or bulimia, extreme restriction, unintentional weight loss — respond with: "Hey, that sounds like something really important to talk to a doctor or registered sports dietitian about. Please reach out to a professional right away — they're there to help you!"

KNOWLEDGE EXCERPTS:
{chunks_text}
{calc_text}"""


def _call_bedrock(system_prompt: str, user_question: str) -> str:
    return converse_text(system=system_prompt, user=user_question, max_tokens=600, temperature=0.5)


def answer_with_knowledge(question: str, athlete: dict, is_first_message: bool = False) -> dict:
    """
    Main RAG entry point.
    Returns {"answer": str, "citations": list, "calculation": dict|None}.
    is_first_message=True adds a one-time personalised opener drawn from the athlete's blueprint.
    """
    # Layer 1 — input filter (model never called if this fires)
    blocked = check_input_safe(question)
    if blocked:
        return {"answer": blocked, "citations": [], "calculation": None, "safety_flag": True}

    calc_result = _maybe_calculate(question, athlete)
    chunks = retrieve(question, top_n=5)

    if not chunks:
        return {
            "answer": _FALLBACK,
            "citations": [],
            "calculation": calc_result,
        }

    if not is_configured():
        return {
            "answer": "The FuelUp Coach isn't available right now — please check back shortly or consult your team's dietitian.",
            "citations": [],
            "calculation": calc_result,
        }

    system_prompt = _build_system_prompt(chunks, calc_result, athlete, is_first_message)
    answer_text = _call_bedrock(system_prompt, question)

    # Layer 2 — output filter (model response discarded if this fires)
    blocked = check_output_safe(answer_text)
    if blocked:
        return {"answer": blocked, "citations": [], "calculation": calc_result, "safety_flag": True}

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
