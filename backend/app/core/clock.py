"""Dates as the Practice sees them (Australia; one time zone until Sites span more than one)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

PRACTICE_TIME_ZONE = ZoneInfo("Australia/Sydney")


def practice_today() -> date:
    return datetime.now(PRACTICE_TIME_ZONE).date()


def practice_date(moment: datetime) -> str:
    """e.g. "25 Sep 2026"."""
    return moment.astimezone(PRACTICE_TIME_ZONE).strftime("%-d %b %Y")
