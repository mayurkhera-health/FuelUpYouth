"""LLM client for FuelUp AI calls.

Chat / vision / JSON-completion calls go to Kimi (Moonshot AI), an
OpenAI-compatible API. Embeddings stay on AWS Bedrock (Titan) — Kimi has no
embeddings endpoint. Module name kept as `bedrock_client` since ~10 call
sites import from it; renaming is a separate cleanup, not part of this swap.
"""
import base64
import json
import os
import re

import boto3
import requests
from botocore.config import Config

DEFAULT_KIMI_MODEL = "kimi-k2.5"
DEFAULT_KIMI_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"


# ── Kimi (chat / vision / JSON completions) ────────────────────────────────────

def _kimi_base_url() -> str:
    return os.getenv("KIMI_BASE_URL", DEFAULT_KIMI_BASE_URL)


def model_id() -> str:
    return os.getenv("KIMI_MODEL_ID", DEFAULT_KIMI_MODEL)


def is_configured() -> bool:
    """True when a Kimi API key is set. Gates every chat/vision/JSON call."""
    return bool(os.getenv("KIMI_API_KEY"))


def _kimi_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('KIMI_API_KEY', '')}",
        "Content-Type": "application/json",
    }


def _kimi_chat(
    *,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    model: str | None = None,
) -> str:
    """POST to Kimi's OpenAI-compatible /chat/completions. One retry on
    transient failures (timeout, 5xx, 429) — mirrors the old Bedrock
    standard-mode config (max_attempts=2 total == one retry)."""
    payload = {
        "model": model or model_id(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            resp = requests.post(
                f"{_kimi_base_url()}/chat/completions",
                headers=_kimi_headers(),
                json=payload,
                timeout=(10, 30),  # (connect, read) — matches old Bedrock config
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"Kimi transient error {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if not text:
                raise RuntimeError("Kimi returned empty response")
            return text
        except Exception as e:
            last_exc = e
            if attempt == 0:
                continue
            raise
    raise last_exc  # unreachable — loop always returns or raises


# ── Embeddings (AWS Bedrock — Kimi has no embeddings API) ──────────────────────

def _region() -> str:
    return os.getenv("AWS_REGION", "us-east-1")


def embed_model_id() -> str:
    return os.getenv("BEDROCK_EMBED_MODEL_ID", DEFAULT_EMBED_MODEL)


def embeddings_configured() -> bool:
    """True when AWS Bedrock credentials are available for embeddings."""
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_PROFILE")
        or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        or os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
        or os.getenv("AWS_ROLE_ARN")
    )


def _bedrock_config() -> Config:
    # max_attempts is TOTAL attempts in "standard" mode → 2 means one retry.
    # Standard mode retries only transient errors (throttling, 5xx, timeouts).
    return Config(
        read_timeout=30,
        connect_timeout=10,
        retries={"max_attempts": 2, "mode": "standard"},
    )


def _client():
    return boto3.client(
        "bedrock-runtime",
        region_name=_region(),
        config=_bedrock_config(),
    )


def embed_text(text: str, *, model: str | None = None) -> list[float]:
    """Return a dense embedding vector for semantic retrieval."""
    trimmed = (text or "").strip()
    if not trimmed:
        raise ValueError("Cannot embed empty text")

    response = _client().invoke_model(
        modelId=model or embed_model_id(),
        body=json.dumps({"inputText": trimmed[:8000]}),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    vector = payload.get("embedding")
    if not vector:
        raise RuntimeError("Bedrock embedding response missing 'embedding'")
    return vector


# ── JSON parsing helpers (provider-agnostic) ────────────────────────────────────

def extract_json(text: str) -> str:
    raw = text.strip()
    if raw.startswith("{") or raw.startswith("["):
        return raw
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        return raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        return match.group(1).strip()
    return raw


def _sanitize_json_string_literals(json_str: str) -> str:
    """Escape raw newlines/tabs/control chars inside JSON string literals."""
    result: list[str] = []
    in_string = False
    escaped = False

    for ch in json_str:
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == "\\":
            result.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == "\n":
                result.append("\\n")
                continue
            if ch == "\r":
                result.append("\\r")
                continue
            if ch == "\t":
                result.append("\\t")
                continue
            if ord(ch) < 32:
                continue
        result.append(ch)

    return "".join(result)


def parse_json_from_llm(text: str):
    """Parse JSON from an LLM response, repairing common formatting mistakes."""
    raw = extract_json(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_sanitize_json_string_literals(raw))


# ── Anthropic fallback (used when Kimi is not configured) ──────────────────────

def _anthropic_converse(
    *,
    user: str,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """Fallback: Anthropic Claude when Kimi credentials are absent."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    kwargs: dict = {
        "model": os.getenv("ANTHROPIC_COACH_MODEL", "claude-haiku-4-5-20251001"),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _anthropic_converse_multi_turn(
    *,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """Fallback: Anthropic Claude for multi-turn conversations when Kimi is absent."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    kwargs: dict = {
        "model": os.getenv("ANTHROPIC_COACH_MODEL", "claude-haiku-4-5-20251001"),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


# ── Public call surface (unchanged signatures — every caller is untouched) ─────

def converse_text(
    *,
    user: str,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    if not is_configured():
        return _anthropic_converse(user=user, system=system, max_tokens=max_tokens, temperature=temperature)
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    return _kimi_chat(messages=messages, max_tokens=max_tokens, temperature=temperature, model=model)


def converse_multi_turn(
    *,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    """Send a multi-turn conversation. Each message: {"role": "user"|"assistant", "content": "..."}."""
    if not is_configured():
        return _anthropic_converse_multi_turn(
            messages=messages, system=system, max_tokens=max_tokens, temperature=temperature
        )
    kimi_messages: list[dict] = []
    if system:
        kimi_messages.append({"role": "system", "content": system})
    kimi_messages.extend({"role": m["role"], "content": m["content"]} for m in messages)
    try:
        return _kimi_chat(messages=kimi_messages, max_tokens=max_tokens, temperature=temperature, model=model)
    except Exception:
        return _anthropic_converse_multi_turn(
            messages=messages, system=system, max_tokens=max_tokens, temperature=temperature
        )


def converse_vision(
    *,
    prompt: str,
    image_base64: str,
    media_type: str = "image/jpeg",
    max_tokens: int = 1024,
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}"}},
            ],
        }
    ]
    return _kimi_chat(messages=messages, max_tokens=max_tokens, temperature=temperature, model=model)
