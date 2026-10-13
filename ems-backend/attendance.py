"""Attendance day-by-day builder shared by the employee and admin routers.

The raw Attendance sheet only has a row for days someone actually checked in. This module
fills in every day in a range with what actually happened: a computed Present / Half Day /
Missing Check-out (from a row), On Leave (approved full-day leave), Holiday / Weekly Off,
Absent (a working day, while EMS was tracking this person, with nothing explaining it), or
Not Tracked (a working day BEFORE the person could have used EMS -- see tracking_start()).
"""
from datetime import date, datetime, timedelta
from typing import Optional

from config import EMS_START_DATE
from utils import (
    attendance_status, format_minutes, is_working_day, now, parse_date_safe,
    today_date, worked_minutes,
)

NOT_TRACKED = "Not Tracked"

# "Permission" is a few hours off, not a whole day, so it must not turn the day into "On Leave".
NON_FULL_DAY_LEAVE_TYPES = {"Permission"}


def tracking_start(joined: Optional[date], account_created: Optional[date] = None) -> Optional[date]:
    """First day this person can fairly be marked Absent.

    "Absent" means "should have checked in but didn't". That is only true once the person is
    employed AND EMS exists AND they have a login. So it is the LATEST of:
      * the joining date            - nobody is absent before they joined
      * EMS_START_DATE (go-live)    - nobody could check in before the app existed
      * the day their login was created - same reason, for people added to EMS after go-live
    Earlier working days with no record are reported as "Not Tracked", never "Absent".
    Returns None (= no restriction) only when none of the three is known.
    """
    known = [d for d in (joined, EMS_START_DATE, account_created) if d is not None]
    return max(known) if known else None


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
    track_from: Optional[date] = None,
    recorded_only: bool = False,
) -> list[dict]:
    """One entry per day in [range_from, range_to].

    track_from    - see tracking_start(). Working days before it with no record are "Not Tracked".
    recorded_only - only return days that have a real record (a check-in or approved leave); used
                    for deactivated employees so they aren't listed as Absent after they left.
    """
    today = today or today_date()
    now_dt = now_dt or now()
    by_date = index_by_date(att_rows)
    leave_days = approved_leave_days(leave_rows, range_from, range_to)

    out = []
    d = range_from
    while d <= range_to:
        ds = d.isoformat()
        row = by_date.get(ds)
        if row and row.get("CheckIn"):
            out.append(entry_from_row(ds, row, today=today, now_dt=now_dt))
        elif ds in leave_days:
            out.append(empty_entry(ds, "On Leave"))
        elif recorded_only:
            pass  # no record and we were asked for real records only
        elif not is_working_day(d, holidays):
            out.append(empty_entry(ds, "Holiday" if ds in holidays else "Weekly Off"))
        elif track_from is not None and d < track_from:
            out.append(empty_entry(ds, NOT_TRACKED))
        else:
            out.append(empty_entry(ds, "Absent"))
        d += timedelta(days=1)
    return out
