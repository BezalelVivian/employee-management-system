import json
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from time import monotonic

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine, get_db, SessionLocal
from .models import User, Employee, Department, Attendance, Task, LeaveRequest, EditRequest
from .auth import (
    verify_password,
    login_user,
    logout_user,
    current_user_id,
    require_login,
    require_admin,
    csrf_token,
    validate_csrf,
)
from .crud import (
    ensure_seed,
    get_employee_for_user,
    mark_check_in,
    mark_check_out,
    attendance_for,
    dashboard_stats,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

ENV = os.getenv("APP_ENV", "development").lower()
IS_PROD = ENV == "production"

SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@company.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if IS_PROD:
    missing = [
        name
        for name, value in (
            ("SECRET_KEY", SECRET_KEY),
            ("ADMIN_PASSWORD", ADMIN_PASSWORD),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing required environment variables in production: "
            + ", ".join(missing)
        )
    if len(SECRET_KEY) < 32:
        raise RuntimeError(
            "SECRET_KEY must be at least 32 characters in production."
        )
else:
    # Development-only fallbacks. Never used when APP_ENV=production.
    SECRET_KEY = SECRET_KEY or "dev-secret-change-me"
    ADMIN_PASSWORD = ADMIN_PASSWORD or "ChangeMe123!"

flash_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="ems-flash")


# ============================================================
# STARTUP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        ensure_seed(db, ADMIN_EMAIL, ADMIN_PASSWORD)

    yield


app = FastAPI(
    title="EMS - Employment Management System",
    lifespan=lifespan,
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None,
    openapi_url=None if IS_PROD else "/openapi.json",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=IS_PROD,
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def read_flash(request: Request):
    """
    Read the signed, short-lived toast message from ?flash=...
    Forged, tampered or expired tokens are ignored.
    """
    token = request.query_params.get("flash")

    if not token:
        return None

    try:
        data = flash_serializer.loads(token, max_age=120)
    except BadSignature:
        return None

    kind = data.get("k")

    return {
        "msg": str(data.get("m", ""))[:300],
        "kind": kind if kind in ("success", "error") else "success",
    }


def ctx(request: Request, **kwargs):
    """
    Common Jinja template context.
    """
    context = {
        "request": request,
        "csrf": csrf_token(request),
        "flash": read_flash(request),
    }

    context.update(kwargs)

    return context


def render_template(
    template_name: str,
    request: Request,
    **kwargs,
):
    """
    Centralized template rendering.
    """
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=ctx(request, **kwargs),
    )


def redirect_with(path, msg, kind="success"):
    token = flash_serializer.dumps({"m": msg, "k": kind})
    sep = "&" if "?" in path else "?"

    return RedirectResponse(
        f"{path}{sep}flash={token}",
        status_code=303,
    )


def employee_or_redirect(request, db):
    block = require_login(request)

    if block:
        return None, block

    employee = get_employee_for_user(
        db,
        current_user_id(request),
    )

    if not employee:
        return (
            None,
            redirect_with(
                "/dashboard",
                "No employee profile is linked to this account.",
                "error",
            ),
        )

    return employee, None


TASK_STATUSES = {"Pending", "In Progress", "Completed"}
TASK_PRIORITIES = {"Low", "Medium", "High", "Urgent"}


# ============================================================
# ROOT
# ============================================================

@app.get("/", response_class=HTMLResponse)
def root(request: Request):

    if current_user_id(request):
        return RedirectResponse(
            "/dashboard",
            status_code=303,
        )

    return RedirectResponse(
        "/login",
        status_code=303,
    )


# ============================================================
# LOGIN
# ============================================================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    if current_user_id(request):
        return RedirectResponse(
            "/dashboard",
            status_code=303,
        )

    return render_template(
        "login.html",
        request,
        title="Login",
    )


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
_failed_logins: dict[str, tuple[int, float]] = {}


def _login_key(request: Request, email: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}|{email}"


def _is_locked(key: str) -> bool:
    record = _failed_logins.get(key)

    if not record:
        return False

    count, first_seen = record

    if monotonic() - first_seen > LOCKOUT_SECONDS:
        _failed_logins.pop(key, None)
        return False

    return count >= MAX_LOGIN_ATTEMPTS


def _record_failure(key: str) -> None:
    if len(_failed_logins) > 10_000:
        _failed_logins.clear()

    now = monotonic()
    count, first_seen = _failed_logins.get(key, (0, now))

    if now - first_seen > LOCKOUT_SECONDS:
        count, first_seen = 0, now

    _failed_logins[key] = (count + 1, first_seen)


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        validate_csrf(request, csrf)

    except ValueError as e:
        return redirect_with(
            "/login",
            str(e),
            "error",
        )

    email = email.lower().strip()
    key = _login_key(request, email)

    if _is_locked(key):
        return redirect_with(
            "/login",
            "Too many failed attempts. Try again in 15 minutes.",
            "error",
        )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if (
        not user
        or not user.is_active
        or not verify_password(
            password,
            user.password_hash,
        )
    ):
        _record_failure(key)

        return redirect_with(
            "/login",
            "Invalid email or password.",
            "error",
        )

    _failed_logins.pop(key, None)

    login_user(
        request,
        user.id,
        user.role,
    )

    if user.role == "admin":
        return RedirectResponse(
            "/admin",
            status_code=303,
        )

    return RedirectResponse(
        "/dashboard",
        status_code=303,
    )


# ============================================================
# LOGOUT
# ============================================================

@app.post("/logout")
def logout(
    request: Request,
    csrf: str = Form(...),
):

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    logout_user(request)

    return RedirectResponse(
        "/login",
        status_code=303,
    )


# ============================================================
# EMPLOYEE DASHBOARD
# ============================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    attendance, activities = dashboard_stats(
        db,
        employee,
    )

    task_count = (
        db.scalar(
            select(func.count(Task.id))
            .where(Task.employee_id == employee.id)
        )
        or 0
    )

    pending_leaves = (
        db.scalar(
            select(func.count(LeaveRequest.id))
            .where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status == "Pending",
            )
        )
        or 0
    )

    return render_template(
        "dashboard.html",
        request,
        title="Dashboard",
        employee=employee,
        attendance=attendance,
        activities=activities,
        task_count=task_count,
        pending_leaves=pending_leaves,
    )


