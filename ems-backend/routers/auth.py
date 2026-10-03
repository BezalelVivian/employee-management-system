import logging

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

<<<<<<< HEAD
from auth import create_access_token, get_token_version, verify_password
=======
from auth import create_access_token, verify_password
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
from models import LoginRequest, TokenResponse
from sheets_client import find_one, SheetError

logger = logging.getLogger("ems.auth")
router = APIRouter(tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # basic brute-force protection
def login(request: Request, body: LoginRequest):
    try:
<<<<<<< HEAD
        user = find_one("Users", "Email", str(body.email).strip())
=======
        user = find_one("Users", "Email", body.email)
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
    except SheetError as e:
        logger.error("Sheets error during login: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not reach the datastore")

    if user is None or str(user.get("IsActive", "")).strip().upper() not in ("TRUE", "1", "YES"):
<<<<<<< HEAD
        logger.warning("Login failed for %s: %s", body.email,
                       "no Users row with that Email" if user is None else "IsActive is not TRUE")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(body.password, str(user.get("PasswordHash", "")).strip()):
        logger.warning("Login failed for %s: %s", body.email,
                       "PasswordHash cell is empty" if not str(user.get("PasswordHash", "")).strip()
                       else "password does not match hash")
=======
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(body.password, user.get("PasswordHash", "")):
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
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
<<<<<<< HEAD
        email=user["Email"], role=role, employee_id=employee_id, employee_name=employee_name,
        token_version=get_token_version(user),
=======
        email=user["Email"], role=role, employee_id=employee_id, employee_name=employee_name
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
    )
    return TokenResponse(access_token=token, role=role, name=employee_name or user["Email"])
