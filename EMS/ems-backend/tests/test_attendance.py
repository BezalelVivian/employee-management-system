import os, sys
os.environ.setdefault("SPREADSHEET_ID", "x")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import re
from datetime import date
import pytest
from fastapi.testclient import TestClient

import sheets_client as sc
from utils import today_str, now, to_iso
from attendance import build_days
from auth import hash_password

HEADERS = {
    "Users": ["ID", "Email", "PasswordHash", "Role", "EmployeeID", "IsActive", "CreatedAt", "TokenVersion"],
    "Employees": ["ID", "EmployeeCode", "Name", "Email", "Phone", "DOB", "Designation", "DepartmentID", "RoleTitle", "Address", "JoinedDate", "IsActive"],
    "Attendance": ["ID", "EmployeeID", "AttendanceDate", "CheckIn", "CheckOut", "Status"],
    "Tasks": ["ID", "EmployeeID", "ClientName", "ProjectName", "Description", "Status", "Priority", "Remarks", "TaskDate", "AdminStatus", "AdminRemarks", "CreatedAt", "UpdatedAt"],
    "LeaveRequests": ["ID", "EmployeeID", "LeaveType", "FromDate", "ToDate", "Reason", "Status", "AdminRemarks", "ReviewedBy", "CreatedAt", "UpdatedAt"],
}


class FakeReq:
    def __init__(self, fn): self.fn = fn
    def execute(self): return self.fn()


class FakeValues:
    def __init__(self, store): self.store = store
    def get(self, spreadsheetId, range):
        name = range.split("!")[0]
        if name not in self.store: raise sc.SheetError(f"no sheet {name}")
        data = self.store[name]
        if "!1:1" in range: return FakeReq(lambda: {"values": [data[0]]})
        return FakeReq(lambda: {"values": [list(r) for r in data]})
    def append(self, spreadsheetId, range, valueInputOption, insertDataOption, body):
        assert valueInputOption == "RAW"
        def go(): self.store[range].append(body["values"][0]); return {}
        return FakeReq(go)
    def batchUpdate(self, spreadsheetId, body):
        assert body["valueInputOption"] == "RAW"
        def go():
            self.calls = getattr(self, "calls", 0) + 1
            for d in body["data"]:
                m = re.match(r"(\w+)!([A-Z]+)(\d+)$", d["range"])
                name, col, rown = m.group(1), ord(m.group(2)) - 65, int(m.group(3))
                self.store[name][rown - 1][col] = d["values"][0][0]
            return {}
        return FakeReq(go)
    def update(self, spreadsheetId, range, valueInputOption, body):
        assert valueInputOption == "RAW"
        m = re.match(r"(\w+)!A(\d+):", range)
        name, rown = m.group(1), int(m.group(2))
        def go(): self.store[name][rown - 1] = body["values"][0]; return {}
        return FakeReq(go)


@pytest.fixture()
def env(monkeypatch):
    store = {k: [list(v)] for k, v in HEADERS.items()}
    store["Users"] += [
        ["1", "admin@x.com", hash_password("adminpw"), "admin", "", "TRUE", "", "0"],
        ["2", "bez@x.com", hash_password("secret1"), "employee", "10", "TRUE", "", "0"],
    ]
    store["Employees"].append(["10", "EMP0010", "Bez", "bez@x.com", "", "", "", "", "", "", "2026-01-01", "TRUE"])
    store["Employees"].append(["11", "EMP0011", "Ann", "ann@x.com", "", "", "", "", "", "", "2026-01-01", "TRUE"])
    monkeypatch.setattr(sc, "_values", lambda: FakeValues(store))
    monkeypatch.setattr(sc, "_execute_with_retry", lambda req, action: req.execute())
    sc._sheet_cache.clear()
    import main
    from routers.auth import limiter
    limiter.reset()  # tests log in many times; the real 10/min login limit is left untouched
    client = TestClient(main.app)

    def login(email, pw):
        r = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return client, store, login


def test_checkin_checkout_flow(env):
    client, store, login = env
    h = login("bez@x.com", "secret1")

    # check-out before check-in is refused with a clear message
    r = client.post("/api/employee/attendance/checkout", headers=h)
    assert r.status_code == 400 and "check in first" in r.json()["detail"].lower()

    assert client.post("/api/employee/attendance/checkin", headers=h).status_code == 200
    # second check-in blocked, single row only
    r = client.post("/api/employee/attendance/checkin", headers=h)
    assert r.status_code == 409
    assert len(store["Attendance"]) == 2

    # times are stored as ISO text, never flagged "Late"
    row = store["Attendance"][1]
    assert re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$", row[3]) and row[5] == "Present"

    d = client.get("/api/employee/dashboard", headers=h).json()["today"]
    assert d["checkIn"] and d["status"] == "Present" and d["inProgress"] and d["workingHours"]

    assert client.post("/api/employee/attendance/checkout", headers=h).status_code == 200
    assert client.post("/api/employee/attendance/checkout", headers=h).status_code == 409


