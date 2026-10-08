"""Time helpers and attendance rules.

Storage format: attendance timestamps are ISO strings without timezone, in APP_TIMEZONE
local time (e.g. "2026-09-26T09:15:00"); AttendanceDate is "YYYY-MM-DD".

Google Sheets can silently turn those strings into real dates and hand them back in the
sheet's display format ("9/26/2026 9:15:00"). sheets_client normalises known date columns
back to ISO on every read using normalize_date()/normalize_datetime() below, so the rest
of the app only ever sees ISO strings.
"""
import re
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional

from config import (
    APP_TIMEZONE, SHEET_DAY_FIRST, WEEKLY_OFF_DAYS, ATTENDANCE_START_DATE,
    ENABLE_LATE_MARKING, LATE_CUTOFF_HOUR, LATE_CUTOFF_MINUTE,
    HALF_DAY_HOURS, FULL_DAY_HOURS,
)

ISO_FMT = "%Y-%m-%dT%H:%M:%S"

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo(APP_TIMEZONE)
except Exception:  # tzdata missing or bad name: fall back to India Standard Time (UTC+5:30)
    _TZ = timezone(timedelta(hours=5, minutes=30))


# ---------- "now" / "today" in the app's timezone ----------

def now() -> datetime:
    """Current local time in APP_TIMEZONE, as a naive datetime (no tzinfo)."""
    return datetime.now(_TZ).replace(tzinfo=None, microsecond=0)


def today_date() -> date:
    return now().date()


def today_str() -> str:
    return today_date().isoformat()


def to_iso(dt: datetime) -> str:
    return dt.strftime(ISO_FMT)


# ---------- tolerant parsing (sheet cells are free text) ----------

_DATETIME_FORMATS_ISO = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M")
_SLASH_TIME = ("%H:%M:%S", "%I:%M:%S %p", "%H:%M", "%I:%M %p")


def _slash_date_formats() -> list[str]:
    order = ["%d/%m/%Y", "%m/%d/%Y"] if SHEET_DAY_FIRST else ["%m/%d/%Y", "%d/%m/%Y"]
    return order


# Google Sheets stores real dates as "days since 1899-12-30". When the app used to write
# timestamps with USER_ENTERED, Sheets converted them, and a cell without a date format
# hands back the raw number (e.g. "46291.67885" = 2026-09-26 16:17). Read those too.
_SERIAL_RE = re.compile(r"^\d{5}(\.\d+)?$")
_SHEETS_EPOCH = datetime(1899, 12, 30)


def _from_serial(s: str) -> Optional[datetime]:
    if not _SERIAL_RE.match(s):
        return None
    days = float(s)
    if not 20000 <= days <= 80000:  # ~1954..2118; anything else isn't a date
        return None
    return _SHEETS_EPOCH + timedelta(seconds=round(days * 86400))


def parse_datetime(s) -> Optional[datetime]:
    """Parse ISO, Google-Sheets display strings, or Sheets date serial numbers. None if unparsable."""
    if s is None:
        return None
    s = str(s).strip().lstrip("'")
    if not s:
        return None
    serial = _from_serial(s)
    if serial is not None:
        return serial
    for fmt in _DATETIME_FORMATS_ISO:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    # "9/26/2026 9:15:00" / "26/09/2026 09:15" / "9/26/2026 9:15:00 AM"
    for dfmt in _slash_date_formats():
        for tfmt in _SLASH_TIME:
            try:
                return datetime.strptime(s, f"{dfmt} {tfmt}")
            except ValueError:
                pass
    return None


def parse_date_safe(s) -> Optional[date]:
    """Parse 'YYYY-MM-DD' (or a slash date / a full datetime string) into a date; None if bad."""
    if s is None:
        return None
    s = str(s).strip().lstrip("'")
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d",) + tuple(_slash_date_formats()) + ("%d-%m-%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    dt = parse_datetime(s)
    return dt.date() if dt else None


def normalize_datetime(s) -> str:
    """Return canonical ISO datetime string, or the original text if we can't parse it."""
    dt = parse_datetime(s)
    return to_iso(dt) if dt else ("" if s is None else str(s))


def normalize_date(s) -> str:
    d = parse_date_safe(s)
    return d.isoformat() if d else ("" if s is None else str(s))


def parse_iso(s) -> Optional[datetime]:  # kept for callers that used the old name
    return parse_datetime(s)


# ---------- working hours ----------

def worked_minutes(check_in: str, check_out: str, *, live_until: Optional[datetime] = None) -> Optional[int]:
    """Minutes between check-in and check-out. If there's no check-out but `live_until` is
    given, counts up to that moment (used for "hours so far" today). None if not computable."""
    ci = parse_datetime(check_in)
    if ci is None:
        return None
    co = parse_datetime(check_out)
    if co is None:
        if live_until is None:
            return None
        co = live_until
    return max(0, int((co - ci).total_seconds() // 60))


def format_minutes(total_minutes: Optional[int]) -> Optional[str]:
    if total_minutes is None:
        return None
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def working_hours_str(check_in: str, check_out: str, *, live_until: Optional[datetime] = None) -> Optional[str]:
    """e.g. '7h 45m', or None if it can't be worked out."""
    return format_minutes(worked_minutes(check_in, check_out, live_until=live_until))


# ---------- attendance status (computed, never trusted from the sheet) ----------

def is_late(check_in_time: datetime) -> bool:
    return check_in_time.time() > time(LATE_CUTOFF_HOUR, LATE_CUTOFF_MINUTE)


def attendance_status(att_date: str, check_in: str, check_out: str, *, today: Optional[date] = None,
                      now_dt: Optional[datetime] = None) -> str:
    """Status for a day that HAS a check-in.

    Present            - checked in (the default; flexible hours, so start time doesn't matter)
    Late               - only if ENABLE_LATE_MARKING is on and check-in was after the cutoff
    Half Day / Short Hours - only if HALF_DAY_HOURS / FULL_DAY_HOURS are set and the finished day is short
    Missing Check-out  - a PAST day with a check-in but no check-out (admin can fix it)
    """
    today = today or today_date()
    now_dt = now_dt or now()
    ci = parse_datetime(check_in)
    if ci is None:
        return "Absent"

    if not parse_datetime(check_out):
        d = parse_date_safe(att_date)
        if d is not None and d < today:
            return "Missing Check-out"
        return "Late" if ENABLE_LATE_MARKING and is_late(ci) else "Present"

    minutes = worked_minutes(check_in, check_out) or 0
    if HALF_DAY_HOURS and minutes < HALF_DAY_HOURS * 60:
        return "Half Day"
    if FULL_DAY_HOURS and minutes < FULL_DAY_HOURS * 60:
        return "Short Hours"
    return "Late" if ENABLE_LATE_MARKING and is_late(ci) else "Present"


# ---------- calendar ----------


def attendance_tracking_start_date() -> Optional[date]:
    """First date for which EMS is responsible for attendance records.
    Returns None when no deployment start date is configured."""
    return ATTENDANCE_START_DATE


def is_attendance_tracking_day(d: date) -> bool:
    """Whether EMS should create/display attendance for this calendar day."""
    return ATTENDANCE_START_DATE is None or d >= ATTENDANCE_START_DATE


def is_working_day(d: date, holidays: Optional[set] = None) -> bool:
    """True unless d is a listed holiday or falls on a weekly-off weekday (Monday=0 ... Sunday=6)."""
    if holidays and d.isoformat() in holidays:
        return False
    return d.weekday() not in WEEKLY_OFF_DAYS
