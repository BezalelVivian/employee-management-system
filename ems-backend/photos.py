"""Employee profile photos.

Stored in their own optional `Photos` tab (EmployeeID, Photo, UpdatedAt) as a small JPEG data URL,
NOT in the Employees tab: that tab is read on almost every request, and embedding ~30 KB per
person in it would make every page heavier and eat into the Sheets read quota. Here a photo is
only read when a photo endpoint is called (and is cached like every other sheet read).

A missing Photos tab never breaks anything: reads return "no photo", and an upload explains
what to add.
"""
import threading

from sheets_client import all_rows, all_rows_optional, append_row, update_row, SheetError
from utils import now, to_iso

SHEET = "Photos"
_lock = threading.Lock()

SETUP_HINT = (
    "Photo storage isn't set up yet: add a 'Photos' tab with the headers "
    "EmployeeID, Photo, UpdatedAt (or run setup_sheets.py)."
)


def _rows_by_employee() -> dict[str, dict]:
    return {str(r.get("EmployeeID", "")).strip(): r for r in all_rows_optional(SHEET)}


def get_photo(employee_id: str) -> str | None:
    row = _rows_by_employee().get(str(employee_id).strip())
    return (row.get("Photo") or None) if row else None


def all_photos() -> dict[str, str]:
    return {eid: r["Photo"] for eid, r in _rows_by_employee().items() if eid and r.get("Photo")}


def set_photo(employee_id: str, data_url: str) -> None:
    """Insert or replace (one row per employee, never duplicates). data_url "" clears it."""
    eid = str(employee_id).strip()
    fields = {"Photo": data_url, "UpdatedAt": to_iso(now())}
    with _lock:
        try:
            existing = next(
                (r for r in all_rows(SHEET, fresh=True) if str(r.get("EmployeeID", "")).strip() == eid), None
            )
            if existing:
                update_row(SHEET, eid, fields, id_col="EmployeeID")
            elif data_url:
                append_row(SHEET, {"EmployeeID": eid, **fields})
        except SheetError as e:
            raise SheetError(SETUP_HINT) from e
