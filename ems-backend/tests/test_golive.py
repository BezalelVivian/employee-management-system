"""Go-live / join-date behaviour.

Scenario that started this: an employee joined on 24 Sep, but EMS only went live on 8 Oct. There are no
attendance rows before 8 Oct because nothing could record them, so those days used to show as Absent.
They must show "Not Tracked" instead.
"""
from datetime import date

import pytest

import attendance
import sheets_client as sc
from attendance import build_days, tracking_start
from test_attendance import env  # noqa: F401  (pytest fixture, reused)

GO_LIVE = date(2026, 10, 8)
JOINED_COL, ACTIVE_COL, USER_CREATED_COL = 10, 11, 6


def _statuses(rows):
    return {r["date"]: r["status"] for r in rows}


# ---------- pure logic ----------

def test_tracking_start_is_the_latest_of_the_known_dates(monkeypatch):
    monkeypatch.setattr(attendance, "EMS_START_DATE", GO_LIVE)
    assert tracking_start(date(2026, 9, 24)) == GO_LIVE                      # joined before go-live
    assert tracking_start(date(2026, 10, 20)) == date(2026, 10, 20)           # joined after go-live
    assert tracking_start(date(2026, 9, 1), date(2026, 10, 12)) == date(2026, 10, 12)  # login made later
    monkeypatch.setattr(attendance, "EMS_START_DATE", None)
    assert tracking_start(date(2026, 9, 24)) == date(2026, 9, 24)
    assert tracking_start(None) is None


def test_days_before_go_live_are_not_tracked_not_absent():
    att = [{"AttendanceDate": "2026-10-08", "CheckIn": "2026-10-08T09:30:00", "CheckOut": ""}]
    days = build_days(att, [], set(), date(2026, 9, 24), date(2026, 10, 8), today=GO_LIVE, track_from=GO_LIVE)
    st = _statuses(days)
    assert "Absent" not in st.values()
    assert st["2026-09-24"] == "Not Tracked" and st["2026-10-07"] == "Not Tracked"
    assert st["2026-09-27"] == "Weekly Off"      # Sundays stay accurate
    assert st["2026-10-08"] == "Present"


def test_real_records_before_go_live_always_win():
    """An admin back-filled 30 Sep and approved leave for 1 Oct: both must show, not 'Not Tracked'."""
    att = [{"AttendanceDate": "2026-09-30", "CheckIn": "2026-09-30T10:00:00", "CheckOut": "2026-09-30T18:00:00"}]
    leave = [{"Status": "Approved", "LeaveType": "Sick Leave", "FromDate": "2026-10-01", "ToDate": "2026-10-01"}]
    st = _statuses(build_days(att, leave, set(), date(2026, 9, 29), date(2026, 10, 2), today=GO_LIVE, track_from=GO_LIVE))
    assert st["2026-09-29"] == "Not Tracked"
    assert st["2026-09-30"] == "Present"
    assert st["2026-10-01"] == "On Leave"
    assert st["2026-10-02"] == "Not Tracked"


def test_genuine_absence_after_go_live_is_still_absent():
    st = _statuses(build_days([], [], set(), date(2026, 10, 6), date(2026, 10, 9), today=date(2026, 10, 9), track_from=date(2026, 10, 7)))
    assert st["2026-10-06"] == "Not Tracked"
    assert st["2026-10-07"] == "Absent" and st["2026-10-09"] == "Absent"


def test_recorded_only_never_invents_days():
    att = [{"AttendanceDate": "2026-10-05", "CheckIn": "2026-10-05T10:00:00", "CheckOut": "2026-10-05T18:00:00"}]
    days = build_days(att, [], set(), date(2026, 10, 1), date(2026, 10, 9), today=date(2026, 10, 9), recorded_only=True)
    assert [d["date"] for d in days] == ["2026-10-05"]


# ---------- through the API ----------

