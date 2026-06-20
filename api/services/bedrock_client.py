"""AWS Bedrock Converse API client for FuelUp AI calls."""
import base64
import os
import re

import boto3
from botocore.config import Config

DEFAULT_BEDROCK_MODEL = "mistral.ministral-3-8b-instruct"


def _region() -> str:
    return os.getenv("AWS_REGION", "us-east-1")


def model_id() -> str:
    return os.getenv("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL)


def _client():
    return boto3.client(
        "bedrock-runtime",
        region_name=_region(),
        config=Config(
            read_timeout=30,
            connect_timeout=10,
            retries={"max_attempts": 0},
        ),
    )


def is_configured() -> bool:
    """True when default AWS credential chain is likely available."""
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_PROFILE")
        or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        or os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
        or os.getenv("AWS_ROLE_ARN")
    )


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


def _extract_text(response: dict) -> str:
    content = response.get("output", {}).get("message", {}).get("content") or []
    text = "".join(block.get("text", "") for block in content if "text" in block).strip()
    if not text:
        raise RuntimeError("Bedrock returned empty response")
    return text


def converse_text(
    *,
    user: str,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    kwargs: dict = {
        "modelId": model or model_id(),
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    return _extract_text(_client().converse(**kwargs))


def converse_multi_turn(
    *,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    """Send a multi-turn conversation. Each message: {"role": "user"|"assistant", "content": "..."}."""
    bedrock_messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]}
        for m in messages
    ]
    kwargs: dict = {
        "modelId": model or model_id(),
        "messages": bedrock_messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    return _extract_text(_client().converse(**kwargs))


def converse_vision(
    *,
    prompt: str,
    image_base64: str,
    media_type: str = "image/jpeg",
    max_tokens: int = 1024,
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    fmt = "png" if media_type == "image/png" else "jpeg"
    response = _client().converse(
        modelId=model or model_id(),
        messages=[
            {
                "role": "user",
                "content": [
                    {"text": prompt},
                    {
                        "image": {
                            "format": fmt,
                            "source": {"bytes": base64.b64decode(image_base64)},
                        }
                    },
                ],
            }
        ],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return _extract_text(response)
