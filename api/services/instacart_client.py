"""Instacart Developer Platform API client — low-level HTTP layer only.

Product: "Create shopping list page" (POST /idp/v1/products/products_link).
Docs verified 2026-07-15: https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page

This module does one thing: send an already-validated, already-mapped request
dict to Instacart and return the parsed JSON body, or raise a typed exception.
Request validation and domain mapping live in instacart_shopping_list.py — this
file has no knowledge of our internal item/request shapes.

No generic retry: Instacart does not document idempotency for this endpoint, so
retrying a creation POST risks Instacart-side side effects we can't reason about.
A single attempt with a short timeout is the safe default.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_DEV_BASE_URL = "https://connect.dev.instacart.tools"
_PROD_BASE_URL = "https://connect.instacart.com"
_CREATE_SHOPPING_LIST_PATH = "/idp/v1/products/products_link"

_TIMEOUT_SECONDS = 10

# Hostnames we trust a products_link_url to resolve to. Instacart's docs only
# document instacart.com properties for this response — anything else is treated
# as an unsafe/unexpected upstream response rather than relayed to the client.
TRUSTED_RESPONSE_HOSTS = ("instacart.com", "instacart.tools")


class InstacartError(Exception):
    """Base class for all Instacart client errors. Never includes the API key."""


class InstacartConfigError(InstacartError):
    """Missing/invalid local configuration (e.g. no API key set)."""


class InstacartAuthError(InstacartError):
    """Instacart rejected our API key (401/403)."""


class InstacartValidationError(InstacartError):
    """Instacart rejected the request body as invalid (400)."""

    def __init__(self, message: str, error_code=None, error_meta=None):
        super().__init__(message)
        self.error_code = error_code
        self.error_meta = error_meta


class InstacartRateLimitError(InstacartError):
    """Instacart returned 429."""


class InstacartUnavailableError(InstacartError):
    """Instacart returned a 5xx, or the response could not be parsed as JSON."""


class InstacartNetworkError(InstacartError):
    """DNS, TLS, connection, or timeout failure talking to Instacart."""


def instacart_shopping_list_enabled() -> bool:
    """Feature flag — ships dark. Flip INSTACART_SHOPPING_LIST_ENABLED=true (Fly
    secret) only after a real Developer Platform production key is configured."""
    return os.environ.get("INSTACART_SHOPPING_LIST_ENABLED", "false").lower() == "true"


def _api_key() -> str:
    key = os.getenv("INSTACART_API_KEY")
    if not key:
        raise InstacartConfigError(
            "INSTACART_API_KEY is required. See docs/instacart-integration.md for setup."
        )
    return key


def _base_url() -> str:
    """INSTACART_ENV selects the documented dev vs prod base URL. Do not allow
    this to be overridden by request input — it is operator-configured only."""
    env = os.environ.get("INSTACART_ENV", "development").strip().lower()
    if env == "production":
        return _PROD_BASE_URL
    return _DEV_BASE_URL


def create_shopping_list_page(payload: dict) -> dict:
    """POST the given (already validated/mapped) payload to Instacart's Create
    shopping list page endpoint. Returns the parsed JSON body on 200.

    Raises one of the InstacartError subclasses above on any failure. Callers
    must not surface raw exception text from network-layer errors to end users
    (str(e) may include host/path details) — map to a safe message instead.
    """
    url = f"{_base_url()}{_CREATE_SHOPPING_LIST_PATH}"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise InstacartNetworkError("Instacart request timed out") from exc
    except requests.RequestException as exc:
        # Covers DNS failure, TLS verification failure, connection refused, etc.
        # requests verifies TLS certificates by default; we never disable that.
        raise InstacartNetworkError("Instacart request failed") from exc

    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError as exc:
            raise InstacartUnavailableError("Instacart returned a non-JSON response") from exc

    if resp.status_code in (401, 403):
        logger.error("Instacart rejected our API key (status=%s)", resp.status_code)
        raise InstacartAuthError(f"Instacart authentication failed (status={resp.status_code})")

    if resp.status_code == 400:
        body = _safe_json(resp)
        error_code = body.get("error_code") if isinstance(body, dict) else None
        error_meta = body.get("error_meta") if isinstance(body, dict) else None
        message = (body.get("message") if isinstance(body, dict) else None) or "Instacart rejected the request"
        raise InstacartValidationError(message, error_code=error_code, error_meta=error_meta)

    if resp.status_code == 429:
        raise InstacartRateLimitError("Instacart rate limit exceeded")

    if 500 <= resp.status_code < 600:
        raise InstacartUnavailableError(f"Instacart server error (status={resp.status_code})")

    raise InstacartUnavailableError(f"Unexpected Instacart response (status={resp.status_code})")


def _safe_json(resp) -> dict:
    try:
        return resp.json()
    except ValueError:
        return {}
