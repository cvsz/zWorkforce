from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import time
import socket
import uuid
from typing import Any
from zoneinfo import ZoneInfo

from .db import utcnow
from .workflow import WorkflowOrchestrator


class ScheduleError(ValueError):
    pass


def _field(spec: str, minimum: int, maximum: int) -> set[int]:
    values: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise ScheduleError("empty cron field")
        base, slash, step_raw = part.partition("/")
        step = int(step_raw) if slash else 1
        if step <= 0:
            raise ScheduleError("cron step must be positive")
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            a, b = base.split("-", 1)
            start, end = int(a), int(b)
        else:
            value = int(base)
            start = end = value
        if start < minimum or end > maximum or start > end:
            raise ScheduleError(f"cron value outside {minimum}..{maximum}")
        values.update(range(start, end + 1, step))
    return values


def parse_cron(expr: str) -> tuple[set[int], set[int], set[int], set[int], set[int]]:
    parts = expr.split()
    if len(parts) != 5:
        raise ScheduleError("cron expression must have 5 fields: minute hour day month weekday")
    minute = _field(parts[0], 0, 59)
    hour = _field(parts[1], 0, 23)
    day = _field(parts[2], 1, 31)
    month = _field(parts[3], 1, 12)
    weekday = _field(parts[4], 0, 6)
    return minute, hour, day, month, weekday


def next_cron_at(expr: str, after: datetime, timezone_name: str = "UTC") -> str:
    fields = parse_cron(expr)
    parts = expr.split()
    dom_wildcard = parts[2] == "*"
    dow_wildcard = parts[4] == "*"
    try:
        tz = ZoneInfo(timezone_name)
    except Exception as exc:
        raise ScheduleError(f"invalid timezone: {timezone_name}") from exc
    local = after.astimezone(tz).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(366 * 24 * 60 * 2):
        minute, hour, day, month, weekday = fields
        cron_weekday = (local.weekday() + 1) % 7
        dom_match = local.day in day
        dow_match = cron_weekday in weekday
        # POSIX/Vixie cron semantics: when both day-of-month and day-of-week are
        # restricted, either field may match. When one is '*', the other governs.
        if dom_wildcard and dow_wildcard:
            calendar_match = True
        elif dom_wildcard:
            calendar_match = dow_match
        elif dow_wildcard:
            calendar_match = dom_match
        else:
            calendar_match = dom_match or dow_match
        if local.minute in minute and local.hour in hour and local.month in month and calendar_match:
            return local.astimezone(timezone.utc).isoformat(timespec="seconds")
        local += timedelta(minutes=1)
    raise ScheduleError("cron expression has no matching time within search horizon")


def schedule_next(item: dict[str, Any], after: datetime | None = None) -> str:
    after = after or datetime.now(timezone.utc)
    if item["schedule_type"] == "interval":
        seconds = int(item.get("interval_seconds") or 0)
        if seconds < 1:
            raise ScheduleError("interval_seconds must be >= 1")
        return (after + timedelta(seconds=seconds)).isoformat(timespec="seconds")
    if item["schedule_type"] == "cron":
        return next_cron_at(str(item.get("cron_expr") or ""), after, str(item.get("timezone") or "UTC"))
    raise ScheduleError("schedule_type must be cron or interval")


def _subset(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _subset(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        return all(any(_subset(item, candidate) for candidate in actual) for item in expected)
    return actual == expected

