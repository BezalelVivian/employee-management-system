import logging
import os

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import create_access_token, get_token_version, verify_password
from models import LoginRequest, TokenResponse
from sheets_client import find_one, SheetError

logger = logging.getLogger("ems.auth")
router = APIRouter(tags=["auth"])


def client_ip(request: Request) -> str:
    """Who is calling, for the login rate limit.

    On Vercel every request reaches the app through Vercel's proxy, so the socket address is
    the same for everybody and the limit would apply to ALL employees together. Vercel sets
    x-forwarded-for / x-vercel-forwarded-for to the real client IP and overwrites any value the
    client sends, so it is safe to trust -- but only when actually running on Vercel (the VERCEL
    env var), otherwise anyone could spoof the header. On Render/local we keep the socket
    address (Render uses uvicorn --proxy-headers, see the README)."""
    if os.environ.get("VERCEL"):
        header = request.headers.get("x-vercel-forwarded-for") or request.headers.get("x-forwarded-for")
        if header:
            return header.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # basic brute-force protection
def login(request: Request, body: LoginRequest):
    try:
        user = find_one("Users", "Email", str(body.email).strip())
    except SheetError as e:
        logger.error("Sheets error during login: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not reach the datastore")

    if user is None or str(user.get("IsActive", "")).strip().upper() not in ("TRUE", "1", "YES"):
        logger.warning("Login failed for %s: %s", body.email,
                       "no Users row with that Email" if user is None else "IsActive is not TRUE")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(body.password, str(user.get("PasswordHash", "")).strip()):
        logger.warning("Login failed for %s: %s", body.email,
                       "PasswordHash cell is empty" if not str(user.get("PasswordHash", "")).strip()
                       else "password does not match hash")
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
        email=user["Email"], role=role, employee_id=employee_id, employee_name=employee_name,
        token_version=get_token_version(user),
    )
    return TokenResponse(access_token=token, role=role, name=employee_name or user["Email"])
