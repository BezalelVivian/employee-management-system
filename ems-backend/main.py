import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import CORS_ORIGINS, CORS_ORIGIN_REGEX
from routers import auth as auth_router
from routers import employee as employee_router
from routers import admin as admin_router
from routers.auth import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ems")

app = FastAPI(title="EMS API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if not CORS_ORIGINS and not CORS_ORIGIN_REGEX:
    logger.warning("CORS_ORIGINS is not set: allowing every origin. Set it to your frontend URL in production.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ([] if CORS_ORIGIN_REGEX else ["*"]),
    allow_origin_regex=CORS_ORIGIN_REGEX,
    # Login is a Bearer token in the Authorization header, not a cookie, so credentialed CORS is not
    # needed -- and "*" combined with credentials is exactly what browsers distrust.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Consistent error shape across the API. The frontend shows `message` verbatim to people, so make it
    # a readable sentence ("Phone: Phone number must be exactly 10 digits") not a Python list dump.
    parts = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path")]
        field = (loc[-1] if loc else "").replace("_", " ").capitalize()
        msg = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
        parts.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": True, "code": "VALIDATION_ERROR", "message": "; ".join(parts) or "Invalid request"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": True, "code": "INTERNAL_ERROR", "message": "Something went wrong"},
    )


@app.get("/")
def root():
    # So opening the bare API URL in a browser shows something useful instead of a 404.
    return {"service": "EMS API", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router.router, prefix="/api/auth")
app.include_router(employee_router.router)
app.include_router(admin_router.router)
