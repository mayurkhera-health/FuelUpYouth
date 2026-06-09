import os, json
from datetime import date as dt_date, datetime, timedelta
from fastapi import APIRouter, HTTPException
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


class NotificationPrefs(BaseModel):
    remind_pregame_meal:  Optional[bool] = True
    remind_pregame_snack: Optional[bool] = True
    remind_meal_log:      Optional[bool] = True
    remind_hydration:     Optional[bool] = True


def _send_push(sub: dict, title: str, body: str, url: str = "/"):
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CONTACT},
        )
        return True
    except Exception as e:
        print(f"Push failed: {e}")
        return False


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


@router.post("/{athlete_id}/send-daily")
def send_daily_reminders(athlete_id: int):
    """Call this once per day (e.g. via cron) to queue today's reminders."""
    conn = get_conn()
    try:
        athlete = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not athlete:
            raise HTTPException(404, "Athlete not found.")
        name = dict(athlete)["first_name"]

        subs = conn.execute(
            "SELECT * FROM push_subscriptions WHERE athlete_id = ?", (athlete_id,)
        ).fetchall()
        if not subs:
            return {"message": "No subscriptions for this athlete."}

        today = str(dt_date.today())
        events = conn.execute(
            "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
            (athlete_id, today),
        ).fetchall()
        event = dict(events[0]) if events else None
        event_type = event["event_type"] if event else "rest"
        start_time = event.get("start_time") if event else None

        sent = []
        for sub in [dict(s) for s in subs]:
            # Pre-game meal (3hrs before)
            if sub["remind_pregame_meal"] and start_time and event_type in ("game", "tournament", "practice"):
                _send_push(sub,
                    f"🍝 Time for {name}'s pre-event meal!",
                    f"Eat a balanced meal now — {event['event_name']} starts at {start_time}. Carbs + protein + low fat.",
                )
                sent.append("pregame_meal")

            # Pre-game snack (1hr before)
            if sub["remind_pregame_snack"] and start_time and event_type in ("game", "tournament"):
                _send_push(sub,
                    f"🍌 Pre-game snack time for {name}!",
                    f"1 hour until {event['event_name']}. Quick carbs: banana + peanut butter or toast + honey.",
                )
                sent.append("pregame_snack")

            # Hydration
            if sub["remind_hydration"] and event_type in ("game", "tournament", "practice"):
                _send_push(sub,
                    f"💧 Hydration check for {name}",
                    f"Training day! Make sure {name} drinks water before, during, and after {event_type}.",
                )
                sent.append("hydration")

            # Meal log reminder (always send if opted in)
            if sub["remind_meal_log"]:
                _send_push(sub,
                    f"📋 Log {name}'s meals today",
                    "Don't forget to track today's meals in FuelUp to keep nutrition on target.",
                )
                sent.append("meal_log")

        return {"message": f"Sent {len(sent)} reminders.", "sent": sent}
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
