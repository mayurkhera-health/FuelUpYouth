import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from api.database import get_conn

router = APIRouter()

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CONTACT     = os.getenv("VAPID_CONTACT", "mailto:purvi@dietsandlife.com")


class PushSubscription(BaseModel):
    athlete_id: int
    endpoint: str
    p256dh: str
    auth: str


class ExpoTokenPayload(BaseModel):
    token: str
    platform: Optional[str] = None
    timezone: Optional[str] = None   # IANA tz, e.g. "America/Los_Angeles"
    athlete_id: Optional[int] = None
    parent_id: Optional[int] = None


@router.post("/expo-token")
def register_expo_token(data: ExpoTokenPayload):
    if not data.athlete_id and not data.parent_id:
        return {"message": "No profile id provided."}
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO expo_push_tokens (athlete_id, parent_id, token, platform, timezone)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(token) DO UPDATE SET
               athlete_id=excluded.athlete_id,
               parent_id=excluded.parent_id,
               platform=excluded.platform,
               timezone=excluded.timezone,
               updated_at=datetime('now')""",
            (data.athlete_id, data.parent_id, data.token, data.platform, data.timezone),
        )
        conn.commit()
        return {"message": "Token registered."}
    finally:
        conn.close()


class NotificationPrefs(BaseModel):
    remind_pregame_meal:  Optional[bool] = True
    remind_pregame_snack: Optional[bool] = True
    remind_meal_log:      Optional[bool] = True
    remind_hydration:     Optional[bool] = True


@router.get("/vapid-public-key")
def get_vapid_public_key():
    return {"publicKey": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
def subscribe(data: PushSubscription):
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO push_subscriptions (athlete_id, endpoint, p256dh, auth)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(athlete_id, endpoint) DO UPDATE SET
               p256dh=excluded.p256dh, auth=excluded.auth""",
            (data.athlete_id, data.endpoint, data.p256dh, data.auth),
        )
        conn.commit()
        return {"message": "Subscribed to push notifications."}
    finally:
        conn.close()


@router.get("/{athlete_id}/prefs")
def get_prefs(athlete_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM push_subscriptions WHERE athlete_id = ? ORDER BY id DESC LIMIT 1",
            (athlete_id,),
        ).fetchone()
        if not row:
            return {"subscribed": False, "remind_pregame_meal": True, "remind_pregame_snack": True,
                    "remind_meal_log": True, "remind_hydration": True}
        r = dict(row)
        return {"subscribed": True, "remind_pregame_meal": bool(r["remind_pregame_meal"]),
                "remind_pregame_snack": bool(r["remind_pregame_snack"]),
                "remind_meal_log": bool(r["remind_meal_log"]),
                "remind_hydration": bool(r["remind_hydration"])}
    finally:
        conn.close()


@router.put("/{athlete_id}/prefs")
def update_prefs(athlete_id: int, prefs: NotificationPrefs):
    conn = get_conn()
    try:
        conn.execute(
            """UPDATE push_subscriptions SET
               remind_pregame_meal=?, remind_pregame_snack=?,
               remind_meal_log=?, remind_hydration=?
               WHERE athlete_id=?""",
            (prefs.remind_pregame_meal, prefs.remind_pregame_snack,
             prefs.remind_meal_log, prefs.remind_hydration, athlete_id),
        )
        conn.commit()
        return {"message": "Preferences updated."}
    finally:
        conn.close()


@router.delete("/{athlete_id}/unsubscribe")
def unsubscribe(athlete_id: int):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM push_subscriptions WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return {"message": "Unsubscribed from push notifications."}
    finally:
        conn.close()
