"""Shared application services."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import SiteSetting, AuditEvent

def get_setting(db: Session, key: str, default=None):
    row = db.get(SiteSetting, key)
    return row.value if row else default

def put_setting(db: Session, key: str, value: dict) -> None:
    row = db.get(SiteSetting, key)
    if row is None:
        db.add(SiteSetting(key=key, value=value))
    else:
        row.value = value
        row.updated_at = datetime.now(timezone.utc)

def audit(db: Session, actor: str, action: str, entity_type: str = "", entity_id: str = "", details: dict | None = None):
    db.add(AuditEvent(actor_username=actor[:80], action=action[:100], entity_type=entity_type[:80], entity_id=str(entity_id)[:80], details=details or {}))
