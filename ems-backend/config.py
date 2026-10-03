"""
Environment configuration.

Required env vars (set these on Render for the backend):
    GOOGLE_SERVICE_ACCOUNT_JSON  - the full service account JSON key, as a single-line string
                                   (alternatively set GOOGLE_SERVICE_ACCOUNT_FILE to a path on disk)
    SPREADSHEET_ID               - the Google Sheet's ID (from its URL)
    JWT_SECRET                   - a long random string used to sign JWTs
    CORS_ORIGINS                 - comma-separated list of allowed frontend origins
                                   e.g. "https://your-app.vercel.app,http://localhost:5173"

Optional:
    JWT_EXPIRE_MINUTES           - access token lifetime in minutes (default 30 days)
    APP_TIMEZONE                 - IANA timezone used for "today" and check-in/out times
                                   (default "Asia/Kolkata"; Render servers run in UTC, so this matters)
    SHEET_DAY_FIRST              - "true" if your Google Sheet's locale shows dates as dd/mm/yyyy
                                   (default "false" = mm/dd/yyyy). Only used to read old cells that
                                   Sheets converted from text into real dates.
    WEEKLY_OFF_DAYS              - comma-separated weekday numbers that are the weekly off, Monday=0
                                   (default "6" = Sunday only; use "5,6" for Saturday + Sunday)

Attendance rules (all OFF by default because we run flexible hours -- the app just records
check-in / check-out and works out the hours):
    ENABLE_LATE_MARKING          - "true" to mark check-ins after the cutoff below as "Late" (default false)
    LATE_CUTOFF_HOUR / LATE_CUTOFF_MINUTE - the cutoff, local time (default 10:00). Only used if enabled.
    HALF_DAY_HOURS               - worked hours below this on a finished day show "Half Day" (default 0 = off)
    FULL_DAY_HOURS               - worked hours below this (but above half-day) show "Short Hours" (default 0 = off)
"""
import os
import json

from dotenv import load_dotenv

load_dotenv()  # no-op in production if there's no .env file; convenient for local dev


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"See config.py for the list of required vars."
        )
    return val


SPREADSHEET_ID = _require("SPREADSHEET_ID")
JWT_SECRET = _require("JWT_SECRET")
JWT_ALGORITHM = "HS256"
# Default is 30 days so logging in once keeps you logged in (this is an internal
# tool with no "remember me" checkbox — the token itself just lasts a long time).
# Override with a shorter value via the JWT_EXPIRE_MINUTES env var if you want
# stricter session expiry later.
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", str(60 * 24 * 30)))

def _bool_env(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _float_env(name: str, default: float = 0.0) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")
SHEET_DAY_FIRST = _bool_env("SHEET_DAY_FIRST", False)

WEEKLY_OFF_DAYS = {
    int(x) for x in os.environ.get("WEEKLY_OFF_DAYS", "6").split(",") if x.strip().isdigit()
}

# Flexible-hours startup: no late marking unless you explicitly switch it on.
ENABLE_LATE_MARKING = _bool_env("ENABLE_LATE_MARKING", False)
LATE_CUTOFF_HOUR = int(os.environ.get("LATE_CUTOFF_HOUR", "10"))
LATE_CUTOFF_MINUTE = int(os.environ.get("LATE_CUTOFF_MINUTE", "0"))

# 0 = rule disabled.
HALF_DAY_HOURS = _float_env("HALF_DAY_HOURS", 0)
FULL_DAY_HOURS = _float_env("FULL_DAY_HOURS", 0)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]


def get_service_account_info() -> dict:
    """
    Returns the service account credentials as a dict, loaded either from
    GOOGLE_SERVICE_ACCOUNT_JSON (raw JSON string) or GOOGLE_SERVICE_ACCOUNT_FILE (a path).
    """
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        return json.loads(raw_json)

    file_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if file_path:
        with open(file_path, "r") as f:
            return json.load(f)

    raise RuntimeError(
        "Missing Google service account credentials. Set GOOGLE_SERVICE_ACCOUNT_JSON "
        "(the raw JSON key contents) or GOOGLE_SERVICE_ACCOUNT_FILE (a path to the key file)."
    )