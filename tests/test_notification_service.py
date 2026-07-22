"""
Tests for api/services/notification_service.py

Covers every pure function the notification service exposes:
  - in_quiet_hours()
  - rank_for_notification()
  - select_notification_windows()
  - already_logged()            (DB, in-memory)
  - send_notification_guarded() (DB, monkeypatched send)
"""

import sqlite3
import pytest

from api.services.notification_service import (
    in_quiet_hours,
    rank_for_notification,
    select_notification_windows,
    already_logged,
    send_notification_guarded,
    send_expo_push,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _window(
    window_key: str,
    category: str,
    open_time: str = "12:00",
    sort_time: str | None = None,
    is_tappable: bool = True,
    priority: bool = False,
) -> dict:
    return {
        "window_key": window_key,
        "category":   category,
        "open_time":  open_time,
        "sort_time":  sort_time or open_time,
        "is_tappable": is_tappable,
        "priority":   priority,
    }


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def suppress_conn():
    """In-memory DB with window_logs and confirmations — for already_logged tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE window_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            window_id  TEXT NOT NULL,
            log_date   TEXT NOT NULL,
            UNIQUE(athlete_id, window_id, log_date)
        );
        CREATE TABLE confirmations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id  INTEGER NOT NULL,
            log_date    TEXT NOT NULL,
            window_key  TEXT NOT NULL,
            window_type TEXT NOT NULL DEFAULT '',
            UNIQUE(athlete_id, window_key, log_date)
        );
    """)
    yield conn
    conn.close()


@pytest.fixture
def notif_conn():
    """In-memory DB with notification_log — for send_notification_guarded tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE notification_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            window_key TEXT NOT NULL,
            send_date  TEXT NOT NULL,
            recipient  TEXT NOT NULL,
            token      TEXT NOT NULL,
            sent_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (athlete_id, window_key, send_date, recipient)
        );
    """)
    yield conn
    conn.close()


# ─── in_quiet_hours ────────────────────────────────────────────────────────────

class TestInQuietHours:
    def test_before_0630_is_quiet(self):
        assert in_quiet_hours("05:00") is True

    def test_midnight_is_quiet(self):
        assert in_quiet_hours("00:00") is True

    def test_0629_is_quiet(self):
        assert in_quiet_hours("06:29") is True

    def test_0630_is_not_quiet(self):
        assert in_quiet_hours("06:30") is False

    def test_midday_is_not_quiet(self):
        assert in_quiet_hours("12:00") is False

    def test_2159_is_not_quiet(self):
        assert in_quiet_hours("21:59") is False

    def test_2200_is_quiet(self):
        assert in_quiet_hours("22:00") is True

    def test_2359_is_quiet(self):
        assert in_quiet_hours("23:59") is True


# ─── rank_for_notification ─────────────────────────────────────────────────────

class TestRankForNotification:
    def test_priority_true_is_rank_0(self):
        w = _window("fuel_after_primary_1", "fuel_after", priority=True)
        assert rank_for_notification(w) == 0

    def test_fuel_before_is_rank_1(self):
        w = _window("pre_event_meal", "fuel_before")
        assert rank_for_notification(w) == 1

    def test_quick_morning_snack_is_rank_1(self):
        # quick_snack that is NOT a top_up → rank 1
        w = _window("quick_morning_snack", "quick_snack")
        assert rank_for_notification(w) == 1

    def test_top_up_snack_is_skipped(self):
        # quick_snack that IS a top_up → rank 99
        w = _window("top_up_snack_1", "quick_snack")
        assert rank_for_notification(w) == 99

    def test_refuel_ready_is_rank_2(self):
        w = _window("refuel_ready_1_2", "refuel_ready")
        assert rank_for_notification(w) == 2

    def test_between_games_is_rank_2(self):
        w = _window("between_games_1_2", "between_games")
        assert rank_for_notification(w) == 2

    def test_fuel_after_second_is_rank_3(self):
        w = _window("fuel_after_second_1", "fuel_after")
        assert rank_for_notification(w) == 3

    def test_everyday_is_skipped(self):
        w = _window("everyday_lunch", "everyday")
        assert rank_for_notification(w) == 99

    def test_fuel_during_nudge_is_skipped(self):
        # fuel_during is not tappable, but rank function doesn't check tappable
        w = _window("fuel_during_1", "fuel_during", is_tappable=False)
        assert rank_for_notification(w) == 99


