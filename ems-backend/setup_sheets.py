"""One-off helper: create the optional tabs this app uses, with the right headers.

    python setup_sheets.py

Safe to run any number of times:
  * it only ADDS -- it never deletes, clears or rewrites any existing tab or row;
  * a tab that already exists is left alone (missing header names are appended to the end
    of its header row, existing columns are never moved);
  * it uses the same env vars as the app (SPREADSHEET_ID + service account credentials).

Tabs handled:
    Holidays        ID, Date, Name
    Notifications   ID, EmployeeID, Type, Message, RelatedID, IsRead, CreatedAt
    Photos          EmployeeID, Photo, UpdatedAt
"""
from sheets_client import _get_service, SPREADSHEET_ID, _execute_with_retry, _col_letter

TABS = {
    "Holidays": ["ID", "Date", "Name"],
    "Notifications": ["ID", "EmployeeID", "Type", "Message", "RelatedID", "IsRead", "CreatedAt"],
    "Photos": ["EmployeeID", "Photo", "UpdatedAt"],
}


def main() -> None:
    sheets = _get_service().spreadsheets()
    meta = _execute_with_retry(sheets.get(spreadsheetId=SPREADSHEET_ID, fields="sheets.properties.title"), "list tabs")
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}

    to_add = [t for t in TABS if t not in existing]
    if to_add:
        body = {"requests": [{"addSheet": {"properties": {"title": t}}} for t in to_add]}
        _execute_with_retry(sheets.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body), "create tabs")

    for tab, wanted in TABS.items():
        got = _execute_with_retry(
            sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=f"{tab}!1:1"), f"read '{tab}' headers"
        ).get("values", [[]])
        current = [h.strip() for h in (got[0] if got else [])]
        missing = [h for h in wanted if h not in current]
        if not missing:
            print(f"OK       {tab}: already has all headers")
            continue
        new_header = current + missing
        _execute_with_retry(
            sheets.values().update(
                spreadsheetId=SPREADSHEET_ID, range=f"{tab}!A1:{_col_letter(len(new_header))}1",
                valueInputOption="RAW", body={"values": [new_header]},
            ),
            f"write '{tab}' headers",
        )
        verb = "created" if tab in to_add else "added headers to"
        print(f"DONE     {verb} {tab}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
