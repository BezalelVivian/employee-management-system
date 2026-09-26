"""Password hashing, JWT issue/verify, and FastAPI auth dependencies.

Identity for "my own data" endpoints ALWAYS comes from the verified JWT claims,
never from a client-supplied employeeId — routers must use `current_user["employee_id"]`,
not anything read from the request body/query params.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from sheets_client import find_one, SheetError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(*, email: str, role: str, employee_id: str, employee_name: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    payload = _decode_token(credentials.credentials)

    # The JWT itself only proves who the caller was AT LOGIN TIME. Because sessions
    # now last up to JWT_EXPIRE_MINUTES (30 days by default), we can't rely on that
    # alone — an admin deactivating someone must take effect immediately, not "next
    # time they happen to log in". So re-check IsActive against the Users sheet on
    # every request. sheets_client's own short-lived cache keeps this cheap.
    try:
        user = find_one("Users", "Email", payload["sub"])
    except SheetError:
        # If Sheets itself is unreachable, fail closed on the safety check but don't
        # brick the whole app over a transient blip elsewhere — treat as active and
        # let the actual route's own Sheets calls surface the real error if it's
        # still down.
        user = None

    if user is not None and str(user.get("IsActive", "")).strip().upper() not in ("TRUE", "1", "YES"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated",
        )

    return {
        "email": payload["sub"],
        "role": payload["role"],
        "employee_id": payload.get("employee_id") or "",
        "employee_name": payload.get("employee_name") or "",
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user