# ─── select_notification_windows ──────────────────────────────────────────────

class TestSelectNotificationWindows:
    def test_caps_at_daily_cap_of_2(self):
        windows = [
            _window("fuel_after_primary_1", "fuel_after", "14:00", priority=True),
            _window("pre_event_meal_1",      "fuel_before", "11:00"),
            _window("refuel_ready_1_2",      "refuel_ready", "12:00"),
        ]
        result = select_notification_windows(windows)
        assert len(result) == 2

    def test_selects_by_priority_rank(self):
        windows = [
            _window("fuel_after_primary_1", "fuel_after",  "14:00", priority=True),
            _window("pre_event_meal_1",      "fuel_before", "11:00"),
            _window("refuel_ready_1_2",      "refuel_ready", "12:00"),
        ]
        result = select_notification_windows(windows)
        keys = [w["window_key"] for w in result]
        # Priority=True (rank 0) and fuel_before (rank 1) win over refuel_ready (rank 2)
        assert "fuel_after_primary_1" in keys
        assert "pre_event_meal_1" in keys

    def test_excludes_quiet_hours(self):
        windows = [
            _window("fuel_after_primary_1", "fuel_after", "04:00", priority=True),
        ]
        assert select_notification_windows(windows) == []

    def test_excludes_non_tappable(self):
        windows = [
            _window("fuel_during_1", "fuel_during", "12:00", is_tappable=False),
        ]
        assert select_notification_windows(windows) == []

    def test_excludes_rank_99(self):
        windows = [
            _window("everyday_lunch",  "everyday",  "12:00"),
            _window("top_up_snack_1",  "quick_snack", "10:00"),
        ]
        assert select_notification_windows(windows) == []

    def test_empty_input_returns_empty(self):
        assert select_notification_windows([]) == []

    def test_fewer_than_cap_returns_all_eligible(self):
        windows = [
            _window("pre_event_meal_1", "fuel_before", "11:00"),
        ]
        result = select_notification_windows(windows)
        assert len(result) == 1


# ─── already_logged ────────────────────────────────────────────────────────────

class TestAlreadyLogged:
    def test_not_logged_returns_false(self, suppress_conn):
        assert already_logged(1, "pre_event_meal", "2026-06-19", suppress_conn) is False

    def test_in_window_logs_returns_true(self, suppress_conn):
        suppress_conn.execute(
            "INSERT INTO window_logs (athlete_id, window_id, log_date) VALUES (1, 'pre_event_meal', '2026-06-19')"
        )
        assert already_logged(1, "pre_event_meal", "2026-06-19", suppress_conn) is True

    def test_in_confirmations_returns_true(self, suppress_conn):
        suppress_conn.execute(
            "INSERT INTO confirmations (athlete_id, window_key, log_date) VALUES (1, 'pre_event_meal', '2026-06-19')"
        )
        assert already_logged(1, "pre_event_meal", "2026-06-19", suppress_conn) is True

    def test_different_athlete_returns_false(self, suppress_conn):
        suppress_conn.execute(
            "INSERT INTO window_logs (athlete_id, window_id, log_date) VALUES (2, 'pre_event_meal', '2026-06-19')"
        )
        assert already_logged(1, "pre_event_meal", "2026-06-19", suppress_conn) is False

    def test_different_date_returns_false(self, suppress_conn):
        suppress_conn.execute(
            "INSERT INTO window_logs (athlete_id, window_id, log_date) VALUES (1, 'pre_event_meal', '2026-06-18')"
        )
        assert already_logged(1, "pre_event_meal", "2026-06-19", suppress_conn) is False


