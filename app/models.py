from datetime import datetime, date, time

from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    Time,
    Boolean,
    ForeignKey,
    Text,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(20),
        default="employee",
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    employee: Mapped["Employee | None"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="user",
        uselist=False,
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    employees: Mapped[list["Employee"]] = relationship(
        back_populates="department"
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    employee_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120)
    )

    email: Mapped[str] = mapped_column(
        String(190),
        unique=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    dob: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    designation: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )

    role_title: Mapped[str] = mapped_column(
        String(80),
        default="Employee",
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    joined_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    salary: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[User.employee_id],
        back_populates="employee",
        uselist=False,
    )

    department: Mapped["Department | None"] = relationship(
        back_populates="employees"
    )

    attendance: Mapped[list["Attendance"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    leaves: Mapped[list["LeaveRequest"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "attendance_date",
            name="uq_employee_attendance_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
    )

    attendance_date: Mapped[date] = mapped_column(
        Date,
        index=True,
    )

    check_in: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    check_out: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="Present",
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="attendance"
    )

    @property
    def working_hours(self):
        """Return working duration after both check-in and check-out exist."""

        if not (self.check_in and self.check_out):
            return None

        seconds = int(
            (
                datetime.combine(
                    self.attendance_date,
                    self.check_out,
                )
                - datetime.combine(
                    self.attendance_date,
                    self.check_in,
                )
            ).total_seconds()
        )

        seconds = max(seconds, 0)

        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
    )

    client_name: Mapped[str] = mapped_column(
        String(150)
    )

    project_name: Mapped[str] = mapped_column(
        String(150)
    )

    description: Mapped[str] = mapped_column(
        Text
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="Pending",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default="Medium",
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    task_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        index=True,
    )

    admin_status: Mapped[str] = mapped_column(
        String(30),
        default="Pending",
    )

    admin_remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="tasks"
    )


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
    )

    leave_type: Mapped[str] = mapped_column(
        String(30)
    )

    from_date: Mapped[date] = mapped_column(
        Date
    )

    to_date: Mapped[date] = mapped_column(
        Date
    )

    reason: Mapped[str] = mapped_column(
        Text
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="Pending",
        index=True,
    )

    admin_remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="leaves"
    )


class EditRequest(Base):
    __tablename__ = "edit_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
    )

    target_type: Mapped[str] = mapped_column(
        String(30)
    )

    target_id: Mapped[int] = mapped_column(
        Integer
    )

    payload_json: Mapped[str] = mapped_column(
        Text
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="Pending",
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    admin_remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )