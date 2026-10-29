"""Initial safe defaults. Values are editable and avoid making up personal facts."""
from sqlalchemy.orm import Session
from app.models import SiteSetting, PortfolioItem

DEFAULT_SITE_SETTINGS = {
    "portfolio_name": "Ahmed Shahid",
    "cv_name": "Ahmed Chai",
    "browser_title": "Ahmed Shahid — Portfolio",
    "meta_description": "Portfolio, education, skills, projects, and contact information.",
    "tagline": "Building thoughtful digital experiences",
    "intro": "Hello, I'm Ahmed Shahid.",
    "hero_description": "A place to share a professional journey, ideas, and work. Explore the sections below, or get in touch.",
    "about_text": "This portfolio is ready for verified biography details, skills, and project work. Use the Admin dashboard to personalize this section.",
    "footer_text": "Designed with care · Ahmed Shahid",
    "contact_email": "",
    "whatsapp_number": "",
    "location": "",
    "profile_image_file": "",
}
DEFAULT_CV_CONTENT = {
    "headline": "Professional Profile",
    "summary": "Add a verified professional summary in the Admin dashboard.",
    "email": "",
    "phone": "",
    "location": "",
    "work_experience": "",
    "certifications": "",
    "achievements": "",
    "additional_information": "",
}

def seed_database(db: Session) -> None:
    marker = db.get(SiteSetting, "_system_seed_version")
    first_seed = marker is None
    site = db.get(SiteSetting, "site_config")
    if site is None:
        db.add(SiteSetting(key="site_config", value=DEFAULT_SITE_SETTINGS.copy()))
    else:
        merged_site = dict(site.value or {})
        for key, value in DEFAULT_SITE_SETTINGS.items():
            merged_site.setdefault(key, value)
        site.value = merged_site
    cv = db.get(SiteSetting, "cv_content")
    if cv is None:
        db.add(SiteSetting(key="cv_content", value=DEFAULT_CV_CONTENT.copy()))
    else:
        merged_cv = dict(cv.value or {})
        for key, value in DEFAULT_CV_CONTENT.items():
            merged_cv.setdefault(key, value)
        cv.value = merged_cv
    if first_seed and not db.query(PortfolioItem).filter(PortfolioItem.kind == "education").count():
        db.add(PortfolioItem(kind="education", data={
            "title": "Cambridge World High School",
            "institution": "Cambridge World High School",
            "qualification": "Add verified qualification",
            "dates": "",
            "description": "Education details can be completed in the Admin dashboard."
        }, sort_order=0, published=True, moderation_status="approved"))
    if first_seed:
        db.add(SiteSetting(key="_system_seed_version", value={"version": 1}))
    db.commit()