# ─── send_notification_guarded ─────────────────────────────────────────────────

class TestSendNotificationGuarded:
    def test_first_send_returns_true_and_calls_push(self, notif_conn, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "api.services.notification_service.send_expo_push",
            lambda tokens, title, body: sent.append((tokens, title, body)),
        )
        result = send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        assert result is True
        assert len(sent) == 1

    def test_duplicate_send_returns_false_and_does_not_push(self, notif_conn, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "api.services.notification_service.send_expo_push",
            lambda tokens, title, body: sent.append((tokens, title, body)),
        )
        # First send
        send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        # Duplicate
        result = send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        assert result is False
        assert len(sent) == 1  # not called again

    def test_dry_run_does_not_write_to_notification_log(self, notif_conn, monkeypatch):
        """DRY_RUN must not poison notification_log — real sends after dry-run must still fire."""
        import api.services.notification_service as svc
        monkeypatch.setattr(svc, "DRY_RUN", True)

        # Dry-run call — should return True but write nothing to notification_log
        result = send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        assert result is True

        row_count = notif_conn.execute("SELECT COUNT(*) FROM notification_log").fetchone()[0]
        assert row_count == 0, "dry-run must not write to notification_log"

    def test_real_send_after_dry_run_is_not_suppressed(self, notif_conn, monkeypatch):
        """A prior dry-run for the same key must not block the first real send."""
        import api.services.notification_service as svc

        # Simulate a dry-run tick
        monkeypatch.setattr(svc, "DRY_RUN", True)
        send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )

        # Switch to real mode — first real send should go through
        sent = []
        monkeypatch.setattr(svc, "DRY_RUN", False)
        monkeypatch.setattr(svc, "send_expo_push", lambda tokens, title, body: sent.append(tokens))
        result = send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        assert result is True
        assert len(sent) == 1, "real send after dry-run should not be suppressed"


class TestSendExpoPush:
    def test_data_payload_is_included_when_provided(self, monkeypatch):
        import api.services.notification_service as svc
        monkeypatch.setattr(svc, "DRY_RUN", False)

        captured = {}

        class FakeResponse:
            status_code = 200

        def fake_post(url, json, timeout):
            captured["messages"] = json
            return FakeResponse()

        monkeypatch.setattr(svc.requests, "post", fake_post)
        ok = send_expo_push(
            ["ExponentPushToken[abc]"], "Title", "Body",
            record=False, data={"type": "daily_challenge"},
        )
        assert ok is True
        assert captured["messages"][0]["data"] == {"type": "daily_challenge"}

    def test_no_data_key_when_not_provided_backward_compatible(self, monkeypatch):
        import api.services.notification_service as svc
        monkeypatch.setattr(svc, "DRY_RUN", False)

        captured = {}

        class FakeResponse:
            status_code = 200

        def fake_post(url, json, timeout):
            captured["messages"] = json
            return FakeResponse()

        monkeypatch.setattr(svc.requests, "post", fake_post)
        send_expo_push(["ExponentPushToken[abc]"], "Title", "Body", record=False)
        assert "data" not in captured["messages"][0]

    def test_different_recipient_is_independent(self, notif_conn, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "api.services.notification_service.send_expo_push",
            lambda tokens, title, body: sent.append((tokens, title, body)),
        )
        r1 = send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "athlete",
            ["ExponentPushToken[abc]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        r2 = send_notification_guarded(
            1, "pre_event_meal", "2026-06-19", "parent",
            ["ExponentPushToken[xyz]"], "Pre-Game Meal", "Eat now.", notif_conn,
        )
        assert r1 is True
        assert r2 is True
        assert len(sent) == 2