def test_employee_history_via_api(env, monkeypatch):  # noqa: F811
    client, store, login = env
    monkeypatch.setattr(attendance, "EMS_START_DATE", GO_LIVE)
    store["Employees"][1][JOINED_COL] = "2026-09-24"
    sc._sheet_cache.clear()
    h = login("bez@x.com", "secret1")

    rows = client.get("/api/employee/attendance", params={"date_from": "2026-09-24", "date_to": "2026-10-07"}, headers=h).json()
    st = _statuses(rows)
    assert len(rows) == 14                       # every day from the joining date, none dropped
    assert "Absent" not in st.values()
    assert st["2026-09-24"] == "Not Tracked" and st["2026-09-27"] == "Weekly Off"

    # filtering by the new status works
    only = client.get("/api/employee/attendance", params={"date_from": "2026-09-24", "date_to": "2026-10-07", "status": "Not Tracked"}, headers=h).json()
    assert len(only) == 12 and all(r["status"] == "Not Tracked" for r in only)


def test_range_entirely_before_joining_is_empty(env):  # noqa: F811
    """Used to fabricate a single 'Absent' row for a day before the person even joined."""
    client, store, login = env
    store["Employees"][1][JOINED_COL] = "2026-09-24"
    sc._sheet_cache.clear()
    h = login("bez@x.com", "secret1")
    assert client.get("/api/employee/attendance", params={"date_from": "2026-09-01", "date_to": "2026-09-10"}, headers=h).json() == []


def test_login_created_after_go_live_covers_back_dated_join_date(env, monkeypatch):  # noqa: F811
    """Employee added to EMS on 12 Oct with a joining date of 1 Oct: 1-11 Oct can't be 'Absent'."""
    client, store, login = env
    monkeypatch.setattr(attendance, "EMS_START_DATE", None)   # no go-live configured at all
    store["Employees"][1][JOINED_COL] = "2026-10-01"
    store["Users"][2][USER_CREATED_COL] = "2026-10-12T10:00:00"
    sc._sheet_cache.clear()
    h = login("bez@x.com", "secret1")
    st = _statuses(client.get("/api/employee/attendance", params={"date_from": "2026-10-01", "date_to": "2026-10-07"}, headers=h).json())
    assert "Absent" not in st.values() and st["2026-10-01"] == "Not Tracked"


def test_admin_listing_and_edit_rules(env, monkeypatch):  # noqa: F811
    client, store, login = env
    monkeypatch.setattr(attendance, "EMS_START_DATE", GO_LIVE)
    store["Employees"][1][JOINED_COL] = "2026-09-24"   # Bez: joined before go-live
    store["Employees"][2][JOINED_COL] = "2026-09-01"   # Ann
    store["Employees"].append(["12", "EMP0012", "Old", "old@x.com", "", "", "", "", "", "", "2026-01-01", "FALSE"])  # ex-employee
    store["Attendance"].append(["1", "12", "2026-10-01", "2026-10-01T10:00:00", "2026-10-01T18:00:00", "Present"])
    sc._sheet_cache.clear()
    a = login("admin@x.com", "adminpw")

    rows = client.get("/api/admin/attendance", params={"date_from": "2026-09-24", "date_to": "2026-10-07"}, headers=a).json()
    assert not [r for r in rows if r["status"] == "Absent"]
    assert {r["employeeName"] for r in rows} == {"Bez", "Ann", "Old"}
    # the ex-employee only appears for the day they really worked
    assert [(r["date"], r["status"]) for r in rows if r["employeeName"] == "Old"] == [("2026-10-01", "Present")]
    # Bez has no rows before joining on the 24th; Ann does
    bez_days = {r["date"] for r in rows if r["employeeName"] == "Bez"}
    ann_days = {r["date"] for r in rows if r["employeeName"] == "Ann"}
    assert min(bez_days) == "2026-09-24" and min(ann_days) == "2026-09-24"   # range start, both joined earlier/equal

    # an admin can back-fill a Not Tracked day (e.g. from a paper register) ...
    ok = client.put("/api/admin/attendance", headers=a, json={"employee_id": "10", "attendance_date": "2026-09-30", "check_in": "09:30", "check_out": "18:00"})
    assert ok.status_code == 200
    # ... but not a day before the person joined
    bad = client.put("/api/admin/attendance", headers=a, json={"employee_id": "10", "attendance_date": "2026-09-20", "check_in": "09:30"})
    assert bad.status_code == 400 and "joined on 24-09-2026" in bad.json()["detail"]


