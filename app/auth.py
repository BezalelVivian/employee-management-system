import secrets
from functools import wraps
from fastapi import Request
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def validate_csrf(request: Request, token: str | None):
    expected = request.session.get("csrf")
    if not expected or not token or not secrets.compare_digest(expected, token):
        raise ValueError("Invalid security token. Please refresh and try again.")


def login_user(request: Request, user_id: int, role: str):
    request.session.clear()
    request.session["user_id"] = user_id
    request.session["role"] = role
    request.session["csrf"] = secrets.token_urlsafe(32)


def logout_user(request: Request):
    request.session.clear()


def current_user_id(request: Request):
    return request.session.get("user_id")


def require_login(request: Request):
    if not current_user_id(request):
        return RedirectResponse("/login", status_code=303)
    return None


def require_admin(request: Request):
    if not current_user_id(request):
        return RedirectResponse("/login", status_code=303)
    if request.session.get("role") != "admin":
        return RedirectResponse("/dashboard", status_code=303)
    return None
