"""Domain layer for the Instacart shopping-list handoff.

Maps our internal grocery-list shape to Instacart's documented
"Create shopping list page" request schema, validates everything before it
leaves our server, and validates the URL Instacart hands back before we relay
it to the client.

Field-level facts (units, UPC format, health filters, quantity>0, the
product_ids/upcs exclusivity rule, and the deprecation of the top-level
quantity/unit fields in favor of line_item_measurements) come from
https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page
and https://docs.instacart.com/developer_platform_api/api/units_of_measurement/
(verified 2026-07-15). Limits marked "our own limit" below are NOT documented by
Instacart — they are defensive guardrails we chose, not upstream behavior.
"""

import os
import re
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional

from api.services import instacart_client

# ── Our own defensive limits (not Instacart-documented) ──────────────────────
MAX_LINE_ITEMS = 50
MAX_TITLE_LENGTH = 150
MAX_ITEM_NAME_LENGTH = 200
MAX_BRAND_PREFERENCES = 10

# Instacart's documented supported units (exact codes), plus a normalization map
# from common full words to those codes. Anything not resolvable to a documented
# code is rejected rather than silently passed through (unsupported units make
# Instacart's own quantity matching fail, per their docs).
_SUPPORTED_UNITS = {
    "c", "fl oz", "gal", "ml", "l", "pt", "qt", "tb", "ts",
    "g", "kg", "lb", "oz",
    "bunch", "can", "each", "ears", "head", "lg", "md", "package", "packet", "sm",
}
_UNIT_SYNONYMS = {
    "cup": "c", "cups": "c",
    "fluid ounce": "fl oz", "fluid ounces": "fl oz", "floz": "fl oz",
    "gallon": "gal", "gallons": "gal",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml",
    "liter": "l", "liters": "l", "litre": "l",
    "pint": "pt", "pints": "pt",
    "quart": "qt", "quarts": "qt",
    "tablespoon": "tb", "tablespoons": "tb", "tbsp": "tb",
    "teaspoon": "ts", "teaspoons": "ts", "tsp": "ts",
    "gram": "g", "grams": "g",
    "kilogram": "kg", "kilograms": "kg",
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz",
    "package": "package", "packages": "package", "pkg": "package",
    "packet": "packet", "packets": "packet",
    "small": "sm", "medium": "md", "large": "lg",
}

_UPC_RE = re.compile(r"^\d{12}(\d{2})?$")  # 12 or 14 digits
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_unit(raw: str) -> str:
    """Resolve a user-supplied unit string to an Instacart-documented unit code.
    Raises ValueError if it cannot be resolved. This normalization (full-word ->
    code) is our own convenience layer, not an Instacart-documented behavior."""
    key = raw.strip().lower()
    if key in _SUPPORTED_UNITS:
        return key
    if key in _UNIT_SYNONYMS:
        return _UNIT_SYNONYMS[key]
    raise ValueError(
        f"Unsupported unit {raw!r}. Supported units: {sorted(_SUPPORTED_UNITS)}"
    )


def _reject_control_chars(v: str, field_name: str) -> str:
    if _CONTROL_CHAR_RE.search(v):
        raise ValueError(f"{field_name} contains control characters")
    return v


