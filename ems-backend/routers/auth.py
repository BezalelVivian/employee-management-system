import logging

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import create_access_token, verify_password
from models import LoginRequest, TokenResponse
from sheets_client import find_one, SheetError

logger = logging.getLogger("ems.auth")
router = APIRouter(tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # basic brute-force protection
def login(request: Request, body: LoginRequest):
    try:
        user = find_one("Users", "Email", body.email)
    except SheetError as e:
        logger.error("Sheets error during login: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not reach the datastore")

    if user is None or str(user.get("IsActive", "")).strip().upper() not in ("TRUE", "1", "YES"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(body.password, user.get("PasswordHash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    role = user.get("Role", "")
    employee_id = user.get("EmployeeID", "") or ""
    employee_name = ""

    if role == "employee" and employee_id:
        try:
            emp = find_one("Employees", "ID", employee_id)
        except SheetError as e:
            logger.error("Sheets error loading employee on login: %s", e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not reach the datastore")
        if emp:
            employee_name = emp.get("Name", "")

    token = create_access_token(
        email=user["Email"], role=role, employee_id=employee_id, employee_name=employee_name
    )
    return TokenResponse(access_token=token, role=role, name=employee_name or user["Email"])