def test_sheet_locale_dates_are_normalised(env):
    """Simulates Google Sheets having converted cells into real dates (old USER_ENTERED rows)."""
    client, store, login = env
    h = login("bez@x.com", "secret1")
    t = now()
    store["Attendance"].append(["5", "10", f"{t.month}/{t.day}/{t.year}", f"{t.month}/{t.day}/{t.year} 10:05:00", "", "Late"])
    sc._sheet_cache.clear()

    d = client.get("/api/employee/dashboard", headers=h).json()["today"]
    assert d["checkIn"] == f"{t.year}-{t.month:02d}-{t.day:02d}T10:05:00"
    assert d["status"] == "Present"           # old stored "Late" is ignored: hours are flexible
    # and check-in is correctly detected as already done despite the odd date format
    assert client.post("/api/employee/attendance/checkin", headers=h).status_code == 409


def test_missing_checkout_and_admin_fix(env):
    client, store, login = env
    h, a = login("bez@x.com", "secret1"), login("admin@x.com", "adminpw")
    store["Attendance"].append(["7", "10", "2026-09-22", "2026-09-22T11:00:00", "", "Present"])
    sc._sheet_cache.clear()
    rows = client.get("/api/employee/attendance", params={"date_from": "2026-09-22", "date_to": "2026-09-22"}, headers=h).json()
    assert rows[0]["status"] == "Missing Check-out" and rows[0]["workingHours"] is None

    r = client.put("/api/admin/attendance", headers=a, json={
        "employee_id": "10", "attendance_date": "2026-09-22", "check_in": "11:00", "check_out": "19:30"})
    assert r.status_code == 200
    rows = client.get("/api/employee/attendance", params={"date_from": "2026-09-22", "date_to": "2026-09-22"}, headers=h).json()
    assert rows[0]["status"] == "Present" and rows[0]["workingHours"] == "8h 30m"

    # bad edits
    assert client.put("/api/admin/attendance", headers=a, json={
        "employee_id": "10", "attendance_date": "2026-09-22", "check_in": "11:00", "check_out": "10:00"}).status_code == 400
    assert client.put("/api/admin/attendance", headers=h, json={
        "employee_id": "10", "attendance_date": "2026-09-22", "check_in": "11:00"}).status_code == 403

    # admin creates a missing day
    assert client.put("/api/admin/attendance", headers=a, json={
        "employee_id": "10", "attendance_date": "2026-09-21", "check_in": "10:00", "check_out": "18:00"}).status_code == 200
    listing = client.get("/api/admin/attendance", params={"date_from": "2026-09-21", "date_to": "2026-09-22"}, headers=a).json()
    assert {(r["employeeName"], r["date"], r["status"]) for r in listing} >= {("Bez", "2026-09-21", "Present"), ("Ann", "2026-09-22", "Absent")}


def test_permission_leave_not_full_day_and_dashboard(env):
    client, store, login = env
    a = login("admin@x.com", "adminpw")
    today = today_str()
    store["LeaveRequests"].append(["1", "10", "Permission", today, today, "", "Approved", "", "", "", ""])
    store["LeaveRequests"].append(["2", "11", "Sick Leave", today, today, "", "Approved", "", "", "", ""])
    sc._sheet_cache.clear()
    d = client.get("/api/admin/dashboard", headers=a).json()
    assert d["onLeaveToday"] == 1  # only Ann's full-day leave


def test_password_change_keeps_session_and_kills_old_token(env):
    client, store, login = env
    old = login("bez@x.com", "secret1")
    r = client.put("/api/employee/password", headers=old, json={"current_password": "secret1", "new_password": "newpass1"})
    assert r.status_code == 200
    new = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/employee/profile", headers=new).status_code == 200
    assert client.get("/api/employee/profile", headers=old).status_code == 401


def test_role_comes_from_sheet(env):
    client, store, login = env
    a = login("admin@x.com", "adminpw")
    assert client.get("/api/admin/dashboard", headers=a).status_code == 200
    store["Users"][1][3] = "employee"  # demote
    sc._sheet_cache.clear()
    assert client.get("/api/admin/dashboard", headers=a).status_code == 403


