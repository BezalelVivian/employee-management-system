"""
Data-access layer over a single Google Spreadsheet used as the app's only datastore.

Design notes:
- Every "table" is a tab (sheet) with a header row in row 1. Rows are mapped to/from
  dicts BY HEADER NAME, not column position, so column order in the sheet doesn't matter
  (but header spelling must match exactly).
- This module hides all raw Sheets API calls behind a small set of generic functions;
  routers never call the Google API directly.
- Reads always fetch the whole sheet in one call (no per-row reads) to stay well within
  the free quota and keep latency predictable.
"""
import logging
import socket
import ssl
import threading
import time
from typing import Any, Optional

import httplib2
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import SPREADSHEET_ID, get_service_account_info

logger = logging.getLogger("ems.sheets")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Without an explicit timeout, httplib2 will block forever waiting for Google to
# respond. On a flaky network (AV/SSL-inspection, restrictive wifi, etc.) that turns
# a bad connection into a request that hangs for minutes instead of failing fast.
HTTP_TIMEOUT_SECONDS = 15

# Retry a request this many times (on top of the first attempt) if it fails with a
# transient network error. googleapiclient's own num_retries already retries on
# 5xx/HttpError, but NOT on socket/SSL timeouts, so we handle those ourselves.
MAX_NETWORK_RETRIES = 2

# Exceptions that mean "the network hiccuped", not "something is wrong with the data
# or the request itself" — worth retrying / reporting as a distinct error.
TRANSIENT_NETWORK_ERRORS = (TimeoutError, socket.timeout, ssl.SSLError, ConnectionError, OSError)

# HTTP status codes worth retrying with backoff: 429 (per-minute quota exceeded) and
# 5xx (Google-side hiccups). Anything else (404 sheet not found, 403 permission, 400
# bad request, ...) is a real problem and should fail immediately, not retry.
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}

# How long a full-sheet read is considered "fresh enough to reuse" instead of
# re-fetching from Google. The Sheets API free tier caps reads at 60/minute/user,
# and this app's pages each read several sheets on every navigation, plus the
# frontend sometimes fires duplicate requests — a short cache absorbs both without
# making the data noticeably stale for an internal EMS tool.
SHEET_CACHE_TTL_SECONDS = 8

_sheet_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_sheet_cache_lock = threading.Lock()


class SheetError(Exception):
    """Raised for any problem reading/writing the spreadsheet (missing sheet, empty
    header row, etc.) so routers can turn it into a clean HTTP error."""


_service_cache = threading.local()


def _get_service():
    """
    Returns a Sheets service object that is private to the CURRENT THREAD.

    FastAPI runs sync route functions (like the ones in routers/) in a worker
    thread pool, so multiple requests can call into this module concurrently.
    httplib2.Http (and the connections it caches internally) is NOT safe to share
    across threads: two threads reading/writing the same TLS socket at once
    corrupts the encrypted stream, which shows up as a spurious
    "[SSL: WRONG_VERSION_NUMBER]" error on whichever thread reads next. A single
    cached client (e.g. via @lru_cache) reproduces this under concurrent load.
    threading.local() gives each worker thread its own client, so requests
    handled on different threads never touch the same socket.
    """
    service = getattr(_service_cache, "service", None)
    if service is None:
        info = get_service_account_info()
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        # Build our own http object so we can set a timeout — build() with just
        # credentials= leaves httplib2 on its default of "no timeout at all".
        http = AuthorizedHttp(creds, http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS))
        service = build("sheets", "v4", http=http, cache_discovery=False)
        _service_cache.service = service
    return service


def _execute_with_retry(request, action: str):
    """Run a googleapiclient request's .execute(), retrying transient network errors
    and transient HTTP errors (429 rate-limit, 5xx) a couple of times with backoff
    before giving up, and turning any failure into a SheetError with a message that
    actually points at the real problem."""
    last_error: Optional[Exception] = None
    for attempt in range(1 + MAX_NETWORK_RETRIES):
        try:
            return request.execute()
        except HttpError as e:
            status = getattr(e, "status_code", None) or getattr(e.resp, "status", None)
            if status not in RETRYABLE_HTTP_STATUSES:
                raise SheetError(f"Could not {action}: {e}") from e
            last_error = e
            if attempt < MAX_NETWORK_RETRIES:
                wait = 2 ** attempt  # 1s, 2s, ...
                logger.warning(
                    "Google Sheets returned %s while trying to %s "
                    "(attempt %d/%d), retrying in %ds: %s",
                    status, action, attempt + 1, 1 + MAX_NETWORK_RETRIES, wait, e,
                )
                time.sleep(wait)
                continue
            raise SheetError(
                f"Could not {action}: still getting HTTP {status} from Google Sheets "
                f"after {1 + MAX_NETWORK_RETRIES} attempts (likely the per-minute "
                f"quota — 60 read requests/minute/user on the free tier). "
                f"Last error: {e}"
            ) from e
        except TRANSIENT_NETWORK_ERRORS as e:
            last_error = e
            logger.warning(
                "Network error talking to Google Sheets while trying to %s "
                "(attempt %d/%d): %s",
                action, attempt + 1, 1 + MAX_NETWORK_RETRIES, e,
            )
    raise SheetError(
        f"Could not {action}: timed out talking to Google Sheets after "
        f"{1 + MAX_NETWORK_RETRIES} attempts. This usually means something on this "
        f"machine/network (antivirus SSL inspection, a firewall, or the network "
        f"itself) is blocking or interfering with the connection to "
        f"sheets.googleapis.com, rather than a problem with the app. "
        f"Last error: {last_error}"
    ) from last_error


