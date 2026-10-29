"""API payload validation."""
from pydantic import BaseModel, Field
from typing import Any

class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)

class ContentPayload(BaseModel):
    data: dict[str, Any]
    published: bool = True
    sort_order: int = Field(default=0, ge=-100000, le=100000)
    moderation_status: str = Field(default="approved", pattern="^(pending|approved|rejected)$")

class SettingsPayload(BaseModel):
    settings: dict[str, Any]

class CVPayload(BaseModel):
    content: dict[str, Any]

class ContactPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    subject: str = Field(default="", max_length=180)
    message: str = Field(min_length=5, max_length=5000)
    website: str = Field(default="", max_length=300)  # honeypot; must remain empty

class ReviewPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="", max_length=120)
    message: str = Field(min_length=8, max_length=1500)
    rating: int = Field(default=5, ge=1, le=5)
    website: str = Field(default="", max_length=300)

class ContactStatusPayload(BaseModel):
    status: str = Field(pattern="^(unread|read|resolved)$")


class ProfileImagePositionPayload(BaseModel):
    x: int = Field(default=50, ge=0, le=100)
    y: int = Field(default=27, ge=0, le=100)
