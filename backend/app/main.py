import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import engine
from app.core.security import csrf_token_for

logger = logging.getLogger("securepay")
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_production()
    with engine.connect() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("alembic_version") or not inspector.has_table("users"):
            raise RuntimeError("Database schema is missing. Apply Alembic migrations with `alembic upgrade head`.")
        version = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one_or_none()
        if version is None:
            raise RuntimeError("Database has no applied Alembic revision. Run `alembic upgrade head`.")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="SecurePay account API. Payment services remain unavailable until a provider is connected.",
    docs_url=None if settings.environment.lower() == "production" else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.environment.lower() == "production" else "/api/openapi.json",
    debug=settings.debug,
    lifespan=lifespan,
)
app.state.csrf_token = csrf_token_for
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
    max_age=600,
)


@app.middleware("http")
async def security_headers_and_limits(request: Request, call_next):
    request_id = secrets.token_hex(16)
    request.state.correlation_id = request_id
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 64 * 1024:
        response = JSONResponse(status_code=413, content={"detail": "Request body is too large."})
        response.headers["X-Request-ID"] = request_id
        return response
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith(("/api/docs", "/api/redoc", "/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, _exc: Exception):
    logger.error("Unhandled request failure", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "The request could not be completed."})


app.include_router(router)
