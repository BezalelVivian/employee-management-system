"""Attendance day-by-day builder shared by the employee and admin routers.

The raw Attendance sheet only has a row for days someone actually checked in. This module
fills in every day in a range with what actually happened: a computed Present / Half Day /
Missing Check-out (from a row), On Leave (approved full-day leave), Holiday / Weekly Off,
or Absent (a working day with nothing explaining it).
"""
from datetime import date, datetime, timedelta
from typing import Optional

from utils import (
    attendance_status, format_minutes, is_working_day, now, parse_date_safe,
    today_date, worked_minutes, is_attendance_tracking_day,
)

# "Permission" is a few hours off, not a whole day, so it must not turn the day into "On Leave".
NON_FULL_DAY_LEAVE_TYPES = {"Permission"}


def approved_leave_days(leave_rows: list[dict], range_from: date, range_to: date) -> set[str]:
    """ISO dates within [range_from, range_to] covered by approved full-day leave.
    Only walks the overlap with the range, so a typo'd leave like 2020..2099 can't hang a request."""
    days: set[str] = set()
    for lr in leave_rows:
        if lr.get("Status") != "Approved" or lr.get("LeaveType") in NON_FULL_DAY_LEAVE_TYPES:
            continue
        f, t = parse_date_safe(lr.get("FromDate")), parse_date_safe(lr.get("ToDate"))
        if not f or not t:
            continue
        d, end = max(f, range_from), min(t, range_to)
        while d <= end:
            days.add(d.isoformat())
            d += timedelta(days=1)
    return days


def index_by_date(att_rows: list[dict]) -> dict[str, dict]:
    """One row per date. If a date has duplicates (e.g. an old double-click), keep the one
    that actually has a check-in."""
    by_date: dict[str, dict] = {}
    for r in att_rows:
        ds = r.get("AttendanceDate")
        if not ds:
            continue
        cur = by_date.get(ds)
        if cur is None or (not cur.get("CheckIn") and r.get("CheckIn")):
            by_date[ds] = r
    return by_date


def entry_from_row(ds: str, row: dict, *, today: date, now_dt: datetime) -> dict:
    check_in, check_out = row.get("CheckIn") or "", row.get("CheckOut") or ""
    in_progress = bool(check_in) and not check_out and ds == today.isoformat()
    minutes = worked_minutes(check_in, check_out, live_until=now_dt if in_progress else None)
    if not check_in:
        status = "Absent"
    else:
        status = attendance_status(ds, check_in, check_out, today=today, now_dt=now_dt)
    return {
        "date": ds,
        "checkIn": check_in or None,
        "checkOut": check_out or None,
        "workingHours": format_minutes(minutes),
        "status": status,
        "inProgress": in_progress,
    }


def empty_entry(ds: str, status: str) -> dict:
    return {"date": ds, "checkIn": None, "checkOut": None, "workingHours": None,
            "status": status, "inProgress": False}


def build_days(
    att_rows: list[dict],
    leave_rows: list[dict],
    holidays: set[str],
    range_from: date,
    range_to: date,
    *,
    today: Optional[date] = None,
    now_dt: Optional[datetime] = None,
) -> list[dict]:
    today = today or today_date()
    now_dt = now_dt or now()
    by_date = index_by_date(att_rows)
    leave_days = approved_leave_days(leave_rows, range_from, range_to)

    out = []
    d = range_from
    while d <= range_to:
        # Before EMS went live there is no trustworthy attendance record to judge.
        # Do not synthesize those days as Absent.
        if not is_attendance_tracking_day(d):
            d += timedelta(days=1)
            continue
        ds = d.isoformat()
        row = by_date.get(ds)
        if row and row.get("CheckIn"):
            out.append(entry_from_row(ds, row, today=today, now_dt=now_dt))
        elif ds in leave_days:
            out.append(empty_entry(ds, "On Leave"))
        elif not is_working_day(d, holidays):
            out.append(empty_entry(ds, "Holiday" if ds in holidays else "Weekly Off"))
        else:
            out.append(empty_entry(ds, "Absent"))
        d += timedelta(days=1)
    return out
