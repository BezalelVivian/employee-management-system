import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import create_access_token, get_current_user, get_token_version, hash_password, verify_password
from models import ProfileUpdate, TaskCreate, TaskUpdate, LeaveCreate, PasswordChange
from sheets_client import (
    all_rows, find_by_id, find_one, find_all, find_all_optional,
    append_row, update_row, next_id, get_holiday_dates, SheetError,
)
from utils import now, today_str, to_iso, is_late, working_hours_str, is_working_day, parse_date_safe

# History views only backfill this many days before today by default (bounded so a
# long-tenured employee's page load doesn't have to synthesize years of empty rows).
DEFAULT_HISTORY_DAYS = 90

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

    today = today_str()
    today_att = next((r for r in attendance_rows if r.get("AttendanceDate") == today), None)

    if today_att:
        today_summary = {
            "checkIn": today_att.get("CheckIn") or None,
            "checkOut": today_att.get("CheckOut") or None,
            "workingHours": working_hours_str(today_att.get("CheckIn", ""), today_att.get("CheckOut", "")),
            "status": today_att.get("Status") or "Absent",
        }
    else:
        holidays = get_holiday_dates()
        today_date = date.today()
        if not is_working_day(today_date, holidays):
            fallback_status = "Holiday" if today_date.isoformat() in holidays else "Weekly Off"
        else:
            fallback_status = "Absent"
        today_summary = {"checkIn": None, "checkOut": None, "workingHours": None, "status": fallback_status}

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

    try:
        update_row("Users", user["ID"], {"PasswordHash": hash_password(body.new_password)})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Password updated"}


# ---------- Attendance ----------

@router.post("/attendance/checkin")
def check_in(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    today = today_str()
    try:
        existing = find_all("Attendance", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    todays_row = next((r for r in existing if r.get("AttendanceDate") == today), None)
    if todays_row and todays_row.get("CheckIn"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in today")

    ts = now()
    status_val = "Late" if is_late(ts) else "Present"
    row = {
        "ID": next_id("Attendance"),
        "EmployeeID": emp_id,
        "AttendanceDate": today,
        "CheckIn": to_iso(ts),
        "CheckOut": "",
        "Status": status_val,
    }
    try:
        if todays_row:
            update_row("Attendance", todays_row["ID"], {"CheckIn": to_iso(ts), "Status": status_val})
        else:
            append_row("Attendance", row)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Checked in", "checkIn": row["CheckIn"], "status": status_val}


@router.post("/attendance/checkout")
def check_out(current_user: dict = Depends(get_current_user)):
    emp_id = _my_employee_id(current_user)
    today = today_str()
    try:
        existing = find_all("Attendance", "EmployeeID", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    todays_row = next((r for r in existing if r.get("AttendanceDate") == today), None)
    if not todays_row or not todays_row.get("CheckIn"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must check in before checking out")
    if todays_row.get("CheckOut"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked out today")

    ts = to_iso(now())
    try:
        update_row("Attendance", todays_row["ID"], {"CheckOut": ts})
    except SheetError as e:
        _handle_sheet_error(e)
    return {
        "message": "Checked out",
        "checkOut": ts,
        "workingHours": working_hours_str(todays_row.get("CheckIn", ""), ts),
    }


@router.get("/attendance")
def get_my_attendance(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
):
    """
    Day-by-day attendance history. Unlike the raw Attendance sheet (which only has a row
    for days someone actually checked in), this fills in every day in range with its real
    status: Present/Late (from a row), On Leave (approved leave covers that day), Holiday /
    Weekly Off (from the Holidays sheet + Sunday), or Absent (a working day with no check-in
    and nothing else explaining it).
    """
    emp_id = _my_employee_id(current_user)
    try:
        att_rows = find_all("Attendance", "EmployeeID", emp_id)
        leave_rows = find_all("LeaveRequests", "EmployeeID", emp_id)
        emp = find_by_id("Employees", emp_id)
    except SheetError as e:
        _handle_sheet_error(e)

    holidays = get_holiday_dates()
    today = date.today()
    joined = parse_date_safe(emp.get("JoinedDate")) if emp else None

    range_to = date_to or today
    if range_to > today:
        range_to = today  # never synthesize future days

    default_from = today - timedelta(days=DEFAULT_HISTORY_DAYS)
    range_from = date_from or default_from
    if joined and joined > range_from:
        range_from = joined  # don't mark someone absent before they joined
    if range_from > range_to:
        range_from = range_to

    by_date = {r.get("AttendanceDate"): r for r in att_rows if r.get("AttendanceDate")}

    approved_leave_days = set()
    for lr in leave_rows:
        if lr.get("Status") != "Approved":
            continue
        f, t = parse_date_safe(lr.get("FromDate")), parse_date_safe(lr.get("ToDate"))
        if not f or not t:
            continue
        d = f
        while d <= t:
            approved_leave_days.add(d.isoformat())
            d += timedelta(days=1)

    result = []
    d = range_from
    while d <= range_to:
        ds = d.isoformat()
        row = by_date.get(ds)
        if row:
            entry = {
                "date": ds,
                "checkIn": row.get("CheckIn") or None,
                "checkOut": row.get("CheckOut") or None,
                "workingHours": working_hours_str(row.get("CheckIn", ""), row.get("CheckOut", "")),
                "status": row.get("Status") or "Absent",
            }
        elif ds in approved_leave_days:
            entry = {"date": ds, "checkIn": None, "checkOut": None, "workingHours": None, "status": "On Leave"}
        elif not is_working_day(d, holidays):
            entry = {
                "date": ds, "checkIn": None, "checkOut": None, "workingHours": None,
                "status": "Holiday" if ds in holidays else "Weekly Off",
            }
        else:
            entry = {"date": ds, "checkIn": None, "checkOut": None, "workingHours": None, "status": "Absent"}
        result.append(entry)
        d += timedelta(days=1)

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
    return result


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
    for r in rows:
        if str(r.get("IsRead", "")).strip().upper() not in ("TRUE", "1", "YES"):
            try:
                update_row("Notifications", r["ID"], {"IsRead": "TRUE"})
            except SheetError as e:
                _handle_sheet_error(e)
    return {"message": "All notifications marked as read"}