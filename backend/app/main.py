"""Punto de entrada de RallyHub (monolito modular FastAPI + frontend estático del mismo origen)."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.dependencies.auth import SAFE_METHODS
from app.domain.errors import DomainError

STATIC_DIR = Path(__file__).parent / "static"
log = logging.getLogger("rallyhub")

CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
DOC_PATHS = ("/docs", "/openapi.json")  # Swagger UI carga recursos de CDN: sin CSP estricta


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("RallyHub iniciado (entorno=%s)", get_settings().environment)
    yield
    from app.db.session import get_engine

    get_engine().dispose()  # cierre ordenado del pool
    log.info("RallyHub detenido")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    docs = settings.docs_enabled
    app = FastAPI(
        title="RallyHub API",
        version="0.1.0",
        description="Gestión de clubes y academias de tenis de mesa. Autenticación por cookie "
                    "HttpOnly; las escrituras requieren la cabecera X-CSRF-Token.",
        docs_url="/docs" if docs else None, redoc_url=None,
        openapi_url="/openapi.json" if docs else None, lifespan=lifespan,
    )

    @app.middleware("http")
    async def security(request: Request, call_next):
        started = time.perf_counter()
        rid = uuid.uuid4().hex[:12]
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > settings.max_body_bytes:
            return JSONResponse(status_code=413, content={"code": "payload_too_large",
                                                          "detail": "Solicitud demasiado grande."})
        if request.method not in SAFE_METHODS and request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and urlparse(origin).netloc != request.headers.get("host") \
                    and origin.rstrip("/") not in settings.origins:
                return JSONResponse(status_code=403, content={"code": "bad_origin",
                                                              "detail": "Origen no permitido."})
        response = await call_next(request)
        h = response.headers
        h["X-Request-ID"] = rid
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "same-origin"
        h["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not request.url.path.startswith(DOC_PATHS):
            h["Content-Security-Policy"] = CSP
        if request.url.path.startswith("/api/"):
            h["Cache-Control"] = "no-store"
        if settings.cookie_secure:
            h["Strict-Transport-Security"] = "max-age=31536000"
        log.info("%s %s %s %.0fms rid=%s", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - started) * 1000, rid)
        return response

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code,
                            content={"code": exc.code, "detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        # Se omite `input` (podría contener contraseñas) y `ctx`.
        errors = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
                  for e in exc.errors()]
        return JSONResponse(status_code=422, content={"code": "validation_error",
                                                      "detail": "Datos inválidos.",
                                                      "errors": errors})

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content={"code": f"http_{exc.status_code}", "detail": str(exc.detail)},
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("Error no controlado en %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"code": "internal_error",
                                                      "detail": "Error interno del servidor."})

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/registro", include_in_schema=False)
    def register_page():
        return FileResponse(STATIC_DIR / "registro.html", headers={"Cache-Control": "no-cache"})

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(STATIC_DIR / "login.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
