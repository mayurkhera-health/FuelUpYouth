from datetime import date, timedelta


def get_week_start(d: date) -> date:
    """Return the Sunday on or before d."""
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)
