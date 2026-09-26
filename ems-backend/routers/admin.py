import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin, hash_password
from models import EmployeeCreate, EmployeeAdminUpdate, TaskReview, LeaveReview, AdminPasswordReset
from sheets_client import (
    all_rows, find_by_id, find_one, find_all,
    append_row, append_row_optional, update_row, next_id, next_id_optional, get_holiday_dates, SheetError,
)
from utils import today_str, to_iso, now, is_working_day

logger = logging.getLogger("ems.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _handle_sheet_error(e: SheetError):
    logger.error("Sheets error: %s", e)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


def _employee_name_map() -> dict:
    try:
        emps = all_rows("Employees")
    except SheetError as e:
        _handle_sheet_error(e)
    return {e.get("ID"): e.get("Name", "") for e in emps}


def _notify(employee_id: str, ntype: str, message: str, related_id: str = "") -> None:
    """Best-effort: write an in-app notification for the employee. Never blocks the
    calling action (e.g. a review) if the Notifications sheet isn't set up yet."""
    if not employee_id:
        return
    try:
        append_row_optional("Notifications", {
            "ID": next_id_optional("Notifications"),
            "EmployeeID": employee_id,
            "Type": ntype,
            "Message": message,
            "RelatedID": related_id,
            "IsRead": "FALSE",
            "CreatedAt": to_iso(now()),
        })
    except Exception:
        logger.exception("Failed to write notification for employee %s (non-fatal)", employee_id)


# ---------- Dashboard ----------

@router.get("/dashboard")
def get_admin_dashboard():
    try:
        employees = all_rows("Employees")
        attendance = all_rows("Attendance")
        leaves = all_rows("LeaveRequests")
        tasks = all_rows("Tasks")
    except SheetError as e:
        _handle_sheet_error(e)

    total_employees = len(employees)
    active_employees = sum(1 for e in employees if str(e.get("IsActive", "")).strip().upper() in ("TRUE", "1", "YES"))

    today = today_str()
    present_today = sum(
        1 for a in attendance
        if a.get("AttendanceDate") == today and a.get("Status") in ("Present", "Late")
    )
    on_leave_today = sum(
        1 for l in leaves
        if l.get("Status") == "Approved" and l.get("FromDate", "") <= today <= l.get("ToDate", "")
    )
    pending_leaves = sum(1 for l in leaves if l.get("Status") == "Pending")
    pending_tasks = sum(1 for t in tasks if t.get("AdminStatus") == "Pending")

    # On a Sunday or a listed holiday, nobody is expected in, so don't report a misleading
    # "absent" count just because check-in rows are naturally empty that day.
    holidays = get_holiday_dates()
    if is_working_day(date.today(), holidays):
        estimated_absent = max(0, active_employees - present_today - on_leave_today)
    else:
        estimated_absent = 0

    return {
        "totalEmployees": total_employees,
        "activeEmployees": active_employees,
        "presentToday": present_today,
        "onLeaveToday": on_leave_today,
        "estimatedAbsentToday": estimated_absent,
        "pendingLeaveRequests": pending_leaves,
        "pendingTaskReviews": pending_tasks,
    }


# ---------- Departments (read-only) ----------

@router.get("/departments")
def list_departments():
    try:
        return all_rows("Departments")
    except SheetError as e:
        _handle_sheet_error(e)


# ---------- Employees ----------

@router.get("/employees")
def list_employees():
    try:
        rows = all_rows("Employees")
    except SheetError as e:
        _handle_sheet_error(e)
    for r in rows:
        r.pop("_row_number", None)
    return rows


@router.post("/employees", status_code=status.HTTP_201_CREATED)
def create_employee(body: EmployeeCreate):
    try:
        if find_one("Users", "Email", body.email) or find_one("Employees", "Email", body.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    except SheetError as e:
        _handle_sheet_error(e)

    emp_id = next_id("Employees")
    emp_row = {
        "ID": emp_id,
        "EmployeeCode": f"EMP{emp_id.zfill(4)}",
        "Name": body.name,
        "Email": body.email,
        "Phone": body.phone,
        "DOB": body.dob.isoformat() if body.dob else "",
        "Designation": body.designation,
        "DepartmentID": body.department_id,
        "RoleTitle": body.role_title,
        "Address": body.address,
        "JoinedDate": body.joined_date.isoformat(),
        "IsActive": "TRUE",
    }
    user_row = {
        "ID": next_id("Users"),
        "Email": body.email,
        "PasswordHash": hash_password(body.temp_password),
        "Role": "employee",
        "EmployeeID": emp_id,
        "IsActive": "TRUE",
        "CreatedAt": to_iso(now()),
    }
    try:
        append_row("Employees", emp_row)
        append_row("Users", user_row)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Employee created", "employeeId": emp_id, "employeeCode": emp_row["EmployeeCode"]}


@router.patch("/employees/{employee_id}/toggle-active")
def toggle_employee_active(employee_id: str):
    try:
        emp = find_by_id("Employees", employee_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    currently_active = str(emp.get("IsActive", "")).strip().upper() in ("TRUE", "1", "YES")
    new_value = "FALSE" if currently_active else "TRUE"

    try:
        update_row("Employees", employee_id, {"IsActive": new_value})
        user = find_one("Users", "EmployeeID", employee_id)
        if user:
            update_row("Users", user["ID"], {"IsActive": new_value})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": f"Employee is now {'active' if new_value == 'TRUE' else 'inactive'}"}


@router.patch("/employees/{employee_id}")
def admin_update_employee(employee_id: str, body: EmployeeAdminUpdate):
    updates = {}
    field_map = {
        "employee_code": "EmployeeCode",
        "name": "Name",
        "email": "Email",
        "designation": "Designation",
        "department_id": "DepartmentID",
        "role_title": "RoleTitle",
    }
    for attr, header in field_map.items():
        val = getattr(body, attr)
        if val is not None:
            updates[header] = val
    if body.joined_date is not None:
        updates["JoinedDate"] = body.joined_date.isoformat()

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    try:
        ok = update_row("Employees", employee_id, updates)
        # Keep Users.Email in sync if email changed
        if ok and "Email" in updates:
            user = find_one("Users", "EmployeeID", employee_id)
            if user:
                update_row("Users", user["ID"], {"Email": updates["Email"]})
    except SheetError as e:
        _handle_sheet_error(e)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return {"message": "Employee updated"}


# ---------- Task review ----------

@router.get("/tasks")
def list_all_tasks():
    try:
        rows = all_rows("Tasks")
    except SheetError as e:
        _handle_sheet_error(e)
    names = _employee_name_map()
    for r in rows:
        r.pop("_row_number", None)
        r["EmployeeName"] = names.get(r.get("EmployeeID"), "")
    return rows


@router.patch("/tasks/{task_id}/review")
def review_task(task_id: str, body: TaskReview):
    try:
        task = find_by_id("Tasks", task_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        update_row("Tasks", task_id, {
            "AdminStatus": body.admin_status,
            "AdminRemarks": body.admin_remarks,
            "UpdatedAt": to_iso(now()),
        })
    except SheetError as e:
        _handle_sheet_error(e)

    _notify(
        task.get("EmployeeID", ""),
        "task",
        f"Your task '{task.get('ProjectName', '')}' for {task.get('ClientName', '')} was marked {body.admin_status}.",
        task_id,
    )
    return {"message": "Task reviewed"}


# ---------- Leave review ----------

@router.get("/leaves")
def list_all_leaves():
    try:
        rows = all_rows("LeaveRequests")
    except SheetError as e:
        _handle_sheet_error(e)
    names = _employee_name_map()
    for r in rows:
        r.pop("_row_number", None)
        r["EmployeeName"] = names.get(r.get("EmployeeID"), "")
    return rows


@router.patch("/leaves/{leave_id}/review")
def review_leave(leave_id: str, body: LeaveReview, current_user: dict = Depends(require_admin)):
    try:
        leave = find_by_id("LeaveRequests", leave_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if leave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    try:
        update_row("LeaveRequests", leave_id, {
            "Status": body.status,
            "AdminRemarks": body.admin_remarks,
            "ReviewedBy": current_user["email"],
            "UpdatedAt": to_iso(now()),
        })
    except SheetError as e:
        _handle_sheet_error(e)

    _notify(
        leave.get("EmployeeID", ""),
        "leave",
        f"Your {leave.get('LeaveType', 'leave')} request ({leave.get('FromDate', '')} to {leave.get('ToDate', '')}) was {body.status.lower()}.",
        leave_id,
    )
    return {"message": "Leave request reviewed"}


# ---------- Password reset (admin-assisted) ----------
# There's no email service wired up, so a locked-out employee can't get a self-service
# "forgot password" link — an admin sets a new temporary password here instead and shares
# it with the employee directly (same as at account creation).

@router.post("/employees/{employee_id}/reset-password")
def reset_employee_password(employee_id: str, body: AdminPasswordReset):
    try:
        emp = find_by_id("Employees", employee_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    try:
        user = find_one("Users", "EmployeeID", employee_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No login account linked to this employee")

    try:
        update_row("Users", user["ID"], {"PasswordHash": hash_password(body.new_temp_password)})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Password reset. Share the new temporary password with the employee directly."}