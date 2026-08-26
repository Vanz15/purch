"""Centralized display-time helpers for Purch.

Stored timestamps remain untouched. Display conversion defaults to the
Philippines timezone and accepts a valid IANA timezone when a user provides
one, without making timezone detection a prerequisite for rendering.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PHILIPPINES_TIMEZONE = "Asia/Manila"


def _timezone_or_default(timezone_name: str) -> tzinfo:
    return ZoneInfo(display_timezone(timezone_name))


def display_timezone(timezone_name: str = "") -> str:
    """Return a validated IANA timezone name, defaulting to Philippines time."""
    candidate = timezone_name.strip() if timezone_name else ""
    if not candidate:
        return PHILIPPINES_TIMEZONE
    try:
        ZoneInfo(candidate)
        return candidate
    except (ZoneInfoNotFoundError, ValueError) as exc:
        logging.exception(
            f"Invalid display timezone; using Philippines time: {exc}"
        )
        return PHILIPPINES_TIMEZONE


def now_display(timezone_name: str = "", include_timezone: bool = False) -> str:
    """Format the current server time for a compact Purch UI label."""
    zone_name = display_timezone(timezone_name)
    current = datetime.now(_timezone_or_default(zone_name))
    value = current.strftime("%I:%M %p").lstrip("0")
    if include_timezone:
        return f"{value} · {zone_name}"
    return value


def today_in_timezone(timezone_name: str = "") -> date:
    return datetime.now(
        _timezone_or_default(display_timezone(timezone_name))
    ).date()


def month_label(day: date, timezone_name: str = "") -> str:
    """Return the month label using the user's timezone when available."""
    del timezone_name
    return day.strftime("%B %Y")


def month_window(timezone_name: str = "") -> tuple[date, date]:
    """Return the current local month bounds for display/query parameters."""
    current = today_in_timezone(timezone_name)
    if current.month == 12:
        next_month = date(current.year + 1, 1, 1)
    else:
        next_month = date(current.year, current.month + 1, 1)
    return current.replace(day=1), next_month


def format_stored_timestamp(value: object, timezone_name: str = "") -> str:
    """Convert a stored UTC-naive timestamp to a local display timestamp."""
    if value is None:
        return ""
    try:
        if isinstance(value, datetime):
            parsed = value
        else:
            raw = str(value)
            try:
                parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                parsed = datetime.fromisoformat(raw)
        source = parsed.replace(tzinfo=ZoneInfo("UTC"))
        local = source.astimezone(
            _timezone_or_default(display_timezone(timezone_name))
        )
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception as exc:
        logging.exception(f"Stored timestamp formatting failed: {exc}")
        return str(value)