# ============================================================
# ATTENDANCE CHECK-IN
# ============================================================

@app.post("/attendance/check-in")
def check_in(
    request: Request,
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        validate_csrf(request, csrf)

    except ValueError as e:
        return redirect_with(
            "/dashboard",
            str(e),
            "error",
        )

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    _, msg = mark_check_in(
        db,
        employee.id,
    )

    return redirect_with(
        "/dashboard",
        msg,
        "success" if "successfully" in msg else "error",
    )


# ============================================================
# ATTENDANCE CHECK-OUT
# ============================================================

@app.post("/attendance/check-out")
def check_out(
    request: Request,
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        validate_csrf(request, csrf)

    except ValueError as e:
        return redirect_with(
            "/dashboard",
            str(e),
            "error",
        )

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    _, msg = mark_check_out(
        db,
        employee.id,
    )

    return redirect_with(
        "/dashboard",
        msg,
        "success" if "successfully" in msg else "error",
    )


# ============================================================
# EMPLOYEE PROFILE
# ============================================================

@app.get("/profile", response_class=HTMLResponse)
def profile(
    request: Request,
    db: Session = Depends(get_db),
):

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    pending = db.scalars(
        select(EditRequest)
        .where(
            EditRequest.employee_id == employee.id,
            EditRequest.status == "Pending",
        )
        .order_by(
            desc(EditRequest.created_at)
        )
    ).all()

    return render_template(
        "profile.html",
        request,
        title="My Profile",
        employee=employee,
        pending=pending,
    )


@app.post("/profile/request-edit")
def profile_edit_request(
    request: Request,
    phone: str = Form(""),
    dob: str = Form(""),
    address: str = Form(""),
    reason: str = Form(""),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError as e:
        return redirect_with(
            "/profile",
            str(e),
            "error",
        )

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    dob = dob.strip()

    if dob:
        try:
            date.fromisoformat(dob)
        except ValueError:
            return redirect_with(
                "/profile",
                "Invalid date of birth.",
                "error",
            )

    payload = {
        "phone": phone.strip(),
        "dob": dob or None,
        "address": address.strip(),
    }

    db.add(
        EditRequest(
            employee_id=employee.id,
            target_type="employee",
            target_id=employee.id,
            payload_json=json.dumps(payload),
            reason=reason.strip(),
        )
    )

    db.commit()

    return redirect_with(
        "/profile",
        "Profile edit request sent to admin for approval.",
    )


# ============================================================
# ATTENDANCE HISTORY
# ============================================================

@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(
    request: Request,
    from_date: str = Query(""),
    to_date: str = Query(""),
    status: str = Query(""),
    db: Session = Depends(get_db),
):

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    q = (
        select(Attendance)
        .where(
            Attendance.employee_id == employee.id
        )
        .order_by(
            Attendance.attendance_date.desc()
        )
    )

    if from_date:
        try:
            q = q.where(
                Attendance.attendance_date
                >= date.fromisoformat(from_date)
            )
        except ValueError:
            pass

    if to_date:
        try:
            q = q.where(
                Attendance.attendance_date
                <= date.fromisoformat(to_date)
            )
        except ValueError:
            pass

    if status:
        q = q.where(
            Attendance.status == status
        )

    records = db.scalars(
        q.limit(100)
    ).all()

    return render_template(
        "attendance.html",
        request,
        title="Attendance History",
        employee=employee,
        records=records,
        from_date=from_date,
        to_date=to_date,
        status=status,
    )


# ============================================================
# TASKS
# ============================================================

@app.get("/tasks", response_class=HTMLResponse)
def tasks_page(
    request: Request,
    db: Session = Depends(get_db),
):

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    tasks = db.scalars(
        select(Task)
        .where(
            Task.employee_id == employee.id
        )
        .order_by(
            Task.task_date.desc(),
            Task.created_at.desc(),
        )
        .limit(200)
    ).all()

    counts = {
        "Total": len(tasks),
        "Completed": sum(
            t.status == "Completed"
            for t in tasks
        ),
        "Pending": sum(
            t.status == "Pending"
            for t in tasks
        ),
        "In Progress": sum(
            t.status == "In Progress"
            for t in tasks
        ),
    }

    return render_template(
        "tasks.html",
        request,
        title="Tasks",
        employee=employee,
        tasks=tasks,
        counts=counts,
    )


@app.post("/tasks")
def create_task(
    request: Request,
    client_name: str = Form(...),
    project_name: str = Form(...),
    description: str = Form(...),
    status: str = Form(...),
    priority: str = Form(...),
    remarks: str = Form(""),
    task_date: str = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        validate_csrf(request, csrf)
        day = date.fromisoformat(task_date)

    except (ValueError, TypeError) as e:
        return redirect_with(
            "/tasks",
            str(e) if str(e) else "Invalid task date.",
            "error",
        )

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    if status not in TASK_STATUSES or priority not in TASK_PRIORITIES:
        return redirect_with(
            "/tasks",
            "Invalid task status or priority.",
            "error",
        )

    db.add(
        Task(
            employee_id=employee.id,
            client_name=client_name.strip(),
            project_name=project_name.strip(),
            description=description.strip(),
            status=status,
            priority=priority,
            remarks=remarks.strip(),
            task_date=day,
        )
    )

    db.commit()

    return redirect_with(
        "/tasks",
        "Task submitted successfully.",
    )


@app.post("/tasks/{task_id}/edit")
def task_edit(
    request: Request,
    task_id: int,
    client_name: str = Form(...),
    project_name: str = Form(...),
    description: str = Form(...),
    status: str = Form(...),
    priority: str = Form(...),
    remarks: str = Form(""),
    task_date: str = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        validate_csrf(request, csrf)
        day = date.fromisoformat(task_date)
    except (ValueError, TypeError) as e:
        return redirect_with("/tasks", str(e) or "Invalid date.", "error")

    employee, block = employee_or_redirect(request, db)
    if block:
        return block

    task = db.get(Task, task_id)

    # Employees can only edit their own tasks; owner is never changed here.
    if not task or task.employee_id != employee.id:
        return redirect_with("/tasks", "Task not found.", "error")

    if status not in TASK_STATUSES or priority not in TASK_PRIORITIES:
        return redirect_with("/tasks", "Invalid task status or priority.", "error")

    task.client_name = client_name.strip()
    task.project_name = project_name.strip()
    task.description = description.strip()
    task.status = status
    task.priority = priority
    task.remarks = remarks.strip()
    task.task_date = day
    task.admin_status = "Pending"  # edited work goes back for review

    db.commit()
    return redirect_with("/tasks", "Task updated.")

# ============================================================
# LEAVE
# ============================================================

@app.get("/leave", response_class=HTMLResponse)
def leave_page(
    request: Request,
    search: str = Query(""),
    status: str = Query(""),
    leave_type: str = Query(""),
    from_date: str = Query(""),
    to_date: str = Query(""),
    db: Session = Depends(get_db),
):

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    q = (
        select(LeaveRequest)
        .where(
            LeaveRequest.employee_id == employee.id
        )
        .order_by(
            LeaveRequest.created_at.desc()
        )
    )

    if search:
        q = q.where(
            or_(
                LeaveRequest.reason.ilike(
                    f"%{search}%"
                ),
                LeaveRequest.leave_type.ilike(
                    f"%{search}%"
                ),
            )
        )

    if status:
        q = q.where(
            LeaveRequest.status == status
        )

    if leave_type:
        q = q.where(
            LeaveRequest.leave_type == leave_type
        )

    if from_date:
        try:
            q = q.where(
                LeaveRequest.from_date
                >= date.fromisoformat(from_date)
            )
        except ValueError:
            pass

    if to_date:
        try:
            q = q.where(
                LeaveRequest.to_date
                <= date.fromisoformat(to_date)
            )
        except ValueError:
            pass

    leaves = db.scalars(
        q.limit(200)
    ).all()

    return render_template(
        "leave.html",
        request,
        title="Leave",
        employee=employee,
        leaves=leaves,
        search=search,
        status=status,
        leave_type=leave_type,
        from_date=from_date,
        to_date=to_date,
    )


@app.post("/leave")
def create_leave(
    request: Request,
    leave_type: str = Form(...),
    from_date: str = Form(...),
    to_date: str = Form(...),
    reason: str = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        validate_csrf(request, csrf)

        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)

    except (ValueError, TypeError):
        return redirect_with(
            "/leave",
            "Invalid dates or security token.",
            "error",
        )

    employee, block = employee_or_redirect(
        request,
        db,
    )

    if block:
        return block

    if start > end:
        return redirect_with(
            "/leave",
            "To date cannot be before from date.",
            "error",
        )

    if leave_type not in {
        "Sick Leave",
        "Casual Leave",
        "Emergency Leave",
        "Permission",
    }:
        return redirect_with(
            "/leave",
            "Invalid leave type.",
            "error",
        )

    overlap = db.scalar(
        select(LeaveRequest.id)
        .where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_(
                ["Pending", "Approved"]
            ),
            LeaveRequest.from_date <= end,
            LeaveRequest.to_date >= start,
        )
    )

    if overlap:
        return redirect_with(
            "/leave",
            "An existing pending/approved leave overlaps these dates.",
            "error",
        )

    db.add(
        LeaveRequest(
            employee_id=employee.id,
            leave_type=leave_type,
            from_date=start,
            to_date=end,
            reason=reason.strip(),
        )
    )

    db.commit()

    return redirect_with(
        "/leave",
        "Leave request submitted successfully.",
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    today = date.today()

    total = (
        db.scalar(
            select(func.count(Employee.id))
        )
        or 0
    )

    active = (
        db.scalar(
            select(func.count(Employee.id))
            .where(Employee.is_active == True)
        )
        or 0
    )

    present = (
        db.scalar(
            select(func.count(Attendance.id))
            .where(
                Attendance.attendance_date == today,
                Attendance.status.in_(
                    ["Present", "Late"]
                ),
            )
        )
        or 0
    )

    on_leave = (
        db.scalar(
            select(func.count(LeaveRequest.id))
            .where(
                LeaveRequest.status == "Approved",
                LeaveRequest.from_date <= today,
                LeaveRequest.to_date >= today,
            )
        )
        or 0
    )

    absent = max(
        active - present - on_leave,
        0,
    )

    pending_leaves = (
        db.scalar(
            select(func.count(LeaveRequest.id))
            .where(
                LeaveRequest.status == "Pending"
            )
        )
        or 0
    )

    pending_tasks = (
        db.scalar(
            select(func.count(Task.id))
            .where(
                Task.admin_status == "Pending"
            )
        )
        or 0
    )

    departments = db.scalars(
        select(Department)
        .order_by(Department.name)
    ).all()

    return render_template(
        "admin.html",
        request,
        title="Admin Dashboard",
        total=total,
        active=active,
        present=present,
        absent=absent,
        pending_leaves=pending_leaves,
        pending_tasks=pending_tasks,
        departments=departments,
    )


# ============================================================
# ADMIN EMPLOYEES
# ============================================================

@app.get("/admin/employees", response_class=HTMLResponse)
def admin_employees(
    request: Request,
    search: str = Query(""),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    q = (
        select(Employee)
        .order_by(Employee.name)
    )

    if search:
        q = q.where(
            or_(
                Employee.name.ilike(
                    f"%{search}%"
                ),
                Employee.employee_code.ilike(
                    f"%{search}%"
                ),
                Employee.email.ilike(
                    f"%{search}%"
                ),
            )
        )

    employees = db.scalars(
        q.limit(300)
    ).all()

    departments = db.scalars(
        select(Department)
        .order_by(Department.name)
    ).all()

    return render_template(
        "admin_employees.html",
        request,
        title="Employees",
        employees=employees,
        departments=departments,
        search=search,
    )


@app.post("/admin/employees/create")
def admin_create_employee(
    request: Request,
    employee_code: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(""),
    designation: str = Form(""),
    department_id: str = Form(""),
    role_title: str = Form("Employee"),
    joined_date: str = Form(""),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError as e:
        return redirect_with(
            "/admin/employees",
            str(e),
            "error",
        )

    email = email.lower().strip()

    existing_user = db.scalar(
        select(User)
        .where(User.email == email)
    )

    existing_employee = db.scalar(
        select(Employee)
        .where(
            or_(
                Employee.email == email,
                Employee.employee_code
                == employee_code.strip(),
            )
        )
    )

    if existing_user or existing_employee:
        return redirect_with(
            "/admin/employees",
            "Employee ID or email already exists.",
            "error",
        )

    employee = Employee(
        employee_code=employee_code.strip(),
        name=name.strip(),
        email=email,
        phone=phone.strip(),
        designation=designation.strip(),
        department_id=(
            int(department_id)
            if department_id
            else None
        ),
        role_title=role_title.strip(),
        joined_date=(
            date.fromisoformat(joined_date)
            if joined_date
            else None
        ),
    )

    db.add(employee)
    db.flush()

    from .auth import hash_password

    db.add(
        User(
            email=email,
            password_hash=hash_password(password),
            role="employee",
            employee_id=employee.id,
        )
    )

    db.commit()

    return redirect_with(
        "/admin/employees",
        "Employee created successfully.",
    )


@app.post("/admin/employees/{employee_id}/toggle")
def admin_toggle_employee(
    request: Request,
    employee_id: int,
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError as e:
        return redirect_with(
            "/admin/employees",
            str(e),
            "error",
        )

    employee = db.get(
        Employee,
        employee_id,
    )

    if not employee:
        return redirect_with(
            "/admin/employees",
            "Employee not found.",
            "error",
        )

    employee.is_active = not employee.is_active

    if employee.user:
        employee.user.is_active = employee.is_active

    db.commit()

    return redirect_with(
        "/admin/employees",
        "Employee status updated.",
    )


# ============================================================
# ADMIN ATTENDANCE
# ============================================================

@app.get("/admin/attendance", response_class=HTMLResponse)
def admin_attendance(
    request: Request,
    employee_id: int | None = None,
    status: str = Query(""),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    q = (
        select(Attendance)
        .order_by(
            Attendance.attendance_date.desc()
        )
    )

    if employee_id:
        q = q.where(
            Attendance.employee_id == employee_id
        )

    if status:
        q = q.where(
            Attendance.status == status
        )

    records = db.scalars(
        q.limit(500)
    ).all()

    employees = db.scalars(
        select(Employee)
        .order_by(Employee.name)
    ).all()

    return render_template(
        "admin_attendance.html",
        request,
        title="Admin Attendance",
        records=records,
        employees=employees,
        employee_id=employee_id,
        status=status,
    )


# ============================================================
# ADMIN TASKS
# ============================================================

@app.get("/admin/tasks", response_class=HTMLResponse)
def admin_tasks(
    request: Request,
    status: str = Query(""),
    employee_id: int | None = None,
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    q = (
        select(Task)
        .order_by(
            Task.task_date.desc(),
            Task.created_at.desc(),
        )
    )

    if status:
        q = q.where(
            Task.admin_status == status
        )

    if employee_id:
        q = q.where(
            Task.employee_id == employee_id
        )

    tasks = db.scalars(
        q.limit(500)
    ).all()

    employees = db.scalars(
        select(Employee)
        .order_by(Employee.name)
    ).all()

    return render_template(
        "admin_tasks.html",
        request,
        title="Admin Tasks",
        tasks=tasks,
        employees=employees,
        status=status,
        employee_id=employee_id,
    )


@app.post("/admin/tasks/{task_id}/review")
def admin_review_task(
    request: Request,
    task_id: int,
    admin_status: str = Form(...),
    admin_remarks: str = Form(""),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError as e:
        return redirect_with(
            "/admin/tasks",
            str(e),
            "error",
        )

    if admin_status not in {
        "Pending",
        "Approved",
        "Needs Changes",
        "Rejected",
    }:
        return redirect_with(
            "/admin/tasks",
            "Invalid admin status.",
            "error",
        )

    task = db.get(
        Task,
        task_id,
    )

    if not task:
        return redirect_with(
            "/admin/tasks",
            "Task not found.",
            "error",
        )

    task.admin_status = admin_status
    task.admin_remarks = admin_remarks.strip()

    db.commit()

    return redirect_with(
        "/admin/tasks",
        "Task review updated.",
    )


# ============================================================
# ADMIN LEAVE
# ============================================================

@app.get("/admin/leave", response_class=HTMLResponse)
def admin_leave(
    request: Request,
    status: str = Query(""),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    q = (
        select(LeaveRequest)
        .order_by(
            LeaveRequest.created_at.desc()
        )
    )

    if status:
        q = q.where(
            LeaveRequest.status == status
        )

    leaves = db.scalars(
        q.limit(500)
    ).all()

    return render_template(
        "admin_leave.html",
        request,
        title="Admin Leave",
        leaves=leaves,
        status=status,
    )


@app.post("/admin/leave/{leave_id}/review")
def admin_review_leave(
    request: Request,
    leave_id: int,
    status: str = Form(...),
    admin_remarks: str = Form(""),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError as e:
        return redirect_with(
            "/admin/leave",
            str(e),
            "error",
        )

    if status not in {
        "Pending",
        "Approved",
        "Rejected",
    }:
        return redirect_with(
            "/admin/leave",
            "Invalid leave status.",
            "error",
        )

    leave = db.get(
        LeaveRequest,
        leave_id,
    )

    if not leave:
        return redirect_with(
            "/admin/leave",
            "Leave request not found.",
            "error",
        )

    leave.status = status
    leave.admin_remarks = admin_remarks.strip()
    leave.reviewed_by = current_user_id(request)

    db.commit()

    return redirect_with(
        "/admin/leave",
        "Leave request updated.",
    )


# ============================================================
# ADMIN EDIT REQUESTS
# ============================================================

@app.get("/admin/edit-requests", response_class=HTMLResponse)
def admin_edit_requests(
    request: Request,
    db: Session = Depends(get_db)
):
    block = require_admin(request)

    if block:
        return block

    edit_requests = db.scalars(
        select(EditRequest)
        .order_by(EditRequest.created_at.desc())
        .limit(300)
    ).all()

    request_rows = []

    for edit_request in edit_requests:
        employee = db.get(Employee, edit_request.employee_id)

        target = None

        if edit_request.target_type == "employee":
            target = db.get(Employee, edit_request.target_id)

        elif edit_request.target_type == "task":
            target = db.get(Task, edit_request.target_id)

        try:
            payload = json.loads(edit_request.payload_json)
        except (json.JSONDecodeError, TypeError):
            payload = {}

        request_rows.append({
            "id": edit_request.id,
            "employee": employee,
            "target_type": edit_request.target_type,
            "target": target,
            "payload": payload,
            "status": edit_request.status,
            "reason": edit_request.reason,
            "admin_remarks": edit_request.admin_remarks,
            "created_at": edit_request.created_at,
        })

    return render_template(
        "admin_edits.html",
        request=request,
        title="Edit Requests",
        requests=request_rows
    )


@app.post("/admin/edit-requests/{request_id}/review")
def admin_review_edit(
    request: Request,
    request_id: int,
    status: str = Form(...),
    admin_remarks: str = Form(""),
    csrf: str = Form(...),
    db: Session = Depends(get_db),
):

    block = require_admin(request)

    if block:
        return block

    try:
        validate_csrf(
            request,
            csrf,
        )

    except ValueError as e:
        return redirect_with(
            "/admin/edit-requests",
            str(e),
            "error",
        )

    req = db.get(
        EditRequest,
        request_id,
    )

    if not req or req.status != "Pending":
        return redirect_with(
            "/admin/edit-requests",
            "Request not found or already reviewed.",
            "error",
        )

    if status not in {
        "Approved",
        "Rejected",
    }:
        return redirect_with(
            "/admin/edit-requests",
            "Invalid review status.",
            "error",
        )

    req.status = status
    req.admin_remarks = admin_remarks.strip()
    req.reviewed_by = current_user_id(request)

    if status == "Approved":

        try:
            payload = json.loads(
                req.payload_json
            )
        except (json.JSONDecodeError, TypeError):
            db.rollback()

            return redirect_with(
                "/admin/edit-requests",
                "This request has unreadable data and cannot be approved.",
                "error",
            )

        # --------------------------------------------
        # EMPLOYEE PROFILE EDIT
        # --------------------------------------------

        if req.target_type == "employee":

            obj = db.get(
                Employee,
                req.target_id,
            )

            if obj:

                if payload.get("phone") is not None:
                    obj.phone = payload.get("phone")

                if payload.get("address") is not None:
                    obj.address = payload.get("address")

                if payload.get("dob"):
                    try:
                        obj.dob = date.fromisoformat(
                            payload["dob"]
                        )
                    except (ValueError, TypeError):
                        db.rollback()

                        return redirect_with(
                            "/admin/edit-requests",
                            "This request has an invalid date of birth and cannot be approved.",
                            "error",
                        )

        # --------------------------------------------
        # TASK EDIT
        # --------------------------------------------

        elif req.target_type == "task":

            obj = db.get(
                Task,
                req.target_id,
            )

            if obj:

                for field in [
                    "description",
                    "status",
                    "priority",
                    "remarks",
                ]:

                    if field in payload:
                        setattr(
                            obj,
                            field,
                            payload[field],
                        )

                if (
                    obj.status not in TASK_STATUSES
                    or obj.priority not in TASK_PRIORITIES
                ):
                    db.rollback()

                    return redirect_with(
                        "/admin/edit-requests",
                        "This request has an invalid status or priority and cannot be approved.",
                        "error",
                    )

    db.commit()

    return redirect_with(
        "/admin/edit-requests",
        "Edit request reviewed.",
    )