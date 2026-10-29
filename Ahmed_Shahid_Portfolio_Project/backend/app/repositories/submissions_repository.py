"""Database access helpers for private contact submissions."""
from sqlalchemy.orm import Session
from app.models import ContactSubmission


def list_contact_submissions(db: Session, limit: int = 500) -> list[ContactSubmission]:
    return db.query(ContactSubmission).order_by(ContactSubmission.created_at.desc()).limit(max(1, min(limit, 1000))).all()


def get_contact_submission(db: Session, submission_id: int) -> ContactSubmission | None:
    return db.query(ContactSubmission).filter_by(id=submission_id).first()
