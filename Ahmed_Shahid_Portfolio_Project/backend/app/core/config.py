"""Environment-based application configuration."""
from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(PROJECT_DIR / 'database' / 'portfolio.db').as_posix()}")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-only-change-this-before-deploy-please")
APP_ENV = os.getenv("APP_ENV", "development").lower()
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(PROJECT_DIR / "database" / "uploads"))).resolve()
N8N_CONTACT_WEBHOOK_URL = os.getenv("N8N_CONTACT_WEBHOOK_URL", "").strip()
N8N_REVIEW_WEBHOOK_URL = os.getenv("N8N_REVIEW_WEBHOOK_URL", "").strip()
N8N_ADMIN_WEBHOOK_URL = os.getenv("N8N_ADMIN_WEBHOOK_URL", "").strip()
N8N_WEBHOOK_TOKEN = os.getenv("N8N_WEBHOOK_TOKEN", "").strip()
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", "28800"))

if APP_ENV == "production":
    if SESSION_SECRET == "dev-only-change-this-before-deploy-please" or len(SESSION_SECRET) < 32 or any(word in SESSION_SECRET.lower() for word in ("replace", "change-me", "change_this", "generate", "placeholder")):
        raise RuntimeError("Set a unique SESSION_SECRET of at least 32 characters in production.")
    if not COOKIE_SECURE:
        raise RuntimeError("Set COOKIE_SECURE=true in production when HTTPS is enabled.")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path(DATABASE_URL.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True) if DATABASE_URL.startswith("sqlite:///") else None
