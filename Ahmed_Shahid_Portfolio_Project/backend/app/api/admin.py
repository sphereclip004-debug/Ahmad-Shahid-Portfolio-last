"""Protected content-management, CV, media, and contact-submission endpoints."""
from __future__ import annotations
import json, re, uuid
from io import BytesIO
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_BYTES
from app.core.database import get_db
from app.core.security import admin_username, require_csrf
from app.models import AdminAccount, PortfolioItem, ContactSubmission, AuditEvent
from app.schemas.api import ContentPayload, SettingsPayload, CVPayload, ContactStatusPayload, ProfileImagePositionPayload
from app.services.common import get_setting, put_setting, audit
from app.integrations.n8n import send_event
from app.repositories.content_repository import list_items, get_item, create_item
from app.repositories.submissions_repository import list_contact_submissions, get_contact_submission

router = APIRouter(prefix="/api/admin", tags=["admin"])
KINDS = {"education", "skills", "services", "projects", "reviews"}
CONTENT_FIELDS = {
    "education": {"title", "institution", "qualification", "dates", "description"},
    "skills": {"title", "category", "level", "description"},
    "services": {"title", "description", "icon", "link"},
    "projects": {"title", "description", "category", "technologies", "link", "image_url"},
    "reviews": {"name", "role", "message", "rating"},
}
SETTING_FIELDS = {
    "portfolio_name": 100, "cv_name": 100, "browser_title": 180,
    "meta_description": 300, "tagline": 240, "intro": 300, "hero_description": 600,
    "about_text": 3000, "footer_text": 250, "contact_email": 254,
    "whatsapp_number": 60, "location": 160,
}
CV_FIELDS = {
    "headline": 140, "summary": 3000, "email": 254, "phone": 60,
    "location": 160, "work_experience": 8000, "certifications": 4000,
    "achievements": 4000, "additional_information": 4000,
}


def _check_upload_size(request: Request) -> None:
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > MAX_UPLOAD_BYTES + 256 * 1024:
                raise HTTPException(status_code=413, detail="Upload exceeds the configured size limit.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content length.")

def _delete_managed_upload(filename: str, pattern: str) -> None:
    """Delete only server-generated managed filenames; ignore all other values."""
    if filename and re.fullmatch(pattern, filename) and filename == Path(filename).name:
        try:
            (UPLOAD_DIR / filename).unlink(missing_ok=True)
        except OSError:
            # A failed cleanup never reverses a successful database update; storage
            # cleanup can be retried by the operator without exposing the file publicly.
            pass

def _delete_project_image_url(value: str) -> None:
    match = re.fullmatch(r"/api/public/media/(project-[a-f0-9]{32}\.webp)", value or "")
    if match:
        _delete_managed_upload(match.group(1), r"project-[a-f0-9]{32}\.webp")

def _current_admin(request: Request, db: Session) -> str:
    username = admin_username(request)
    user = db.query(AdminAccount).filter(AdminAccount.username == username, AdminAccount.active.is_(True)).first()
    if not user or request.session.get("admin_session_version") != user.session_version:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Authentication required.")
    return username

def _mutating_admin(request: Request, db: Session) -> str:
    username = _current_admin(request, db)
    require_csrf(request)
    return username

def _normalize_data(kind: str, raw: dict[str, Any]) -> dict:
    if not isinstance(raw, dict):
        raise HTTPException(status_code=422, detail="Content must be an object.")
    allowed = CONTENT_FIELDS[kind]
    unknown = set(raw) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown fields: {', '.join(sorted(unknown))}")
    result = {}
    for key, value in raw.items():
        if key == "rating":
            try:
                rating = int(value)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="Review rating must be between 1 and 5.")
            if rating < 1 or rating > 5:
                raise HTTPException(status_code=422, detail="Review rating must be between 1 and 5.")
            result[key] = rating
        else:
            if value is None:
                value = ""
            if not isinstance(value, (str, int, float, bool)):
                raise HTTPException(status_code=422, detail=f"Field {key} must be plain text.")
            text = str(value).strip()
            if len(text) > 10000:
                raise HTTPException(status_code=422, detail=f"Field {key} is too long.")
            if key == "image_url" and text:
                if re.fullmatch(r"/api/public/media/project-[a-f0-9]{32}\.webp", text):
                    pass  # internally uploaded and re-encoded project image
                else:
                    from urllib.parse import urlparse
                    parsed = urlparse(text)
                    if parsed.scheme != "https" or not parsed.netloc:
                        raise HTTPException(status_code=422, detail="Project image URLs must use HTTPS or an uploaded project image path.")
            elif key == "link" and text:
                from urllib.parse import urlparse
                parsed = urlparse(text)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    raise HTTPException(status_code=422, detail=f"Field {key} must be a full http(s) URL.")
            result[key] = text
    if len(json.dumps(result, ensure_ascii=False)) > 24000:
        raise HTTPException(status_code=422, detail="Content is too large.")
    if kind in {"skills", "services", "projects"} and not result.get("title", "").strip():
        raise HTTPException(status_code=422, detail="A title is required.")
    if kind == "education" and not (result.get("institution") or result.get("title")):
        raise HTTPException(status_code=422, detail="An institution name is required.")
    if kind == "reviews" and (not result.get("name") or not result.get("message")):
        raise HTTPException(status_code=422, detail="A reviewer name and message are required.")
    return result

