from datetime import date
from pydantic import BaseModel, EmailStr, Field

class LoginForm(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

class TaskForm(BaseModel):
    client_name: str = Field(min_length=1, max_length=150)
    project_name: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=5000)
    status: str
    priority: str
    remarks: str = Field(default="", max_length=5000)
    task_date: date

class LeaveForm(BaseModel):
    leave_type: str
    from_date: date
    to_date: date
    reason: str = Field(min_length=1, max_length=5000)