class ShoppingListItemRequest(BaseModel):
    name: str
    quantity: float = 1.0
    unit: str = "each"
    upc: Optional[str] = None
    brand_preferences: list[str] = []

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        v = _reject_control_chars(v, "name").strip()
        if not v:
            raise ValueError("name must not be blank")
        if len(v) > MAX_ITEM_NAME_LENGTH:
            raise ValueError(f"name must be at most {MAX_ITEM_NAME_LENGTH} characters")
        return v

    @field_validator("quantity")
    @classmethod
    def _validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be greater than 0")
        return v

    @field_validator("unit")
    @classmethod
    def _validate_unit(cls, v: str) -> str:
        return normalize_unit(v)

    @field_validator("upc")
    @classmethod
    def _validate_upc(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not _UPC_RE.match(v):
            raise ValueError("upc must be 12 or 14 digits")
        return v

    @field_validator("brand_preferences")
    @classmethod
    def _validate_brand_preferences(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_BRAND_PREFERENCES:
            raise ValueError(f"brandPreferences must have at most {MAX_BRAND_PREFERENCES} entries")
        cleaned = []
        for brand in v:
            brand = _reject_control_chars(brand, "brandPreferences entry").strip()
            if brand:
                cleaned.append(brand)
        return cleaned


class ShoppingListCreateRequest(BaseModel):
    athlete_id: int
    title: str
    items: list[ShoppingListItemRequest]

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        v = _reject_control_chars(v, "title").strip()
        if not v:
            raise ValueError("title must not be blank")
        if len(v) > MAX_TITLE_LENGTH:
            raise ValueError(f"title must be at most {MAX_TITLE_LENGTH} characters")
        return v

    @model_validator(mode="after")
    def _validate_items(self):
        if not self.items:
            raise ValueError("items must not be empty")
        if len(self.items) > MAX_LINE_ITEMS:
            raise ValueError(f"items must have at most {MAX_LINE_ITEMS} entries")
        seen_upcs = set()
        seen_names = set()
        for item in self.items:
            if item.upc:
                if item.upc in seen_upcs:
                    raise ValueError(f"duplicate upc in items: {item.upc}")
                seen_upcs.add(item.upc)
            name_key = item.name.lower()
            if name_key in seen_names:
                raise ValueError(f"duplicate item name in items: {item.name}")
            seen_names.add(name_key)
        return self


class ShoppingListCreateResponse(BaseModel):
    provider: str = "instacart"
    shopping_list_url: str
    requires_user_review: bool = True


def _partner_linkback_url() -> Optional[str]:
    """Operator-configured only — never taken from the request body, so a
    client can never make us hand Instacart an arbitrary callback domain."""
    return os.environ.get("INSTACART_PARTNER_LINKBACK_URL") or None


def _map_to_instacart_payload(req: ShoppingListCreateRequest) -> dict:
    line_items = []
    for item in req.items:
        line_item: dict = {
            "name": item.name,
            "line_item_measurements": [{"quantity": item.quantity, "unit": item.unit}],
        }
        if item.upc:
            line_item["upcs"] = [item.upc]
        if item.brand_preferences:
            line_item["filters"] = {"brand_filters": item.brand_preferences}
        line_items.append(line_item)

    payload: dict = {
        "title": req.title,
        "link_type": "shopping_list",
        "line_items": line_items,
    }
    landing_page_configuration = {}
    linkback = _partner_linkback_url()
    if linkback:
        landing_page_configuration["partner_linkback_url"] = linkback
    if landing_page_configuration:
        payload["landing_page_configuration"] = landing_page_configuration
    return payload


def _validate_response_url(url: str) -> str:
    """Reject anything that isn't an https:// URL on a trusted Instacart host.
    Instacart's docs only document instacart.com-family hosts for this
    response; treating anything else as unsafe protects against relaying an
    unexpected/compromised redirect target to the client."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise instacart_client.InstacartUnavailableError("Instacart returned a non-HTTPS URL")
    host = (parsed.hostname or "").lower()
    if not any(host == h or host.endswith(f".{h}") for h in instacart_client.TRUSTED_RESPONSE_HOSTS):
        raise instacart_client.InstacartUnavailableError(f"Instacart returned an untrusted host: {host}")
    return url


def create_shopping_list(req: ShoppingListCreateRequest) -> ShoppingListCreateResponse:
    """Validate, map, call Instacart, validate the response. Raises
    instacart_client.InstacartError subclasses on failure — callers (the route)
    are responsible for safe error-to-HTTP-status mapping."""
    payload = _map_to_instacart_payload(req)
    result = instacart_client.create_shopping_list_page(payload)

    url = result.get("products_link_url") if isinstance(result, dict) else None
    if not url:
        raise instacart_client.InstacartUnavailableError("Instacart response missing products_link_url")
    url = _validate_response_url(url)

    return ShoppingListCreateResponse(shopping_list_url=url)