def test_real_sheet_rows_from_startup(env):
    """The exact shapes seen in the live sheet: CheckIn as a Sheets date serial, CheckOut as
    'YYYY-MM-DD HH:MM:SS' text, old Status 'Late'."""
    client, store, login = env
    h = login("bez@x.com", "secret1")
    store["Attendance"] += [
        ["1", "10", "2026-09-26", "46291.67885", "2026-09-26 16:17:56", "Late"],
        ["2", "10", "2026-09-28", "46293.48134", "2026-09-28 11:33:15", "Late"],
    ]
    sc._sheet_cache.clear()
    rows = client.get("/api/employee/attendance", params={"date_from": "2026-09-26", "date_to": "2026-09-28"}, headers=h).json()
    by = {r["date"]: r for r in rows}
    assert by["2026-09-26"]["checkIn"].startswith("2026-09-26T16:17")
    assert by["2026-09-26"]["checkOut"] == "2026-09-26T16:17:56"
    assert by["2026-09-26"]["status"] == "Present" and by["2026-09-26"]["workingHours"] == "0h 0m"
    assert by["2026-09-28"]["checkIn"].startswith("2026-09-28T11:33")
    assert by["2026-09-28"]["status"] == "Present"


def test_departments(env):
    client, store, login = env
    store["Departments"] = [["ID", "Name", "Description", "IsActive"],
                            ["2", "Information Technology", "Software", "TRUE"],
                            ["9", "Old Dept", "x", "FALSE"]]
    store["Employees"][1][7] = "2"
    sc._sheet_cache.clear()
    a, h = login("admin@x.com", "adminpw"), login("bez@x.com", "secret1")
    depts = client.get("/api/admin/departments", headers=a).json()
    assert [d["Name"] for d in depts] == ["Information Technology"]
    assert client.get("/api/employee/profile", headers=h).json()["DepartmentName"] == "Information Technology"
    emps = client.get("/api/admin/employees", headers=a).json()
    assert emps[0]["DepartmentName"] == "Information Technology"


# ---------- photos / notifications / holidays ----------

import base64

def _jpeg(n=2000):
    return "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"a" * n).decode()


def test_photo_upload_replace_remove_and_validation(env):
    client, store, login = env
    store["Photos"] = [["EmployeeID", "Photo", "UpdatedAt"]]
    h, a = login("bez@x.com", "secret1"), login("admin@x.com", "adminpw")

    assert client.get("/api/employee/photo", headers=h).json() == {"photo": None}
    p1 = _jpeg()
    assert client.put("/api/employee/photo", headers=h, json={"photo": p1}).status_code == 200
    assert client.get("/api/employee/photo", headers=h).json()["photo"] == p1
    # replacing keeps ONE row per employee
    p2 = _jpeg(3000)
    assert client.put("/api/employee/photo", headers=h, json={"photo": p2}).status_code == 200
    assert len(store["Photos"]) == 2 and store["Photos"][1][1] == p2

    # rejected: not a jpeg data URL, not base64, not really a jpeg, too big
    bad = ["hello", "data:image/png;base64,AAAA", "data:image/jpeg;base64,!!notb64!!",
           "data:image/jpeg;base64," + base64.b64encode(b"not a jpeg").decode(), _jpeg(60000)]
    for b in bad:
        assert client.put("/api/employee/photo", headers=h, json={"photo": b}).status_code == 422, b[:40]
    assert len(store["Photos"]) == 2

    # admin sees it, can set another employee's photo, and remove it
    assert client.get("/api/admin/photos", headers=a).json() == {"10": p2}
    assert client.put("/api/admin/employees/11/photo", headers=a, json={"photo": p1}).status_code == 200
    assert set(client.get("/api/admin/photos", headers=a).json()) == {"10", "11"}
    assert client.put("/api/admin/employees/99/photo", headers=a, json={"photo": p1}).status_code == 404
    assert client.delete("/api/admin/employees/11/photo", headers=a).status_code == 200
    assert set(client.get("/api/admin/photos", headers=a).json()) == {"10"}
    # an employee cannot use the admin endpoints
    assert client.put("/api/admin/employees/11/photo", headers=h, json={"photo": p1}).status_code == 403
    assert client.delete("/api/employee/photo", headers=h).status_code == 200
    assert client.get("/api/employee/photo", headers=h).json() == {"photo": None}


def test_photo_without_photos_tab_does_not_break(env):
    client, store, login = env
    h, a = login("bez@x.com", "secret1"), login("admin@x.com", "adminpw")
    assert client.get("/api/employee/photo", headers=h).json() == {"photo": None}
    assert client.get("/api/admin/photos", headers=a).json() == {}
    r = client.put("/api/employee/photo", headers=h, json={"photo": _jpeg()})
    assert r.status_code == 503 and "Photos" in r.json()["detail"]
    assert client.get("/api/employee/profile", headers=h).status_code == 200


