from datetime import date, datetime, time
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from .models import User, Employee, Department, Attendance, Task, LeaveRequest, EditRequest
from .auth import hash_password

LATE_CUTOFF = time(9, 30)

def get_user(db: Session, user_id: int):
    return db.get(User, user_id)

def get_employee_for_user(db: Session, user_id: int):
    user = get_user(db, user_id)
    return user.employee if user else None

def attendance_for(db, employee_id, day=None):
    day = day or date.today()
    return db.scalar(select(Attendance).where(Attendance.employee_id == employee_id, Attendance.attendance_date == day))

def mark_check_in(db, employee_id):
    now = datetime.now()
    rec = attendance_for(db, employee_id, now.date())
    if rec:
        if rec.check_out:
            return False, "You have already checked out today."
        return False, "You have already checked in today."
    status = "Late" if now.time() > LATE_CUTOFF else "Present"
    db.add(Attendance(employee_id=employee_id, attendance_date=now.date(), check_in=now.time().replace(microsecond=0), status=status))
    db.commit()
    return True, "Checked in successfully."

def mark_check_out(db, employee_id):
    now = datetime.now()
    rec = attendance_for(db, employee_id, now.date())
    if not rec or not rec.check_in:
        return False, "You have not checked in today."
    if rec.check_out:
        return False, "You have already checked out today."
    rec.check_out = now.time().replace(microsecond=0)
    db.commit()
    return True, "Checked out successfully."

def ensure_seed(db, admin_email, admin_password):
    if not db.scalar(select(User).where(User.email == admin_email)):
        admin = User(email=admin_email, password_hash=hash_password(admin_password), role="admin")
        db.add(admin)
        db.commit()
    if not db.scalar(select(Department).limit(1)):
        db.add_all([Department(name="Engineering"), Department(name="Human Resources"), Department(name="Finance"), Department(name="Operations")])
        db.commit()

def dashboard_stats(db, employee):
    today = date.today()
    attendance = attendance_for(db, employee.id, today)
    tasks = db.scalars(select(Task).where(Task.employee_id == employee.id).order_by(Task.created_at.desc()).limit(5)).all()
    leaves = db.scalars(select(LeaveRequest).where(LeaveRequest.employee_id == employee.id).order_by(LeaveRequest.created_at.desc()).limit(5)).all()
    activities = []
    if attendance:
        if attendance.check_in:
            activities.append(("Checked in", attendance.check_in.strftime("%I:%M %p")))
        if attendance.check_out:
            activities.append(("Checked out", attendance.check_out.strftime("%I:%M %p")))
    for t in tasks:
        activities.append((f"Task submitted: {t.project_name}", t.created_at.strftime("%d %b %Y")))
    for l in leaves:
        activities.append((f"Leave request: {l.leave_type}", l.created_at.strftime("%d %b %Y")))
    return attendance, activities[:8]
