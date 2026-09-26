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
    JWT_EXPIRE_MINUTES           - access token lifetime in minutes (default 60)
    LATE_CUTOFF_HOUR             - hour (24h, local time) after which check-in is "Late" (default 9)
    LATE_CUTOFF_MINUTE           - minute component of the late cutoff (default 30)
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

LATE_CUTOFF_HOUR = int(os.environ.get("LATE_CUTOFF_HOUR", "9"))
LATE_CUTOFF_MINUTE = int(os.environ.get("LATE_CUTOFF_MINUTE", "30"))

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