def _item_json(item: PortfolioItem, private: bool = True) -> dict:
    result = {"id": item.id, "kind": item.kind, "data": item.data, "sort_order": item.sort_order, "published": item.published, "moderation_status": item.moderation_status, "created_at": item.created_at.isoformat() if item.created_at else None, "updated_at": item.updated_at.isoformat() if item.updated_at else None}
    if not private:
        result.pop("moderation_status", None)
    return result

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    _current_admin(request, db)
    return {
        "education": db.query(PortfolioItem).filter_by(kind="education").count(),
        "skills": db.query(PortfolioItem).filter_by(kind="skills").count(),
        "services": db.query(PortfolioItem).filter_by(kind="services").count(),
        "projects": db.query(PortfolioItem).filter_by(kind="projects").count(),
        "pending_reviews": db.query(PortfolioItem).filter_by(kind="reviews", moderation_status="pending").count(),
        "unread_messages": db.query(ContactSubmission).filter_by(status="unread").count(),
    }

@router.get("/settings")
def read_settings(request: Request, db: Session = Depends(get_db)):
    _current_admin(request, db)
    return {"settings": get_setting(db, "site_config", {}) or {}}

@router.put("/settings")
async def update_settings(payload: SettingsPayload, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    if set(payload.settings) - set(SETTING_FIELDS):
        raise HTTPException(status_code=422, detail="One or more settings are not editable here.")
    current = get_setting(db, "site_config", {}) or {}
    changed = {}
    for key, max_len in SETTING_FIELDS.items():
        if key not in payload.settings:
            continue
        value = payload.settings[key]
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"Setting {key} must be text.")
        value = value.strip()
        if len(value) > max_len:
            raise HTTPException(status_code=422, detail=f"Setting {key} is too long.")
        if key == "contact_email" and value:
            if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}", value):
                raise HTTPException(status_code=422, detail="Enter a valid contact email address.")
        changed[key] = value
    current.update(changed)
    put_setting(db, "site_config", current)
    audit(db, username, "settings.updated", "site_settings", "site_config", {"fields": sorted(changed.keys())})
    db.commit()
    await send_event("admin.updated", {"action": "settings.updated", "fields": sorted(changed.keys())})
    return {"ok": True, "settings": current}

@router.get("/content/{kind}")
def list_content(kind: str, request: Request, db: Session = Depends(get_db)):
    _current_admin(request, db)
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Unknown content type.")
    items = list_items(db, kind, include_unpublished=True)
    return {"items": [_item_json(x) for x in items]}