def _values():
    return _get_service().spreadsheets().values()


def _read_sheet_uncached(sheet_name: str) -> list[dict[str, Any]]:
    request = _values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name)
    result = _execute_with_retry(request, f"read sheet '{sheet_name}'")

    values = result.get("values", [])
    if not values:
        raise SheetError(
            f"Sheet '{sheet_name}' is empty — it needs at least a header row."
        )

    headers = values[0]
    if not any(h.strip() for h in headers):
        raise SheetError(f"Sheet '{sheet_name}' has a blank header row.")

    rows = []
    for i, raw_row in enumerate(values[1:], start=2):  # row 2 is the first data row
        padded = raw_row + [""] * (len(headers) - len(raw_row))
        row = {headers[j]: padded[j] for j in range(len(headers))}
        row["_row_number"] = i  # internal bookkeeping, not written back to the sheet
        rows.append(row)
    return rows


def all_rows(sheet_name: str) -> list[dict[str, Any]]:
    """
    Fetch every data row from `sheet_name` as a list of dicts keyed by header name.
    Raises SheetError if the sheet is missing or has no header row.

    Results are cached for SHEET_CACHE_TTL_SECONDS: this app re-reads the same
    sheets on almost every page navigation (and the frontend sometimes fires
    duplicate requests), which quickly hits Google's 60 reads/minute/user quota.
    A short cache absorbs that without making data noticeably stale for an
    internal tool. Any write (append_row/update_row) invalidates the affected
    sheet's cache entry immediately, so you always see your own changes.
    """
    now = time.monotonic()
    with _sheet_cache_lock:
        cached = _sheet_cache.get(sheet_name)
        if cached is not None and now - cached[0] < SHEET_CACHE_TTL_SECONDS:
            return cached[1]

    rows = _read_sheet_uncached(sheet_name)

    with _sheet_cache_lock:
        _sheet_cache[sheet_name] = (now, rows)
    return rows


def _invalidate_sheet_cache(sheet_name: str) -> None:
    with _sheet_cache_lock:
        _sheet_cache.pop(sheet_name, None)


def all_rows_optional(sheet_name: str) -> list[dict[str, Any]]:
    """Like all_rows, but returns [] instead of raising if the sheet doesn't exist yet or is empty.
    Used for newer, optional tabs (e.g. Holidays) that older spreadsheets may not have —
    lets the feature degrade gracefully instead of breaking every request."""
    try:
        return all_rows(sheet_name)
    except SheetError:
        logger.info("Optional sheet '%s' not found or empty; treating as no rows.", sheet_name)
        return []


def get_holiday_dates() -> set[str]:
    """Set of 'YYYY-MM-DD' strings from the optional Holidays sheet (columns: ID, Date, Name)."""
    rows = all_rows_optional("Holidays")
    return {str(r.get("Date", "")).strip() for r in rows if str(r.get("Date", "")).strip()}


def find_all_optional(sheet_name: str, column: str, value: Any) -> list[dict[str, Any]]:
    """Like find_all, but returns [] instead of raising if the sheet doesn't exist yet."""
    target = str(value)
    return [row for row in all_rows_optional(sheet_name) if str(row.get(column, "")) == target]


def append_row_optional(sheet_name: str, row_dict: dict[str, Any]) -> bool:
    """Like append_row, but swallows SheetError (logging a warning) instead of raising.
    Used for best-effort side effects (e.g. writing a notification) that shouldn't block
    the main action — like reviewing a task — if the sheet hasn't been set up yet."""
    try:
        append_row(sheet_name, row_dict)
        return True
    except SheetError as e:
        logger.warning("Could not append to optional sheet '%s': %s", sheet_name, e)
        return False


