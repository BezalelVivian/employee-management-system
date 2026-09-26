"""Small time/formatting helpers. Attendance timestamps are stored as ISO datetime
strings (e.g. "2026-09-26T09:15:00") in the CheckIn/CheckOut columns; AttendanceDate
is stored as "YYYY-MM-DD"."""
from datetime import datetime, date, time

from config import LATE_CUTOFF_HOUR, LATE_CUTOFF_MINUTE

ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def now() -> datetime:
    return datetime.now()


def today_str() -> str:
    return date.today().isoformat()


def to_iso(dt: datetime) -> str:
    return dt.strftime(ISO_FMT)


def parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, ISO_FMT)
    except ValueError:
        return None


def is_late(check_in_time: datetime) -> bool:
    cutoff = time(LATE_CUTOFF_HOUR, LATE_CUTOFF_MINUTE)
    return check_in_time.time() > cutoff


def working_hours_str(check_in: str, check_out: str) -> str | None:
    """Returns e.g. '7h 45m', or None if either timestamp is missing/unparsable."""
    ci = parse_iso(check_in)
    co = parse_iso(check_out)
    if ci is None or co is None:
        return None
    delta = co - ci
    total_minutes = max(0, int(delta.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def parse_date_safe(s: str | None) -> date | None:
    """Parse a 'YYYY-MM-DD' string into a date, returning None instead of raising
    for blank/missing/malformed values (sheet cells are free-text, so this is never
    guaranteed to be clean)."""
    if not s:
        return None
    try:
        return date.fromisoformat(str(s).strip())
    except ValueError:
        return None


def is_working_day(d: date, holidays: set[str] | None = None) -> bool:
    """True for a normal working day: Monday-Saturday, and not in the given set of
    'YYYY-MM-DD' holiday strings. Sunday is the weekly off."""
    if holidays and d.isoformat() in holidays:
        return False
    return d.weekday() != 6  # Monday=0 ... Sunday=6