def test_dashboard_does_not_count_future_joiners_as_absent(env):  # noqa: F811
    client, store, login = env
    store["Employees"][1][JOINED_COL] = "2099-01-01"   # Bez hasn't joined yet
    sc._sheet_cache.clear()
    a = login("admin@x.com", "adminpw")
    d = client.get("/api/admin/dashboard", headers=a).json()
    # Ann (joined 2026-01-01) can be estimated absent on a working day, Bez must never be.
    assert d["estimatedAbsentToday"] <= 1


def test_employee_dashboard_before_joining(env):  # noqa: F811
    client, store, login = env
    store["Employees"][1][JOINED_COL] = "2099-01-01"
    sc._sheet_cache.clear()
    h = login("bez@x.com", "secret1")
    today = client.get("/api/employee/dashboard", headers=h).json()["today"]
    assert today["status"] in ("Not joined yet", "Weekly Off", "Holiday")


# ---------- other fixes found in the review ----------

def test_changing_email_to_one_already_used_is_refused(env):  # noqa: F811
    client, store, login = env
    a = login("admin@x.com", "adminpw")
    r = client.patch("/api/admin/employees/10", headers=a, json={"email": "ann@x.com"})
    assert r.status_code == 409 and "already used" in r.json()["detail"]
    assert client.patch("/api/admin/employees/10", headers=a, json={"email": "bez2@x.com"}).status_code == 200
    # the login email moved with it
    assert store["Users"][2][1] == "bez2@x.com"


def test_validation_errors_are_readable(env):  # noqa: F811
    client, store, login = env
    h = login("bez@x.com", "secret1")
    r = client.put("/api/employee/profile", headers=h, json={"phone": "123"})
    assert r.status_code == 422
    msg = r.json()["message"]
    assert msg == "Phone: Phone number must be exactly 10 digits"   # not a Python list/dict dump


def test_history_window_is_capped(env):  # noqa: F811
    client, store, login = env
    store["Employees"][1][JOINED_COL] = "2001-01-01"
    sc._sheet_cache.clear()
    h = login("bez@x.com", "secret1")
    rows = client.get("/api/employee/attendance", params={"date_from": "2001-01-01", "date_to": "2026-10-07"}, headers=h).json()
    assert len(rows) <= 366


def test_config_rejects_a_bad_go_live_date(monkeypatch):
    import importlib, config
    monkeypatch.setenv("EMS_START_DATE", "08-10-2026")
    with pytest.raises(RuntimeError, match="EMS_START_DATE"):
        importlib.reload(config)
    monkeypatch.delenv("EMS_START_DATE")
    importlib.reload(config)


def test_config_cleans_cors_and_service_account(monkeypatch):
    import importlib, config
    monkeypatch.setenv("CORS_ORIGINS", "https://my-ems.vercel.app/, http://localhost:5173")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"private_key": "-----BEGIN-----\\\\nabc\\\\n-----END-----"}')
    importlib.reload(config)
    assert config.CORS_ORIGINS == ["https://my-ems.vercel.app", "http://localhost:5173"]
    assert "\n" in config.get_service_account_info()["private_key"]
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "not json")
    with pytest.raises(RuntimeError, match="not valid JSON"):
        config.get_service_account_info()
    monkeypatch.undo()
    importlib.reload(config)
