"""ASGI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import APP_ENV, SESSION_SECRET, COOKIE_SECURE, SESSION_MAX_AGE_SECONDS, PROJECT_DIR
from app.core.database import Base, engine, SessionLocal
from app.models import *  # ensure metadata models are registered
from app.core.security import hash_password
from app.services.seed import seed_database
from app.api.auth import router as auth_router
from app.api.public import router as public_router
from app.api.admin import router as admin_router

FRONTEND_DIR = PROJECT_DIR / "frontend"
@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
        # Bootstrap one administrator on a brand-new database only.
        # Change these credentials immediately after first sign-in; they are
        # intentionally documented in README for the project owner.
        if db.query(AdminAccount).count() == 0:
            db.add(AdminAccount(
                username="ahmed_admin",
                password_hash=hash_password("AhmedPortfolio@2026!"),
                active=True,
            ))
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Ahmed Shahid Portfolio API",
    version="1.0.0",
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
    openapi_url=None if APP_ENV == "production" else "/openapi.json",
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="ahmed_portfolio_session",
    max_age=SESSION_MAX_AGE_SECONDS,
    same_site="lax",
    https_only=COOKIE_SECURE,
)


# TrustedHostMiddleware is enabled through configuration for production rather than
# imposing a local-only hostname on users running this on a development machine.
if APP_ENV == "production":
    allowed = [x.strip() for x in __import__("os").getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

app.include_router(auth_router)
app.include_router(public_router)
app.include_router(admin_router)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}

@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-cache"})

@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(FRONTEND_DIR / "admin.html", headers={"Cache-Control": "no-store"})

@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found."})
    return JSONResponse(status_code=404, content={"detail": "Page not found."})
