"""Diagnose the spreadsheet against what the app expects.   python check_sheets.py [email]
Prints missing/misspelled headers, the Departments rows, the Users rows (hash masked),
and, if you pass an email, whether that login exists and is linked to an employee."""
import sys
from sheets_client import _values, SPREADSHEET_ID, _execute_with_retry, all_rows_optional

EXPECTED = {
    "Users": ["ID", "Email", "PasswordHash", "Role", "EmployeeID", "IsActive", "CreatedAt"],
    "Employees": ["ID", "EmployeeCode", "Name", "Email", "Phone", "DOB", "Designation", "DepartmentID", "RoleTitle", "Address", "JoinedDate", "IsActive"],
    "Departments": ["ID", "Name", "Description", "IsActive"],
    "Attendance": ["ID", "EmployeeID", "AttendanceDate", "CheckIn", "CheckOut", "Status"],
    "Tasks": ["ID", "EmployeeID", "ClientName", "ProjectName", "Description", "Status", "Priority", "Remarks", "TaskDate", "AdminStatus", "AdminRemarks", "CreatedAt", "UpdatedAt"],
    "LeaveRequests": ["ID", "EmployeeID", "LeaveType", "FromDate", "ToDate", "Reason", "Status", "AdminRemarks", "ReviewedBy", "CreatedAt", "UpdatedAt"],
}
for tab, want in EXPECTED.items():
    try:
        got = _execute_with_retry(_values().get(spreadsheetId=SPREADSHEET_ID, range=f"{tab}!1:1"), tab).get("values", [[]])[0]
    except Exception as e:
        print(f"MISSING TAB {tab}: {e}"); continue
    bad = [w for w in want if w not in got]
    print(f"{'OK  ' if not bad else 'FIX '} {tab}: raw headers = {[repr(g) for g in got]}" + (f"\n      not an exact match for: {bad}" if bad else ""))

print("\nDepartments rows:")
for r in all_rows_optional("Departments"): print("  ", {k: v for k, v in r.items() if k != "_row_number"})
print("\nUsers rows:")
for r in all_rows_optional("Users"):
    h = str(r.get("PasswordHash", ""))
    print(f"   id={r.get('ID')} email={r.get('Email')!r} role={r.get('Role')} employeeId={r.get('EmployeeID')!r} active={r.get('IsActive')!r} hash={'(EMPTY)' if not h.strip() else h[:7]+'... len '+str(len(h))}")
if len(sys.argv) > 1:
    from sheets_client import find_one
    print("\nLookup:", find_one("Users", "Email", sys.argv[1]))
