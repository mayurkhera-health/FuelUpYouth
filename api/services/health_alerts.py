"""
Health alerting — fires only on meaningful transitions, push-first to the
founder's device with email strictly as fallback.

Rules:
  down     = green|unknown -> red   → "🔴 [FuelUp] <check> failed: <detail>"
  recovery = red -> green           → "✅ [FuelUp] <check> recovered"
  (unknown -> green never alerts.)

Cooldown: repeated DOWN alerts for the same check are suppressed for 3h (flap
control, survives restart via health_checks.last_alerted_at). Recovery always
notifies. Channel: Expo push to ADMIN_ALERT_PARENT_ID's device(s); if the push
send fails/raises, fall back to send_email(ADMIN_ALERT_EMAIL) — email fires ONLY
as fallback, never duplicated. If the failing check IS expo_push, skip straight
to email. All sends are best-effort and never raise into the runner.
"""

import logging
import os
from datetime import datetime, timedelta

from api.services.email_service import send_email

log = logging.getLogger(__name__)

COOLDOWN_HOURS = 3


def _direction(from_status, to_status):
    if to_status == "red" and from_status in ("green", "unknown"):
        return "down"
    if to_status == "green" and from_status == "red":
        return "recovery"
    return None


def _in_cooldown(conn, check_name) -> bool:
    row = conn.execute(
        "SELECT last_alerted_at FROM health_checks WHERE check_name = ?", (check_name,)).fetchone()
    if not row or not row[0]:
        return False
    try:
        return (datetime.utcnow() - datetime.fromisoformat(row[0])) < timedelta(hours=COOLDOWN_HOURS)
    except Exception:
        return False


def _mark_alerted(conn, check_name):
    try:
        conn.execute("UPDATE health_checks SET last_alerted_at=? WHERE check_name=?",
                     (datetime.utcnow().isoformat(), check_name))
    except Exception:
        log.debug("mark_alerted failed for %s", check_name, exc_info=True)


def _message(check_name, direction, detail):
    if direction == "down":
        return f"🔴 [FuelUp] {check_name} failed", f"{check_name} failed: {detail}"
    return f"✅ [FuelUp] {check_name} recovered", f"{check_name} recovered."


def _push(conn, title, body) -> bool:
    pid = os.getenv("ADMIN_ALERT_PARENT_ID")
    if not pid:
        return False
    try:
        tokens = [r[0] for r in conn.execute(
            "SELECT token FROM expo_push_tokens WHERE parent_id = ?", (int(pid),)).fetchall()]
    except Exception:
        tokens = []
    if not tokens:
        return False
    # Lazy import avoids a load-time cycle (notification_service -> health_service).
    from api.services.notification_service import send_expo_push
    # record=False so alert sends don't pollute the passive expo_push health log.
    return bool(send_expo_push(tokens, title, body, record=False))


def _email(title, body) -> bool:
    to = os.getenv("ADMIN_ALERT_EMAIL")
    if not to:
        return False
    try:
        return bool(send_email(title, body, to=[to]))
    except Exception:
        log.warning("alert email failed", exc_info=True)
        return False


def dispatch(conn, check_name, from_status, to_status, detail):
    """Send an alert if this transition warrants one. Returns a short note
    (channel + outcome) to append to the incident, or None if no alert fired."""
    direction = _direction(from_status, to_status)
    if not direction:
        return None
    if direction == "down" and _in_cooldown(conn, check_name):
        return "suppressed (cooldown)"

    title, body = _message(check_name, direction, detail)

    # If the push channel itself is the failing check, go straight to email.
    if check_name == "expo_push":
        ok = _email(title, body)
        _mark_alerted(conn, check_name)
        return f"email {'✓' if ok else '✗'} (push unavailable)"

    try:
        pushed = _push(conn, title, body)
    except Exception as e:
        log.warning("alert push error: %s", e)
        pushed = False
    if pushed:
        _mark_alerted(conn, check_name)
        return "push ✓"

    ok = _email(title, body)
    _mark_alerted(conn, check_name)
    return f"email {'✓' if ok else '✗'} (push failed)"
