import logging
<<<<<<< HEAD
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from attendance import build_days, approved_leave_days
from auth import require_admin, hash_password, next_token_version
from models import (
    EmployeeCreate, EmployeeAdminUpdate, TaskReview, LeaveReview, AdminPasswordReset, AttendanceEdit, PhotoUpload, HolidayCreate,
)
import photos
from sheets_client import (
    all_rows, all_rows_optional, find_by_id, find_one, find_all,
    append_row, append_row_optional, update_row, next_id, next_id_optional, get_holiday_dates,
    get_headers, get_department_names, SheetError,
)
from utils import today_str, today_date, to_iso, now, is_working_day, parse_date_safe

MAX_ADMIN_ATTENDANCE_DAYS = 31
=======
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin, hash_password
from models import EmployeeCreate, EmployeeAdminUpdate, TaskReview, LeaveReview, AdminPasswordReset
from sheets_client import (
    all_rows, find_by_id, find_one, find_all,
    append_row, append_row_optional, update_row, next_id, next_id_optional, get_holiday_dates, SheetError,
)
from utils import today_str, to_iso, now, is_working_day
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

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


<<<<<<< HEAD
def _dmy(iso) -> str:
    d = parse_date_safe(iso)
    return d.strftime("%d-%m-%Y") if d else str(iso or "")


# ---------- Holidays ----------
# Admin manages company holidays here (stored in the optional "Holidays" tab). Employees see
# them on their dashboard and in the bell for HOLIDAY_NOTICE_DAYS days before the date.

@router.get("/holidays")
def list_holidays():
    rows = [
        {"id": r.get("ID"), "date": str(r.get("Date", "")).strip(), "name": str(r.get("Name", "")).strip()}
        for r in all_rows_optional("Holidays")
    ]
    return sorted((h for h in rows if h["date"]), key=lambda h: h["date"])


@router.post("/holidays", status_code=status.HTTP_201_CREATED)
def add_holiday(body: HolidayCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Holiday name is required")
    iso = body.date.isoformat()
    if any(h["date"] == iso for h in list_holidays()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That date is already a holiday")
    ok = append_row_optional("Holidays", {"ID": next_id_optional("Holidays"), "Date": iso, "Name": name})
    if not ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="The Holidays tab is missing. Run 'python setup_sheets.py' once, then try again.")
    return {"message": "Holiday added"}


@router.delete("/holidays/{holiday_id}")
def remove_holiday(holiday_id: str):
    # Blanking the row is enough: rows without a date are ignored everywhere.
    try:
        found = find_by_id("Holidays", holiday_id)
        if found is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")
        update_row("Holidays", holiday_id, {"Date": "", "Name": ""})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Holiday removed"}


=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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

<<<<<<< HEAD
    def _is_true(v) -> bool:
        return str(v or "").strip().upper() in ("TRUE", "1", "YES")

    total_employees = len(employees)
    active_ids = {e.get("ID") for e in employees if _is_true(e.get("IsActive"))}
    active_employees = len(active_ids)

    today_d = today_date()
    today = today_d.isoformat()

    # Count distinct EMPLOYEES (not rows), and only people who actually checked in.
    present_ids = {
        a.get("EmployeeID") for a in attendance
        if a.get("AttendanceDate") == today and a.get("CheckIn")
    }
    # Full-day leave only: a few-hours "Permission" doesn't take someone out for the day.
    leave_ids = {
        emp_id for emp_id in active_ids
        if today in approved_leave_days(
            [l for l in leaves if l.get("EmployeeID") == emp_id], today_d, today_d
        )
    }
    present_today = len(present_ids & active_ids)
    on_leave_today = len(leave_ids - present_ids)
    pending_leaves = sum(1 for l in leaves if l.get("Status") == "Pending")
    pending_tasks = sum(1 for t in tasks if t.get("AdminStatus") == "Pending")

    # On a weekly off or listed holiday nobody is expected in, so don't report a misleading
    # "absent" count just because check-in rows are naturally empty that day.
    holidays = get_holiday_dates()
    if is_working_day(today_d, holidays):
        estimated_absent = len(active_ids - present_ids - leave_ids)
=======
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
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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


<<<<<<< HEAD
# ---------- Departments ----------

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=200)


def _dept_is_off(r: dict) -> bool:
    return str(r.get("IsActive", "")).strip().upper() in ("FALSE", "0", "NO", "INACTIVE", "N")


