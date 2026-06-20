"""Embedding helpers for Nutrition Coach retrieval."""

from __future__ import annotations

import json
import math

from api.services.bedrock_client import embed_model_id, embed_text as bedrock_embed_text

EMBEDDING_MODEL = embed_model_id()


def embed_text(text: str) -> list[float]:
    return bedrock_embed_text(text)


def pack_embedding(vector: list[float]) -> str:
    return json.dumps(vector)


def unpack_embedding(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    return [float(x) for x in data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