def get_headers(sheet_name: str) -> list[str]:
    request = _values().get(spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!1:1")
    result = _execute_with_retry(request, f"read headers for '{sheet_name}'")
    values = result.get("values", [])
    if not values or not values[0]:
        raise SheetError(f"Sheet '{sheet_name}' has no header row.")
    return values[0]


def find_one(sheet_name: str, column: str, value: Any) -> Optional[dict[str, Any]]:
    """Return the first row where row[column] == str(value), or None."""
    target = str(value)
    for row in all_rows(sheet_name):
        if str(row.get(column, "")) == target:
            return row
    return None


def find_all(sheet_name: str, column: str, value: Any) -> list[dict[str, Any]]:
    target = str(value)
    return [row for row in all_rows(sheet_name) if str(row.get(column, "")) == target]


def find_by_id(sheet_name: str, id_value: Any, id_col: str = "ID") -> Optional[dict[str, Any]]:
    return find_one(sheet_name, id_col, id_value)


def next_id(sheet_name: str, id_col: str = "ID") -> str:
    """Simple incrementing numeric ID: max existing + 1 (as a string). Fine at this scale;
    not safe against true concurrent writes, which the project's known trade-offs accept.

    Deliberately bypasses the all_rows() cache: two ID-generating requests within the
    same cache window must each see the OTHER's latest write, or they'll compute the
    same "next" ID and collide. This is the one place staleness would corrupt data
    (two tasks/leaves/employees sharing one ID) rather than just showing slightly old
    numbers, so it always reads fresh."""
    rows = _read_sheet_uncached(sheet_name)
    max_id = 0
    for row in rows:
        raw = str(row.get(id_col, "")).strip()
        if raw.isdigit():
            max_id = max(max_id, int(raw))
    return str(max_id + 1)


def next_id_optional(sheet_name: str, id_col: str = "ID") -> str:
    """Like next_id, but treats a missing sheet as empty (starts at 1) instead of raising."""
    try:
        rows = _read_sheet_uncached(sheet_name)
    except SheetError:
        rows = []
    max_id = 0
    for row in rows:
        raw = str(row.get(id_col, "")).strip()
        if raw.isdigit():
            max_id = max(max_id, int(raw))
    return str(max_id + 1)


# Cell values starting with one of these characters are interpreted as a
# FORMULA by Google Sheets (and by Excel/LibreOffice if the sheet is ever
# exported) — the exact same way as if someone typed it into a cell by hand.
# Nearly every "table" here stores free text an employee typed directly
# (task descriptions, leave reasons, remarks, addresses, names), so without
# this, a leave "reason" of e.g. `=HYPERLINK("http://evil.example","urgent")`
# would land as a live, clickable formula the instant an admin opens the
# spreadsheet directly — not as inert text. This is the well-known
# "CSV/formula injection" vulnerability class (CWE-1236).
_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@")


def _sanitize_cell(value: str) -> str:
    """Neutralize a value that would otherwise be parsed as a formula.

    Prefixing with a leading apostrophe is the standard mitigation: Sheets
    (under USER_ENTERED, the same parsing mode as typing into the UI) treats
    a leading `'` as a "force text" marker, not as part of the cell's value —
    so this changes nothing about what the app reads back, it only stops the
    spreadsheet itself from ever evaluating the content as a formula.
    """
    if value and value[0] in _FORMULA_TRIGGER_CHARS:
        return "'" + value
    return value


def append_row(sheet_name: str, row_dict: dict[str, Any]) -> None:
    """Append a new row. Missing headers are written as empty strings; extra keys
    in row_dict that don't match a header are ignored."""
    headers = get_headers(sheet_name)
    values = [_sanitize_cell(str(row_dict.get(h, ""))) for h in headers]
    request = _values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    )
    _execute_with_retry(request, f"append row to '{sheet_name}'")
    _invalidate_sheet_cache(sheet_name)


def update_row(sheet_name: str, id_value: Any, updates: dict[str, Any], id_col: str = "ID") -> bool:
    """
    Find the row where id_col == id_value and overwrite just the given fields
    (leaving the rest of that row untouched). Returns False if no matching row exists.
    """
    row = find_by_id(sheet_name, id_value, id_col=id_col)
    if row is None:
        return False

    headers = get_headers(sheet_name)
    row_number = row["_row_number"]

    # Merge: start from the existing row's full values, then apply updates.
    merged = {h: row.get(h, "") for h in headers}
    for k, v in updates.items():
        if k in merged:
            merged[k] = v
        else:
            logger.warning("update_row: '%s' is not a header in '%s', ignoring", k, sheet_name)

    values = [_sanitize_cell(str(merged[h])) for h in headers]
    range_ = f"{sheet_name}!A{row_number}:{_col_letter(len(headers))}{row_number}"
    request = _values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_,
        valueInputOption="USER_ENTERED",
        body={"values": [values]},
    )
    _execute_with_retry(request, f"update row in '{sheet_name}'")
    _invalidate_sheet_cache(sheet_name)
    return True


def _col_letter(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA, ..."""
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters