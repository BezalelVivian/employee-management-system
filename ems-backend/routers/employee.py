import logging
import threading
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import create_access_token, get_current_user, hash_password, next_token_version, verify_password
from models import ProfileUpdate, TaskCreate, TaskUpdate, LeaveCreate, PasswordChange, PhotoUpload
from sheets_client import (
    all_rows, all_rows_optional, find_by_id, find_one, find_all, find_all_optional,
    append_row, update_row, next_id, get_holiday_dates, get_department_names, set_column_for_rows, SheetError,
)
import photos
from attendance import build_days, entry_from_row, empty_entry
from utils import now, today_date, today_str, to_iso, working_hours_str, is_working_day, parse_date_safe

# History views only backfill this many days before today by default (bounded so a
# long-tenured employee's page load doesn't have to synthesize years of empty rows).
DEFAULT_HISTORY_DAYS = 90
MAX_NOTIFICATIONS = 50  # newest first; keeps the response small however long someone has been here

# Check-in / check-out are read-then-write. Serialize them (single Render instance) and read
# fresh from the sheet, so a double click or two quick taps can never create a second row.
_attendance_lock = threading.Lock()

logger = logging.getLogger("ems.employee")
router = APIRouter(prefix="/api/employee", tags=["employee"])


def _handle_sheet_error(e: SheetError):
    logger.error("Sheets error: %s", e)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


def _my_employee_id(current_user: dict) -> str:
    emp_id = current_user.get("employee_id")
    if not emp_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No employee record linked to this account")
    return emp_id


# ---------- Dashboard ----------

@router.get("/dashboard")
def get_my_dashboard(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        attendance_rows = find_all("Attendance", "EmployeeID", emp_id)
        task_rows = find_all("Tasks", "EmployeeID", emp_id)
        leave_rows = find_all("LeaveRequests", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    today_d = today_date()
    today = today_d.isoformat()
    today_att = next((r for r in attendance_rows if r.get("AttendanceDate") == today and r.get("CheckIn")), None)

    if today_att:
        e = entry_from_row(today, today_att, today=today_d, now_dt=now())
        today_summary = {k: e[k] for k in ("checkIn", "checkOut", "workingHours", "status", "inProgress")}
    else:
        holidays = get_holiday_dates()
        if not is_working_day(today_d, holidays):
            fallback_status = "Holiday" if today in holidays else "Weekly Off"
        else:
            fallback_status = "Not checked in"
        today_summary = {"checkIn": None, "checkOut": None, "workingHours": None,
                         "status": fallback_status, "inProgress": False}

    activity = []
    for r in attendance_rows:
        if r.get("CheckIn"):
            activity.append({
                "type": "attendance",
                "label": f"Checked in at {r['CheckIn'][11:16]}" if len(r["CheckIn"]) >= 16 else "Checked in",
                "timestamp": r.get("CheckIn", ""),
            })
    for r in task_rows:
        if r.get("Status") == "Completed":
            activity.append({
                "type": "task",
                "label": f"Task '{r.get('ProjectName', '')}' marked Completed",
                "timestamp": r.get("UpdatedAt", "") or r.get("CreatedAt", ""),
            })
    for r in leave_rows:
        if r.get("Status") in ("Approved", "Rejected"):
            activity.append({
                "type": "leave",
                "label": f"Leave request {r.get('Status', '').lower()}",
                "timestamp": r.get("UpdatedAt", "") or r.get("CreatedAt", ""),
            })

    activity.sort(key=lambda a: a["timestamp"], reverse=True)

    return {"today": today_summary, "recentActivity": activity[:10]}


# ---------- Profile ----------

@router.get("/profile")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        emp = find_by_id("Employees", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee record not found")
    emp.pop("_row_number", None)
    dept_id = str(emp.get("DepartmentID", "")).strip()
    emp["DepartmentName"] = get_department_names().get(dept_id, dept_id)
    return emp


@router.put("/profile")
def update_my_profile(body: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    updates = {}
    if body.phone is not None:
        updates["Phone"] = body.phone
    if body.address is not None:
        updates["Address"] = body.address
    if body.dob is not None:
        updates["DOB"] = body.dob.isoformat()

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No editable fields provided (only phone, address, dob)")

    try:
        ok = update_row("Employees", emp_id, updates)
    except SheetError as e:
        _handle_sheet_error(e)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee record not found")
    return {"message": "Profile updated"}


# ---------- Profile photo ----------

@router.get("/photo")
def get_my_photo(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    return {"photo": photos.get_photo(emp_id)}


@router.put("/photo")
def set_my_photo(body: PhotoUpload, current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        photos.set_photo(emp_id, body.photo)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Photo updated", "photo": body.photo}


@router.delete("/photo")
def delete_my_photo(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        photos.set_photo(emp_id, "")
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Photo removed"}


# ---------- Password ----------

@router.put("/password")
def change_my_password(body: PasswordChange, current_user: dict = Depends(get_current_user)):
    """Self-service password change for a logged-in employee. Requires knowing the current
    password — this is a *change*, not a *reset*; a locked-out employee still needs an admin
    to reset it via /api/admin/employees/{id}/reset-password."""
    try:
        user = find_one("Users", "Email", current_user["email"])
    except SheetError as e:
        _handle_sheet_error(e)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if not verify_password(body.current_password, user.get("PasswordHash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    new_version = next_token_version(user)
    try:
        # TokenVersion (optional column on Users) invalidates every older login token, e.g. a
        # stolen one or a forgotten device. If the column doesn't exist the bump is skipped.
        updates = {"PasswordHash": hash_password(body.new_password)}
        if "TokenVersion" in user:
            updates["TokenVersion"] = str(new_version)
        update_row("Users", user["ID"], updates)
    except SheetError as e:
        _handle_sheet_error(e)
    # Hand back a fresh token so THIS session keeps working after the version bump.
    token = create_access_token(
        email=user["Email"], role=user.get("Role", ""), employee_id=user.get("EmployeeID", "") or "",
        employee_name=current_user.get("employee_name", ""), token_version=new_version,
    )
    return {"message": "Password updated", "access_token": token}


# ---------- Attendance ----------

def _todays_rows(emp_id: str, today: str) -> list[dict]:
    """Today's Attendance rows for this employee, read fresh from the sheet (not the cache)."""
    rows = find_all("Attendance", "EmployeeID", emp_id, fresh=True)
    return [r for r in rows if r.get("AttendanceDate") == today]


@router.post("/attendance/checkin")
def check_in(current_user: dict = Depends(get_current_user)):
    """One check-in per day. Flexible hours: we only record the time, we don't judge it."""
    emp_id = _my_employee_id(current_user)
    today = today_str()
    with _attendance_lock:
        try:
            todays = _todays_rows(emp_id, today)
            if any(r.get("CheckIn") for r in todays):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already checked in today")

            ts = to_iso(now())
            if todays:  # an empty row for today (e.g. created by an admin) -- fill it in
                update_row("Attendance", todays[0]["ID"], {"CheckIn": ts, "CheckOut": "", "Status": "Present"})
            else:
                append_row("Attendance", {
                    "ID": next_id("Attendance"), "EmployeeID": emp_id, "AttendanceDate": today,
                    "CheckIn": ts, "CheckOut": "", "Status": "Present",
                })
        except SheetError as e:
            _handle_sheet_error(e)
    return {"message": "Checked in", "checkIn": ts, "status": "Present"}


@router.post("/attendance/checkout")
def check_out(current_user: dict = Depends(get_current_user)):
    """Check-out only works after today's check-in, and only once."""
    emp_id = _my_employee_id(current_user)
    today = today_str()
    with _attendance_lock:
        try:
            todays = _todays_rows(emp_id, today)
            row = next((r for r in todays if r.get("CheckIn")), None)
            if row is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="You haven't checked in yet. Please check in first, then check out.")
            if row.get("CheckOut"):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already checked out today")

            ts = to_iso(now())
            update_row("Attendance", row["ID"], {"CheckOut": ts})
        except SheetError as e:
            _handle_sheet_error(e)
    return {"message": "Checked out", "checkOut": ts, "workingHours": working_hours_str(row["CheckIn"], ts)}


@router.get("/attendance")
def get_my_attendance(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
):
    """Day-by-day attendance history (see attendance.build_days for how gaps are filled in)."""
    emp_id = _my_employee_id(current_user)
    try:
        att_rows = find_all("Attendance", "EmployeeID", emp_id)
        leave_rows = find_all("LeaveRequests", "EmployeeID", emp_id)
        emp = find_by_id("Employees", emp_id)
        holidays = get_holiday_dates()
    except SheetError as e:
        _handle_sheet_error(e)

    today = today_date()
    joined = parse_date_safe(emp.get("JoinedDate")) if emp else None

    range_to = min(date_to or today, today)  # never synthesize future days
    range_from = date_from or (today - timedelta(days=DEFAULT_HISTORY_DAYS))
    if joined and joined > range_from:
        range_from = joined  # don't mark someone absent before they joined
    if range_from > range_to:
        range_from = range_to

    result = build_days(att_rows, leave_rows, holidays, range_from, range_to, today=today)
    if status_filter:
        result = [r for r in result if r["status"] == status_filter]
    result.sort(key=lambda r: r["date"], reverse=True)
    return result


# ---------- Tasks ----------

@router.post("/tasks")
def submit_task(body: TaskCreate, current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    ts = to_iso(now())
    row = {
        "ID": next_id("Tasks"),
        "EmployeeID": emp_id,
        "ClientName": body.client_name,
        "ProjectName": body.project_name,
        "Description": body.description,
        "Status": body.status,
        "Priority": body.priority,
        "Remarks": body.remarks,
        "TaskDate": body.task_date.isoformat(),
        "AdminStatus": "Pending",
        "AdminRemarks": "",
        "CreatedAt": ts,
        "UpdatedAt": ts,
    }
    try:
        append_row("Tasks", row)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Task submitted", "id": row["ID"]}


@router.put("/tasks/{task_id}")
def edit_task(task_id: str, body: TaskUpdate, current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        task = find_by_id("Tasks", task_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if task is None or task.get("EmployeeID") != emp_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updates = {
        "ClientName": body.client_name,
        "ProjectName": body.project_name,
        "Description": body.description,
        "Status": body.status,
        "Priority": body.priority,
        "Remarks": body.remarks,
        "TaskDate": body.task_date.isoformat(),
        "AdminStatus": "Pending",  # editing resets admin review
        "UpdatedAt": to_iso(now()),
    }
    try:
        update_row("Tasks", task_id, updates)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Task updated, sent back for admin review"}


@router.get("/tasks")
def get_my_tasks(
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    emp_id = _my_employee_id(current_user)
    try:
        rows = find_all("Tasks", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    result = []
    for r in rows:
        if search:
            haystack = " ".join([r.get("ClientName", ""), r.get("ProjectName", ""), r.get("Description", "")]).lower()
            if search.lower() not in haystack:
                continue
        if status_filter and r.get("Status") != status_filter:
            continue
        if priority and r.get("Priority") != priority:
            continue
        task_date = r.get("TaskDate", "")
        if date_from and task_date < date_from.isoformat():
            continue
        if date_to and task_date > date_to.isoformat():
            continue
        result.append({
            "id": r.get("ID"),
            "clientName": r.get("ClientName"),
            "projectName": r.get("ProjectName"),
            "description": r.get("Description"),
            "status": r.get("Status"),
            "priority": r.get("Priority"),
            "remarks": r.get("Remarks"),
            "taskDate": task_date,
            "adminStatus": r.get("AdminStatus"),
            "adminRemarks": r.get("AdminRemarks"),
        })
    result.sort(key=lambda r: r["taskDate"], reverse=True)
    return result


@router.get("/tasks/summary")
def get_my_task_summary(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        rows = find_all("Tasks", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)
    summary = {"completed": 0, "inProgress": 0, "pending": 0}
    for r in rows:
        s = r.get("Status")
        if s == "Completed":
            summary["completed"] += 1
        elif s == "In Progress":
            summary["inProgress"] += 1
        elif s == "Pending":
            summary["pending"] += 1
    return summary


# ---------- Leave ----------

def _ranges_overlap(a_from: str, a_to: str, b_from: str, b_to: str) -> bool:
    return a_from <= b_to and b_from <= a_to


@router.post("/leave")
def apply_leave(body: LeaveCreate, current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        existing = find_all("LeaveRequests", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    new_from, new_to = body.from_date.isoformat(), body.to_date.isoformat()
    for r in existing:
        if r.get("Status") in ("Pending", "Approved"):
            if _ranges_overlap(r.get("FromDate", ""), r.get("ToDate", ""), new_from, new_to):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This overlaps with an existing pending or approved leave request",
                )

    ts = to_iso(now())
    row = {
        "ID": next_id("LeaveRequests"),
        "EmployeeID": emp_id,
        "LeaveType": body.leave_type,
        "FromDate": new_from,
        "ToDate": new_to,
        "Reason": body.reason,
        "Status": "Pending",
        "AdminRemarks": "",
        "ReviewedBy": "",
        "CreatedAt": ts,
        "UpdatedAt": ts,
    }
    try:
        append_row("LeaveRequests", row)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Leave request submitted", "id": row["ID"]}


@router.get("/leave")
def get_my_leaves(
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    leave_type: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    emp_id = _my_employee_id(current_user)
    try:
        rows = find_all("LeaveRequests", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    result = []
    for r in rows:
        if search and search.lower() not in r.get("Reason", "").lower():
            continue
        if status_filter and r.get("Status") != status_filter:
            continue
        if leave_type and r.get("LeaveType") != leave_type:
            continue
        if date_from and r.get("FromDate", "") < date_from.isoformat():
            continue
        if date_to and r.get("ToDate", "") > date_to.isoformat():
            continue
        result.append({
            "id": r.get("ID"),
            "leaveType": r.get("LeaveType"),
            "fromDate": r.get("FromDate"),
            "toDate": r.get("ToDate"),
            "reason": r.get("Reason"),
            "status": r.get("Status"),
            "adminRemarks": r.get("AdminRemarks"),
        })
    result.sort(key=lambda r: r["fromDate"], reverse=True)
    return result


# ---------- Notifications ----------
# In-app notifications, written when an admin reviews a task or leave request (see
# routers/admin.py). Backed by an optional "Notifications" sheet (ID, EmployeeID, Type,
# Message, RelatedID, IsRead, CreatedAt) — if that sheet doesn't exist yet, this simply
# returns an empty list rather than erroring, so the feature degrades gracefully.

HOLIDAY_NOTICE_DAYS = 14  # holidays this many days ahead appear in the bell


def _dmy(iso: str) -> str:
    d = parse_date_safe(iso)
    return d.strftime("%d-%m-%Y") if d else str(iso)


def _upcoming_holiday_notes() -> list:
    today = today_date()
    notes = []
    for h in _holiday_list():
        d = parse_date_safe(h["date"])
        if d is None or d < today or (d - today).days > HOLIDAY_NOTICE_DAYS:
            continue
        left = (d - today).days
        when = "today" if left == 0 else "tomorrow" if left == 1 else f"in {left} days"
        notes.append({
            "id": f"holiday-{h['date']}", "type": "holiday",
            "message": f"Holiday: {h['name'] or 'Company holiday'} on {_dmy(h['date'])} ({when}).",
            "relatedId": h["date"], "isRead": False, "createdAt": to_iso(now()),
        })
    notes.sort(key=lambda n: n["relatedId"])
    return notes


def _holiday_list() -> list:
    rows = all_rows_optional("Holidays")
    out = [{"id": r.get("ID"), "date": str(r.get("Date", "")).strip(), "name": str(r.get("Name", "")).strip()} for r in rows]
    return sorted((h for h in out if h["date"]), key=lambda h: h["date"])


@router.get("/holidays")
def get_holidays(current_user: dict = Depends(get_current_user)):
    """Holidays from today onwards (next 12 months at most), soonest first."""
    today = today_date()
    res = []
    for h in _holiday_list():
        d = parse_date_safe(h["date"])
        if d and today <= d <= today + timedelta(days=366):
            res.append({"date": h["date"], "name": h["name"], "daysLeft": (d - today).days})
    return res


@router.get("/notifications")
def get_my_notifications(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    rows = find_all_optional("Notifications", "EmployeeID", emp_id)
    result = [
        {
            "id": r.get("ID"),
            "type": r.get("Type"),
            "message": r.get("Message"),
            "relatedId": r.get("RelatedID"),
            "isRead": str(r.get("IsRead", "")).strip().upper() in ("TRUE", "1", "YES"),
            "createdAt": r.get("CreatedAt"),
        }
        for r in rows
    ]
    result.sort(key=lambda n: n["createdAt"] or "", reverse=True)
    result = result[:MAX_NOTIFICATIONS]
    # Upcoming holidays are computed on the fly (no extra sheet writes). The browser keeps
    # track of which ones were read, so they simply drop off the list once the day has passed.
    return _upcoming_holiday_notes() + result


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    try:
        note = find_by_id("Notifications", notification_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if note is None or note.get("EmployeeID") != emp_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    try:
        update_row("Notifications", notification_id, {"IsRead": "TRUE"})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Marked as read"}


@router.patch("/notifications/read-all")
def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    rows = find_all_optional("Notifications", "EmployeeID", emp_id)
    unread_ids = [
        r["ID"] for r in rows
        if str(r.get("IsRead", "")).strip().upper() not in ("TRUE", "1", "YES")
    ]
    if unread_ids:
        # One batched write for all of them (not 3 Google calls per notification).
        try:
            set_column_for_rows("Notifications", "ID", unread_ids, "IsRead", "TRUE")
        except SheetError as e:
            _handle_sheet_error(e)
    return {"message": "All notifications marked as read"}