def test_notifications_flow_and_batched_read_all(env):
    client, store, login = env
    store["Notifications"] = [["ID", "EmployeeID", "Type", "Message", "RelatedID", "IsRead", "CreatedAt"]]
    h, a = login("bez@x.com", "secret1"), login("admin@x.com", "adminpw")

    for i in range(3):
        d = f"2026-10-0{i + 1}"
        lid = client.post("/api/employee/leave", headers=h, json={"leave_type": "Sick Leave", "from_date": d, "to_date": d}).json()["id"]
        assert client.patch(f"/api/admin/leaves/{lid}/review", headers=a, json={"status": "Approved"}).status_code == 200
    tid = client.post("/api/employee/tasks", headers=h, json={
        "client_name": "C", "project_name": "P", "status": "Pending", "priority": "Low", "task_date": "2026-09-28"}).json()["id"]
    assert client.patch(f"/api/admin/tasks/{tid}/review", headers=a, json={"admin_status": "Approved"}).status_code == 200

    notes = client.get("/api/employee/notifications", headers=h).json()
    assert len(notes) == 4 and not any(n["isRead"] for n in notes)
    assert {n["type"] for n in notes} == {"leave", "task"}
    # other people don't get them
    assert len(store["Notifications"]) == 5 and all(r[1] == "10" for r in store["Notifications"][1:])

    one = notes[0]["id"]
    assert client.patch(f"/api/employee/notifications/{one}/read", headers=h).status_code == 200
    assert sum(n["isRead"] for n in client.get("/api/employee/notifications", headers=h).json()) == 1

    assert client.patch("/api/employee/notifications/read-all", headers=h).status_code == 200
    assert all(n["isRead"] for n in client.get("/api/employee/notifications", headers=h).json())
    assert all(r[5] == "TRUE" for r in store["Notifications"][1:])


def test_notifications_missing_tab_never_blocks_reviews(env):
    client, store, login = env
    h, a = login("bez@x.com", "secret1"), login("admin@x.com", "adminpw")
    lid = client.post("/api/employee/leave", headers=h, json={"leave_type": "Sick Leave", "from_date": "2026-10-05", "to_date": "2026-10-05"}).json()["id"]
    assert client.patch(f"/api/admin/leaves/{lid}/review", headers=a, json={"status": "Rejected"}).status_code == 200
    assert client.get("/api/employee/notifications", headers=h).json() == []
    assert client.patch("/api/employee/notifications/read-all", headers=h).status_code == 200


def test_holidays_tab_turns_absent_into_holiday(env):
    client, store, login = env
    h = login("bez@x.com", "secret1")
    day = "2026-09-23"  # a Wednesday
    q = {"date_from": day, "date_to": day}
    assert client.get("/api/employee/attendance", params=q, headers=h).json()[0]["status"] == "Absent"
    store["Holidays"] = [["ID", "Date", "Name"], ["1", "9/23/2026", "Festival"]]  # Sheets-style date too
    sc._sheet_cache.clear()
    assert client.get("/api/employee/attendance", params=q, headers=h).json()[0]["status"] == "Holiday"


def test_holidays_admin_add_list_remove_and_notify(env):
    client, store, login = env
    h, a = login("bez@x.com", "secret1"), login("admin@x.com", "adminpw")
    store["Holidays"] = [["ID", "Date", "Name"]]
    sc._sheet_cache.clear()
    from utils import today_date
    soon = (today_date()).isoformat()
    assert client.post("/api/admin/holidays", headers=a, json={"date": soon, "name": "Founders Day"}).status_code == 201
    assert client.post("/api/admin/holidays", headers=a, json={"date": soon, "name": "Dup"}).status_code == 409
    notes = client.get("/api/employee/notifications", headers=h).json()
    assert notes[0]["type"] == "holiday" and "Founders Day" in notes[0]["message"]
    assert client.get("/api/employee/holidays", headers=h).json()[0]["name"] == "Founders Day"
    hid = client.get("/api/admin/holidays", headers=a).json()[0]["id"]
    assert client.delete(f"/api/admin/holidays/{hid}", headers=a).status_code == 200
    assert client.get("/api/admin/holidays", headers=a).json() == []


def test_pre_ems_days_are_not_marked_absent(monkeypatch):
    """If EMS goes live on Oct 8, a Sep 24 joiner has no attendance history before Oct 8."""
    import attendance
    monkeypatch.setattr(
        attendance,
        "is_attendance_tracking_day",
        lambda d: d >= date(2026, 10, 8),
    )
    rows = build_days(
        [], [], set(),
        date(2026, 9, 24),
        date(2026, 10, 8),
        today=date(2026, 10, 8),
    )
    assert [r["date"] for r in rows] == ["2026-10-08"]
    assert rows[0]["status"] == "Absent"