@router.get("/departments")
def list_departments(include_inactive: bool = Query(False)):
    """Departments for the dropdowns (active only), or all of them for the manager (include_inactive=true)."""
    try:
        rows = all_rows("Departments")
    except SheetError as e:
        _handle_sheet_error(e)
    out = []
    for r in rows:
        did = str(r.get("ID") or r.get("DepartmentID") or "").strip()
        name = str(r.get("Name") or r.get("DepartmentName") or "").strip()
        if not did and not name:
            continue  # blank row
        off = _dept_is_off(r)
        if off and not include_inactive:
            continue
        out.append({"ID": did or name, "Name": name or did, "Description": r.get("Description", ""), "IsActive": not off})
    return out


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def add_department(body: DepartmentCreate):
    """Add a department from the app -- the ID is generated for you, nothing to type in the sheet."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Department name is required")
    try:
        if any(str(r.get("Name", "")).strip().lower() == name.lower() for r in all_rows("Departments", fresh=True)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That department already exists")
        dept_id = next_id("Departments")
        append_row("Departments", {"ID": dept_id, "Name": name, "Description": body.description.strip(), "IsActive": "TRUE"})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Department added", "ID": dept_id}


@router.patch("/departments/{dept_id}/toggle-active")
def toggle_department(dept_id: str):
    """Switch a department on/off. Off = hidden from the dropdowns; employees already in it keep it."""
    try:
        row = find_by_id("Departments", dept_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        now_off = not _dept_is_off(row)
        update_row("Departments", dept_id, {"IsActive": "FALSE" if now_off else "TRUE"})
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Department updated", "IsActive": not now_off}
=======
# ---------- Departments (read-only) ----------

@router.get("/departments")
def list_departments():
    try:
        return all_rows("Departments")
    except SheetError as e:
        _handle_sheet_error(e)
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6


# ---------- Employees ----------

@router.get("/employees")
def list_employees():
    try:
        rows = all_rows("Employees")
    except SheetError as e:
        _handle_sheet_error(e)
<<<<<<< HEAD
    names = get_department_names()
    for r in rows:
        r.pop("_row_number", None)
        dept_id = str(r.get("DepartmentID", "")).strip()
        r["DepartmentName"] = names.get(dept_id, dept_id)
=======
    for r in rows:
        r.pop("_row_number", None)
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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


<<<<<<< HEAD
# ---------- Employee photos ----------

@router.get("/photos")
def list_photos():
    """{employeeId: photo data URL} for every employee that has one -- a single sheet read."""
    return photos.all_photos()


def _require_employee(employee_id: str) -> None:
    try:
        emp = find_by_id("Employees", employee_id)
    except SheetError as e:
        _handle_sheet_error(e)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")


@router.put("/employees/{employee_id}/photo")
def set_employee_photo(employee_id: str, body: PhotoUpload):
    _require_employee(employee_id)
    try:
        photos.set_photo(employee_id, body.photo)
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Photo updated", "photo": body.photo}


@router.delete("/employees/{employee_id}/photo")
def delete_employee_photo(employee_id: str):
    _require_employee(employee_id)
    try:
        photos.set_photo(employee_id, "")
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Photo removed"}


=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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


<<<<<<< HEAD
# ---------- Attendance ----------

@router.get("/attendance")
def list_attendance(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    employee_id: str | None = Query(None),
):
    """Every active employee's day-by-day attendance for a date range (default: today).
    Ranges are capped at 31 days to keep the sheet reads bounded."""
    today = today_date()
    range_to = min(date_to or today, today)
    range_from = date_from or range_to
    if range_from > range_to:
        range_from = range_to
    if (range_to - range_from).days + 1 > MAX_ADMIN_ATTENDANCE_DAYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Please pick a range of at most {MAX_ADMIN_ATTENDANCE_DAYS} days")
    try:
        employees = all_rows("Employees")
        att_rows = all_rows("Attendance")
        leave_rows = all_rows("LeaveRequests")
        holidays = get_holiday_dates()
    except SheetError as e:
        _handle_sheet_error(e)

    att_by_emp: dict[str, list] = {}
    for r in att_rows:
        att_by_emp.setdefault(r.get("EmployeeID"), []).append(r)
    leave_by_emp: dict[str, list] = {}
    for r in leave_rows:
        leave_by_emp.setdefault(r.get("EmployeeID"), []).append(r)

    result = []
    for emp in employees:
        eid = emp.get("ID")
        if employee_id and eid != employee_id:
            continue
        is_active = str(emp.get("IsActive", "")).strip().upper() in ("TRUE", "1", "YES")
        has_rows_in_range = any(
            range_from.isoformat() <= (r.get("AttendanceDate") or "") <= range_to.isoformat()
            for r in att_by_emp.get(eid, [])
        )
        if not is_active and not has_rows_in_range:
            continue  # don't list ex-employees as "Absent"
        start = range_from
        joined = parse_date_safe(emp.get("JoinedDate"))
        if joined and joined > start:
            start = joined
        if start > range_to:
            continue
        for day in build_days(att_by_emp.get(eid, []), leave_by_emp.get(eid, []), holidays, start, range_to, today=today):
            day.update({"employeeId": eid, "employeeName": emp.get("Name", ""), "employeeCode": emp.get("EmployeeCode", "")})
            result.append(day)

    result.sort(key=lambda r: (r["date"], r["employeeName"].lower()), reverse=False)
    result.sort(key=lambda r: r["date"], reverse=True)
    return result


@router.put("/attendance")
def edit_attendance(body: AttendanceEdit, current_user: dict = Depends(require_admin)):
    """Correct (or create) one employee's attendance for one day -- e.g. they forgot to check
    out, or forgot to check in. Sets both times explicitly."""
    ds = body.attendance_date.isoformat()
    check_in = to_iso(datetime.fromisoformat(f"{ds}T{body.check_in}:00"))
    check_out = ""
    if body.check_out:
        check_out = to_iso(datetime.fromisoformat(f"{ds}T{body.check_out}:00"))
        if check_out <= check_in:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Check-out must be after check-in")

    try:
        emp = find_by_id("Employees", body.employee_id)
        if emp is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        existing = [
            r for r in find_all("Attendance", "EmployeeID", body.employee_id, fresh=True)
            if r.get("AttendanceDate") == ds
        ]
        fields = {"CheckIn": check_in, "CheckOut": check_out, "Status": "Present"}
        # Optional audit column: if the Attendance sheet has an "EditedBy" header, record who edited.
        if "EditedBy" in get_headers("Attendance"):
            fields["EditedBy"] = current_user["email"]

        if existing:
            update_row("Attendance", existing[0]["ID"], fields)
        else:
            append_row("Attendance", {
                "ID": next_id("Attendance"), "EmployeeID": body.employee_id, "AttendanceDate": ds, **fields,
            })
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Attendance updated"}


=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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
<<<<<<< HEAD
        f"Your {leave.get('LeaveType', 'leave')} request ({_dmy(leave.get('FromDate', ''))} to {_dmy(leave.get('ToDate', ''))}) was {body.status.lower()}.",
=======
        f"Your {leave.get('LeaveType', 'leave')} request ({leave.get('FromDate', '')} to {leave.get('ToDate', '')}) was {body.status.lower()}.",
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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
<<<<<<< HEAD
        if user is None and emp.get("Email"):
            # Login row exists but isn't linked by EmployeeID (or the link got lost): find it by email.
            user = find_one("Users", "Email", emp["Email"])
            if user is not None:
                update_row("Users", user["ID"], {"EmployeeID": employee_id})
        if user is None:
            # No login at all (employee was created but the Users row is missing/broken): create it now.
            if not emp.get("Email"):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="This employee has no email, so a login can't be created")
            append_row("Users", {
                "ID": next_id("Users"), "Email": emp["Email"],
                "PasswordHash": hash_password(body.new_temp_password), "Role": "employee",
                "EmployeeID": employee_id, "IsActive": "TRUE", "CreatedAt": to_iso(now()),
            })
            return {"message": "Login account created and password set"}
    except SheetError as e:
        _handle_sheet_error(e)

    updates = {"PasswordHash": hash_password(body.new_temp_password), "IsActive": "TRUE"}
    if "TokenVersion" in user:  # log the employee out of every existing session
        updates["TokenVersion"] = str(next_token_version(user))
    try:
        update_row("Users", user["ID"], updates)
=======
    except SheetError as e:
        _handle_sheet_error(e)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No login account linked to this employee")

    try:
        update_row("Users", user["ID"], {"PasswordHash": hash_password(body.new_temp_password)})
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
    except SheetError as e:
        _handle_sheet_error(e)
    return {"message": "Password reset. Share the new temporary password with the employee directly."}