@router.post("/content/{kind}")
async def create_content(kind: str, payload: ContentPayload, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Unknown content type.")
    data = _normalize_data(kind, payload.data)
    status = payload.moderation_status
    if kind != "reviews":
        status = "approved"
    row = create_item(db, kind=kind, data=data, sort_order=payload.sort_order, published=payload.published, moderation_status=status)
    audit(db, username, "content.created", kind, row.id, {"published": row.published})
    db.commit()
    db.refresh(row)
    await send_event("admin.updated", {"action": "content.created", "kind": kind, "id": row.id})
    return {"ok": True, "item": _item_json(row)}

@router.put("/content/{kind}/{item_id}")
async def update_content(kind: str, item_id: int, payload: ContentPayload, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Unknown content type.")
    row = get_item(db, kind, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Content item not found.")
    old_image_url = str((row.data or {}).get("image_url") or "") if kind == "projects" else ""
    row.data = _normalize_data(kind, payload.data)
    row.sort_order = payload.sort_order
    row.published = payload.published
    row.moderation_status = payload.moderation_status if kind == "reviews" else "approved"
    audit(db, username, "content.updated", kind, row.id, {"published": row.published, "moderation_status": row.moderation_status})
    db.commit()
    if kind == "projects" and old_image_url != str((row.data or {}).get("image_url") or ""):
        _delete_project_image_url(old_image_url)
    db.refresh(row)
    await send_event("admin.updated", {"action": "content.updated", "kind": kind, "id": row.id})
    return {"ok": True, "item": _item_json(row)}

@router.delete("/content/{kind}/{item_id}")
async def delete_content(kind: str, item_id: int, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Unknown content type.")
    row = get_item(db, kind, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Content item not found.")
    old_image_url = str((row.data or {}).get("image_url") or "") if kind == "projects" else ""
    db.delete(row)
    audit(db, username, "content.deleted", kind, item_id, {})
    db.commit()
    if kind == "projects":
        _delete_project_image_url(old_image_url)
    await send_event("admin.updated", {"action": "content.deleted", "kind": kind, "id": item_id})
    return {"ok": True}

@router.post("/project-image")
async def upload_project_image(request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    _check_upload_size(request)
    form = await request.form()
    upload = form.get("file")
    if not (upload is not None and hasattr(upload, "read")):
        raise HTTPException(status_code=400, detail="Choose an image file.")
    try:
        raw = await upload.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await upload.close()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Project image exceeds the 5 MB upload limit.")
    try:
        image = Image.open(BytesIO(raw))
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WebP image.")
        image.verify()
        image = Image.open(BytesIO(raw)).convert("RGB")
        if image.width < 64 or image.height < 64 or image.width > 6000 or image.height > 6000:
            raise HTTPException(status_code=422, detail="Image dimensions must be between 64 and 6000 pixels.")
        image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        filename = f"project-{uuid.uuid4().hex}.webp"
        image.save(UPLOAD_DIR / filename, "WEBP", quality=88, method=6)
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image.")
    except OSError:
        raise HTTPException(status_code=415, detail="The uploaded file could not be processed as an image.")
    audit(db, username, "project_image.uploaded", "project_asset", filename, {"format": "webp", "bytes": len(raw)})
    db.commit()
    return {"ok": True, "url": f"/api/public/media/{filename}"}

@router.put("/profile-image/position")
def update_profile_position(payload: ProfileImagePositionPayload, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    settings = get_setting(db, "site_config", {}) or {}
    settings["profile_image_x"] = payload.x
    settings["profile_image_y"] = payload.y
    put_setting(db, "site_config", settings)
    audit(db, username, "profile_image.position_updated", "site_settings", "profile_image_position", {"x": payload.x, "y": payload.y})
    db.commit()
    return {"ok": True, "x": payload.x, "y": payload.y}

@router.get("/cv")
def read_cv(request: Request, db: Session = Depends(get_db)):
    _current_admin(request, db)
    settings = get_setting(db, "site_config", {}) or {}
    content = get_setting(db, "cv_content", {}) or {}
    return {"content": content, "uploaded": bool(settings.get("cv_uploaded_file"))}

@router.put("/cv")
def update_cv(payload: CVPayload, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    unknown = set(payload.content) - set(CV_FIELDS)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown CV fields: {', '.join(sorted(unknown))}")
    current = get_setting(db, "cv_content", {}) or {}
    site = get_setting(db, "site_config", {}) or {}
    previous_cv = str(site.get("cv_uploaded_file") or "")
    for key, max_len in CV_FIELDS.items():
        if key not in payload.content:
            continue
        value = payload.content[key]
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"CV field {key} must be text.")
        value = value.strip()
        if len(value) > max_len:
            raise HTTPException(status_code=422, detail=f"CV field {key} is too long.")
        if key == "email" and value and not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}", value):
            raise HTTPException(status_code=422, detail="Enter a valid CV email address.")
        current[key] = value
    put_setting(db, "cv_content", current)
    site["cv_uploaded_file"] = ""
    put_setting(db, "site_config", site)
    audit(db, username, "cv.updated", "cv_content", "cv_content", {"fields": sorted(payload.content.keys())})
    db.commit()
    _delete_managed_upload(previous_cv, r"cv-[a-f0-9]{32}\.pdf")
    return {"ok": True, "content": current, "uploaded": False}

@router.post("/profile-image")
async def upload_profile_image(request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    _check_upload_size(request)
    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile) and not (upload is not None and hasattr(upload, "read")):
        raise HTTPException(status_code=400, detail="Choose an image file.")
    try:
        raw = await upload.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await upload.close()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB upload limit.")
    try:
        image = Image.open(BytesIO(raw))
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WebP image.")
        image.verify()
        image = Image.open(BytesIO(raw)).convert("RGB")
        if image.width < 64 or image.height < 64 or image.width > 6000 or image.height > 6000:
            raise HTTPException(status_code=422, detail="Image dimensions must be between 64 and 6000 pixels.")
        image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        filename = f"profile-{uuid.uuid4().hex}.webp"
        image.save(UPLOAD_DIR / filename, "WEBP", quality=88, method=6)
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image.")
    except OSError:
        raise HTTPException(status_code=415, detail="The uploaded file could not be processed as an image.")
    settings = get_setting(db, "site_config", {}) or {}
    previous_image = str(settings.get("profile_image_file") or "")
    settings["profile_image_file"] = filename
    put_setting(db, "site_config", settings)
    audit(db, username, "profile_image.updated", "site_settings", "profile_image_file", {"format": "webp", "bytes": len(raw)})
    db.commit()
    _delete_managed_upload(previous_image, r"profile-[a-f0-9]{32}\.webp")
    return {"ok": True, "url": "/api/public/profile-image"}

@router.post("/profile-image/reset")
def reset_profile_image(request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    settings = get_setting(db, "site_config", {}) or {}
    previous_image = str(settings.get("profile_image_file") or "")
    settings["profile_image_file"] = ""
    settings["profile_image_x"] = 50
    settings["profile_image_y"] = 27
    put_setting(db, "site_config", settings)
    audit(db, username, "profile_image.reset", "site_settings", "profile_image_file", {})
    db.commit()
    _delete_managed_upload(previous_image, r"profile-[a-f0-9]{32}\.webp")
    return {"ok": True}

@router.post("/cv-upload")
async def upload_cv_pdf(request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    _check_upload_size(request)
    form = await request.form()
    upload = form.get("file")
    if not (upload is not None and hasattr(upload, "read")):
        raise HTTPException(status_code=400, detail="Choose a PDF file.")
    try:
        raw = await upload.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await upload.close()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CV PDF exceeds the 5 MB upload limit.")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file must be a PDF.")
    filename = f"cv-{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / filename).write_bytes(raw)
    settings = get_setting(db, "site_config", {}) or {}
    previous_cv = str(settings.get("cv_uploaded_file") or "")
    settings["cv_uploaded_file"] = filename
    put_setting(db, "site_config", settings)
    audit(db, username, "cv.uploaded", "site_settings", "cv_uploaded_file", {"bytes": len(raw)})
    db.commit()
    _delete_managed_upload(previous_cv, r"cv-[a-f0-9]{32}\.pdf")
    return {"ok": True, "uploaded": True}

@router.post("/cv/reset")
def reset_cv_upload(request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    settings = get_setting(db, "site_config", {}) or {}
    previous_cv = str(settings.get("cv_uploaded_file") or "")
    settings["cv_uploaded_file"] = ""
    put_setting(db, "site_config", settings)
    audit(db, username, "cv.reset_to_generated", "site_settings", "cv_uploaded_file", {})
    db.commit()
    _delete_managed_upload(previous_cv, r"cv-[a-f0-9]{32}\.pdf")
    return {"ok": True, "uploaded": False}

@router.get("/contacts")
def list_contacts(request: Request, db: Session = Depends(get_db)):
    _current_admin(request, db)
    rows = list_contact_submissions(db, limit=500)
    return {"items": [{"id": x.id, "name": x.name, "email": x.email, "subject": x.subject, "message": x.message, "status": x.status, "created_at": x.created_at.isoformat() if x.created_at else None} for x in rows]}

@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, payload: ContactStatusPayload, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    row = get_contact_submission(db, contact_id)
    if not row:
        raise HTTPException(status_code=404, detail="Message not found.")
    row.status = payload.status
    audit(db, username, "contact.status_updated", "contact_submission", row.id, {"status": row.status})
    db.commit()
    return {"ok": True}

@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, request: Request, db: Session = Depends(get_db)):
    username = _mutating_admin(request, db)
    row = get_contact_submission(db, contact_id)
    if not row:
        raise HTTPException(status_code=404, detail="Message not found.")
    db.delete(row)
    audit(db, username, "contact.deleted", "contact_submission", contact_id, {})
    db.commit()
    return {"ok": True}

@router.get("/audit")
def list_audit(request: Request, db: Session = Depends(get_db)):
    _current_admin(request, db)
    rows = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(150).all()
    return {"items": [{"id": x.id, "actor": x.actor_username, "action": x.action, "entity_type": x.entity_type, "entity_id": x.entity_id, "details": x.details, "created_at": x.created_at.isoformat() if x.created_at else None} for x in rows]}
