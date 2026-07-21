"""TeamCoach auth — per-coach password hashing and HMAC-signed bearer tokens.

Same underlying crypto as admin_auth.py (stdlib only: base64, hashlib, hmac).
Separate from admin_auth: multi-user payload, separate env secret, 8h TTL.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8h — external users, shorter than admin 24h

_MAX_FAILS = 5
_WINDOW_SECONDS = 15 * 60
_LOCKOUT_SECONDS = 15 * 60
_failed_logins: dict[str, list[float]] = {}


def _secret() -> str:
    val = os.getenv("TEAM_COACH_SESSION_SECRET", "")
    if not val:
        raise RuntimeError(
            "TEAM_COACH_SESSION_SECRET env var is not set — "
            "TeamCoach login is disabled until this is configured."
        )
    return val


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def hash_password(plaintext: str) -> tuple[str, str]:
    """Return (hex_hash, hex_salt). Salt is random per call."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plaintext.encode(), salt.encode(), 260_000)
    return dk.hex(), salt


def verify_password(plaintext: str, stored_hash: str, salt: str) -> bool:
    dk = hashlib.pbkdf2_hmac("sha256", plaintext.encode(), salt.encode(), 260_000)
    return hmac.compare_digest(dk.hex(), stored_hash)


def mint_token(*, coach_id: int, email: str, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    secret = _secret()
    payload = {
        "coach_id": coach_id,
        "email": email,
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_b = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret.encode(), payload_b, hashlib.sha256).digest()
    return f"{_b64u(payload_b)}.{_b64u(sig)}"


def verify_token(token: str) -> dict | None:
    """Return payload dict if valid and unexpired; None otherwise."""
    secret_val = os.getenv("TEAM_COACH_SESSION_SECRET", "")
    if not secret_val or not token or "." not in token:
        return None
    try:
        payload_part, sig_part = token.split(".", 1)
        payload_b = _b64u_decode(payload_part)
        expected_sig = hmac.new(secret_val.encode(), payload_b, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64u_decode(sig_part), expected_sig):
            return None
        payload = json.loads(payload_b)
        if int(payload.get("exp", 0)) <= time.time():
            return None
        if "coach_id" not in payload:
            return None
        return payload
    except Exception:
        return None


def check_rate_limit(ip: str) -> None:
    from fastapi import HTTPException
    now = time.time()
    hits = [t for t in _failed_logins.get(ip, []) if now - t < _WINDOW_SECONDS]
    _failed_logins[ip] = hits
    if len(hits) >= _MAX_FAILS and now - hits[-1] < _LOCKOUT_SECONDS:
        raise HTTPException(429, "Too many failed login attempts. Try again later.")


def record_failed_login(ip: str) -> None:
    now = time.time()
    hits = [t for t in _failed_logins.get(ip, []) if now - t < _WINDOW_SECONDS]
    hits.append(now)
    _failed_logins[ip] = hits


def clear_failed_logins(ip: str) -> None:
    _failed_logins.pop(ip, None)
