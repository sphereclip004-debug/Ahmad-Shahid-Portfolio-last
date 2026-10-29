"""Administrator authentication endpoints."""
from __future__ import annotations
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import login_is_limited, record_login_failure, clear_login_failures, verify_password, require_csrf, dummy_password_hash
from app.models import AdminAccount, AuditEvent
from app.schemas.api import LoginPayload

router = APIRouter(prefix="/api/admin", tags=["admin-auth"])

@router.post("/login")
def login(payload: LoginPayload, request: Request, db: Session = Depends(get_db)):
    if login_is_limited(request, payload.username):
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again later.")
    origin = request.headers.get("origin")
    if origin:
        from urllib.parse import urlsplit
        parsed_origin = urlsplit(origin)
        if not parsed_origin.netloc or parsed_origin.netloc.lower() != request.url.netloc.lower():
            raise HTTPException(status_code=403, detail="Sign-in request could not be verified.")
    user = db.query(AdminAccount).filter(AdminAccount.username == payload.username.strip()).first()
    # Verify against a dummy hash for unknown users to reduce username timing leaks.
    password_valid = verify_password(user.password_hash if user else dummy_password_hash(), payload.password)
    if not user or not user.active or not password_valid:
        record_login_failure(request, payload.username)
        raise HTTPException(status_code=401, detail="Unable to sign in with those credentials.")
    clear_login_failures(request, payload.username)
    request.session.clear()
    csrf = secrets.token_urlsafe(32)
    request.session["admin_username"] = user.username
    request.session["admin_session_version"] = user.session_version
    request.session["csrf_token"] = csrf
    user.last_login_at = datetime.now(timezone.utc)
    db.add(AuditEvent(actor_username=user.username, action="admin.login", entity_type="admin", entity_id=str(user.id), details={}))
    db.commit()
    return {"ok": True, "username": user.username, "csrf_token": csrf}

@router.get("/session")
def session_info(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("admin_username")
    if not username:
        raise HTTPException(status_code=401, detail="Not signed in.")
    user = db.query(AdminAccount).filter(AdminAccount.username == username, AdminAccount.active.is_(True)).first()
    if not user or request.session.get("admin_session_version") != user.session_version:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not signed in.")
    if not request.session.get("csrf_token"):
        request.session["csrf_token"] = secrets.token_urlsafe(32)
    return {"ok": True, "username": user.username, "csrf_token": request.session["csrf_token"]}

@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("admin_username")
    require_csrf(request)
    request.session.clear()
    if username:
        db.add(AuditEvent(actor_username=str(username), action="admin.logout", entity_type="admin", entity_id="", details={}))
        db.commit()
    return {"ok": True}
