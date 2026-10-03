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


def get_token_version(user: dict) -> int:
    """Read the Users sheet's TokenVersion column as an int, treating a blank,
    missing, or garbage value as 0. This makes the column optional/backward
    compatible: rows created before it existed (or a spreadsheet that never
    added it) just behave as version 0 forever, so nothing breaks — the
    invalidation feature below simply won't do anything for those rows until
    the column is added and starts getting bumped."""
    raw = str(user.get("TokenVersion", "")).strip()
    return int(raw) if raw.isdigit() else 0


<<<<<<< HEAD
def next_token_version(user: dict) -> int:
    """The TokenVersion to store on a password change/reset. Only bumps if the Users sheet
    actually HAS a TokenVersion column -- without one, the bump can't be saved, and a token
    stamped with a version the sheet never holds would lock the user out."""
    current = get_token_version(user)
    return current + 1 if "TokenVersion" in user else current


=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
def create_access_token(
    *, email: str, role: str, employee_id: str, employee_name: str, token_version: int = 0
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "tv": token_version,
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
        # Sheets itself is unreachable — don't brick the whole app over a
        # transient blip elsewhere. Skip the liveness check for this request
        # and let the route's own Sheets calls surface the real error if it's
        # still down.
        return {
            "email": payload["sub"],
            "role": payload["role"],
            "employee_id": payload.get("employee_id") or "",
            "employee_name": payload.get("employee_name") or "",
        }

    # This is different from the case above: the sheet WAS reachable and the
    # row is genuinely gone (or explicitly deactivated). Either way, a token
    # for an account that no longer exists must not keep working for up to
    # JWT_EXPIRE_MINUTES just because deleting the row (instead of setting
    # IsActive=FALSE) is a less common way to remove someone.
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account no longer exists",
        )
    if str(user.get("IsActive", "")).strip().upper() not in ("TRUE", "1", "YES"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated",
        )

    # A JWT proves who logged in and when, but says nothing about whether the
    # password used to get it is still the current one. Without this check, a
    # stolen token — or a token from a device someone meant to sign out of —
    # would keep working for up to JWT_EXPIRE_MINUTES even after a password
    # change or an admin-triggered reset, which is exactly the moment you
    # most want old sessions to die. `tv` is stamped into the token at login;
    # changing/resetting a password bumps TokenVersion in the sheet, so any
    # token minted before that no longer matches and is rejected here.
    if get_token_version(user) != payload.get("tv", 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your password was changed — please log in again",
        )

<<<<<<< HEAD
    # Role and employee link come from the sheet, not the token: if an admin is demoted (or an
    # account re-linked), it takes effect on the very next request instead of up to 30 days later.
    return {
        "email": payload["sub"],
        "role": str(user.get("Role", "")).strip() or payload["role"],
        "employee_id": str(user.get("EmployeeID", "")).strip() or payload.get("employee_id") or "",
=======
    return {
        "email": payload["sub"],
        "role": payload["role"],
        "employee_id": payload.get("employee_id") or "",
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
        "employee_name": payload.get("employee_name") or "",
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user