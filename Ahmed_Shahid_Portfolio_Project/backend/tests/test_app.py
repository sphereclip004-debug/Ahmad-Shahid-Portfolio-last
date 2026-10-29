"""Integration tests for the main security and portfolio flows."""
from __future__ import annotations
import os
from pathlib import Path
from io import BytesIO
from PIL import Image

TEST_ROOT = Path(__file__).resolve().parent
DB_FILE = TEST_ROOT / "test_portfolio.db"
if DB_FILE.exists(): DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"
os.environ["SESSION_SECRET"] = "test-only-session-secret-with-more-than-32-characters"
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["APP_ENV"] = "testing"
os.environ["COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models import AdminAccount, PortfolioItem, ContactSubmission


def setup_admin():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(AdminAccount).filter_by(username="test-admin").first()
        if not existing:
            db.add(AdminAccount(username="test-admin", password_hash=hash_password("a-very-long-test-password-42!"), active=True))
            db.commit()
    finally: db.close()


def test_admin_auth_content_cv_and_moderation():
    with TestClient(app) as client:
        setup_admin()
        assert client.get("/api/admin/dashboard").status_code == 401
        bad = client.post("/api/admin/login", json={"username": "test-admin", "password": "wrong password"})
        assert bad.status_code == 401
        logged = client.post("/api/admin/login", json={"username": "test-admin", "password": "a-very-long-test-password-42!"})
        assert logged.status_code == 200
        csrf = logged.json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        assert client.get("/api/admin/dashboard").status_code == 200

        no_csrf = client.put("/api/admin/settings", json={"settings": {"tagline": "Updated"}})
        assert no_csrf.status_code == 403
        saved = client.put("/api/admin/settings", headers=headers, json={"settings": {"portfolio_name": "Ahmed Shahid", "cv_name": "Ahmed Chai", "tagline": "A verified editable tagline"}})
        assert saved.status_code == 200
        public_settings = client.get("/api/public/data").json()["settings"]
        assert public_settings["cv_name"] == "Ahmed Chai"
        assert "profile_image_file" not in public_settings and "cv_uploaded_file" not in public_settings

        project = client.post("/api/admin/content/projects", headers=headers, json={"data": {"title": "Test project", "description": "Project description", "category": "Test", "technologies": "Python"}, "published": True, "sort_order": 1, "moderation_status": "approved"})
        assert project.status_code == 200
        assert any(x["data"]["title"] == "Test project" for x in client.get("/api/public/data").json()["projects"])
        item_id = project.json()["item"]["id"]
        assert client.delete(f"/api/admin/content/projects/{item_id}", headers=headers).status_code == 200

        review = client.post("/api/public/reviews", json={"name": "Reviewer", "role": "Collaborator", "message": "This is a sufficiently long review.", "rating": 5, "website": ""})
        assert review.status_code == 200
        assert all(x["data"]["name"] != "Reviewer" for x in client.get("/api/public/data").json()["reviews"])
        pending = client.get("/api/admin/content/reviews").json()["items"]
        review_item = next(x for x in pending if x["data"]["name"] == "Reviewer")
        assert review_item["moderation_status"] == "pending"
        approved = client.put(f"/api/admin/content/reviews/{review_item['id']}", headers=headers, json={"data": review_item["data"], "published": True, "sort_order": 0, "moderation_status": "approved"})
        assert approved.status_code == 200
        assert any(x["data"]["name"] == "Reviewer" for x in client.get("/api/public/data").json()["reviews"])

        contact = client.post("/api/public/contact", json={"name": "Test Person", "email": "test@example.com", "subject": "Hi", "message": "This is a contact message test.", "website": ""})
        assert contact.status_code == 200
        private_messages = client.get("/api/admin/contacts").json()["items"]
        message = next(x for x in private_messages if x["email"] == "test@example.com")
        assert client.patch(f"/api/admin/contacts/{message['id']}", headers=headers, json={"status": "resolved"}).status_code == 200
        assert client.get("/api/public/data").status_code == 200

        cv = client.get("/api/public/cv.pdf")
        assert cv.status_code == 200 and cv.content.startswith(b"%PDF-")
        assert cv.headers["content-type"] == "application/pdf"

        assert client.get("/api/admin/contacts").status_code == 200
        # Incrementing the account session version revokes the authenticated cookie.
        db = SessionLocal()
        try:
            account = db.query(AdminAccount).filter_by(username="test-admin").first()
            account.session_version += 1
            db.commit()
        finally:
            db.close()
        assert client.get("/api/admin/session").status_code == 401
        # An invalidated session cannot continue to call protected endpoints.
        assert client.get("/api/admin/dashboard").status_code == 401
        assert client.get("/api/admin/dashboard").status_code == 401


def test_upload_validation_and_dashboard_pages():
    with TestClient(app) as client:
        setup_admin()
        login = client.post("/api/admin/login", json={"username": "test-admin", "password": "a-very-long-test-password-42!"})
        assert login.status_code == 200
        csrf = login.json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        bad_image = client.post("/api/admin/profile-image", headers=headers, files={"file": ("bad.png", b"not an image", "image/png")})
        assert bad_image.status_code in (415, 422)
        bad_pdf = client.post("/api/admin/cv-upload", headers=headers, files={"file": ("bad.pdf", b"not a pdf", "application/pdf")})
        assert bad_pdf.status_code == 415

        image_bytes = BytesIO()
        Image.new("RGB", (256, 256), (20, 40, 90)).save(image_bytes, format="PNG")
        uploaded_image = client.post("/api/admin/profile-image", headers=headers, files={"file": ("portrait.png", image_bytes.getvalue(), "image/png")})
        assert uploaded_image.status_code == 200
        profile_response = client.get("/api/public/profile-image")
        assert profile_response.status_code == 200 and profile_response.content[:4] == b"RIFF" and profile_response.content[8:12] == b"WEBP"
        position = client.put("/api/admin/profile-image/position", headers=headers, json={"x": 42, "y": 36})
        assert position.status_code == 200
        public_settings = client.get("/api/public/data").json()["settings"]
        assert public_settings["profile_image_x"] == 42 and public_settings["profile_image_y"] == 36
        assert client.post("/api/admin/profile-image/reset", headers=headers, json={}).status_code == 200

        project_image = client.post("/api/admin/project-image", headers=headers, files={"file": ("project.png", image_bytes.getvalue(), "image/png")})
        assert project_image.status_code == 200
        project_url = project_image.json()["url"]
        assert client.get(project_url).status_code == 200
        project = client.post("/api/admin/content/projects", headers=headers, json={"data": {"title": "Image project", "description": "Project with uploaded image", "category": "Test", "technologies": "HTML, CSS", "image_url": project_url}, "published": True, "sort_order": 2, "moderation_status": "approved"})
        assert project.status_code == 200
        image_project_id = project.json()["item"]["id"]
        assert any(x["data"].get("image_url") == project_url for x in client.get("/api/public/data").json()["projects"])
        assert client.delete(f"/api/admin/content/projects/{image_project_id}", headers=headers).status_code == 200
        assert client.get(project_url).status_code == 404

        generated_pdf = client.get("/api/public/cv.pdf")
        upload_pdf = client.post("/api/admin/cv-upload", headers=headers, files={"file": ("resume.pdf", generated_pdf.content, "application/pdf")})
        assert upload_pdf.status_code == 200 and upload_pdf.json()["uploaded"] is True
        assert client.post("/api/admin/cv/reset", headers=headers, json={}).status_code == 200
        assert client.get("/").status_code == 200
        assert client.get("/admin").status_code == 200
        assert client.get("/healthz").json()["ok"] is True
        assert client.get("/api/admin/session").status_code == 200
