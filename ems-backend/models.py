"""Pydantic schemas for request bodies and API responses, shared across routers."""
import re
from datetime import date
from datetime import date as _date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------- Auth ----------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


# ---------- Shared validators ----------

PHONE_DIGITS_RE = re.compile(r"^\d{10}$")


def _check_phone(v: Optional[str]) -> Optional[str]:
    """A phone number is exactly 10 digits. Common formatting (spaces, dashes,
    parentheses, a leading +91/91 country code) is stripped before checking, so
    '+91 98765 43210' and '9876543210' both work — but '987654321' (9 digits) or
    '98765432101' (11 digits) are rejected, not silently truncated/padded."""
    if v is None or v == "":
        return v
    cleaned = re.sub(r"[\s\-()]", "", v)
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    if not PHONE_DIGITS_RE.match(cleaned):
        raise ValueError("Phone number must be exactly 10 digits")
    return cleaned


# ---------- Profile ----------

class ProfileUpdate(BaseModel):
    """Only the fields an employee is allowed to change themselves."""
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=300)
    dob: Optional[date] = None

    @field_validator("phone")
    @classmethod
    def phone_is_valid(cls, v: Optional[str]) -> Optional[str]:
        return _check_phone(v)

    @field_validator("dob")
    @classmethod
    def dob_not_in_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v


# ---------- Profile photo ----------

PHOTO_PREFIX = "data:image/jpeg;base64,"
# A Google Sheets cell holds at most 50,000 characters. The browser shrinks photos to a small
# square JPEG well under this; the server enforces it so an oversized value can never be saved.
PHOTO_MAX_CHARS = 42_000


class PhotoUpload(BaseModel):
    photo: str

    @field_validator("photo")
    @classmethod
    def photo_is_small_jpeg(cls, v: str) -> str:
        import base64
        import binascii
        if not v.startswith(PHOTO_PREFIX):
            raise ValueError("Photo must be a JPEG image")
        if len(v) > PHOTO_MAX_CHARS:
            raise ValueError("Photo is too large. Please choose a smaller image")
        try:
            raw = base64.b64decode(v[len(PHOTO_PREFIX):], validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("Photo data is corrupted")
        if not raw.startswith(b"\xff\xd8\xff"):
            raise ValueError("Photo must be a valid JPEG image")
        return v


# ---------- Password ----------

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class AdminPasswordReset(BaseModel):
    new_temp_password: str = Field(..., min_length=6)


# ---------- Attendance ----------

class AttendanceFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[str] = None


_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class AttendanceEdit(BaseModel):
    """Admin correction of one employee's attendance for one day (creates the row if missing).
    Times are 24h 'HH:MM' in the company timezone."""
    employee_id: str = Field(..., min_length=1)
    attendance_date: date
    check_in: str
    check_out: Optional[str] = None

    @field_validator("check_in")
    @classmethod
    def check_in_format(cls, v: str) -> str:
        if not _HHMM_RE.match(v):
            raise ValueError("check_in must be a 24h time like 09:30")
        return v

    @field_validator("check_out")
    @classmethod
    def check_out_format(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        if not _HHMM_RE.match(v):
            raise ValueError("check_out must be a 24h time like 18:00, or empty")
        return v

    @field_validator("attendance_date")
    @classmethod
    def not_future(cls, v: date) -> date:
        from utils import today_date
        if v > today_date():
            raise ValueError("Cannot record attendance for a future date")
        return v


# ---------- Tasks ----------

VALID_TASK_STATUS = {"Pending", "In Progress", "Completed"}
VALID_PRIORITY = {"Low", "Medium", "High", "Urgent"}
VALID_ADMIN_STATUS = {"Pending", "Approved", "Needs Changes", "Rejected"}


class TaskCreate(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200)
    project_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    status: str
    priority: str
    remarks: str = Field("", max_length=1000)
    task_date: date

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in VALID_TASK_STATUS:
            raise ValueError(f"status must be one of {sorted(VALID_TASK_STATUS)}")
        return v

    @field_validator("priority")
    @classmethod
    def check_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITY:
            raise ValueError(f"priority must be one of {sorted(VALID_PRIORITY)}")
        return v


class TaskUpdate(TaskCreate):
    pass


class TaskReview(BaseModel):
    admin_status: str
    admin_remarks: str = Field("", max_length=1000)

    @field_validator("admin_status")
    @classmethod
    def check_admin_status(cls, v: str) -> str:
        if v not in VALID_ADMIN_STATUS:
            raise ValueError(f"admin_status must be one of {sorted(VALID_ADMIN_STATUS)}")
        return v


# ---------- Leave ----------

VALID_LEAVE_TYPE = {"Sick Leave", "Casual Leave", "Emergency Leave", "Permission"}
VALID_LEAVE_STATUS = {"Pending", "Approved", "Rejected"}


class LeaveCreate(BaseModel):
    leave_type: str
    from_date: date
    to_date: date
    reason: str = Field("", max_length=1000)

    @field_validator("leave_type")
    @classmethod
    def check_type(cls, v: str) -> str:
        if v not in VALID_LEAVE_TYPE:
            raise ValueError(f"leave_type must be one of {sorted(VALID_LEAVE_TYPE)}")
        return v

    @field_validator("to_date")
    @classmethod
    def check_date_order(cls, v: date, info) -> date:
        from_date = info.data.get("from_date")
        if from_date is not None and v < from_date:
            raise ValueError("to_date cannot be before from_date")
        return v


class LeaveReview(BaseModel):
    status: str
    admin_remarks: str = Field("", max_length=1000)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in VALID_LEAVE_STATUS:
            raise ValueError(f"status must be one of {sorted(VALID_LEAVE_STATUS)}")
        return v


# ---------- Admin: employees ----------

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field("", max_length=20)
    dob: Optional[date] = None
    designation: str = Field("", max_length=100)
    department_id: str = Field("", max_length=50)
    role_title: str = Field("", max_length=100)
    address: str = Field("", max_length=300)
    joined_date: date
    temp_password: str = Field(..., min_length=6)

    @field_validator("phone")
    @classmethod
    def phone_is_valid(cls, v: str) -> str:
        return _check_phone(v) or ""


class EmployeeAdminUpdate(BaseModel):
    """Official-record fields only an admin can change."""
    employee_code: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    designation: Optional[str] = None
    department_id: Optional[str] = None
    role_title: Optional[str] = None
    joined_date: Optional[date] = None

class HolidayCreate(BaseModel):
    date: _date
    name: str
