from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# At least 8 chars, one uppercase, one lowercase, one digit, one special character
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)

IMAGE_FILE_PATTERN = re.compile(
    r"\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$",
    re.IGNORECASE,
)

# Hosts that serve images even when the path has no file extension
KNOWN_IMAGE_HOSTS = (
    "placehold.co",
    "placekitten.com",
    "picsum.photos",
    "i.ibb.co",
    "ibb.co",
    "res.cloudinary.com",
    "images.unsplash.com",
    "cdn.pixabay.com",
    "imgur.com",
    "i.imgur.com",
)


def validate_password_value(value: str) -> str:
    if not PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be at least 8 characters and include "
            "one uppercase letter, one lowercase letter, one number, "
            "and one special character"
        )
    return value


def validate_phone_value(value: str) -> str:
    """Accept local numbers or +country-code numbers; store a cleaned form.

    Examples of valid values:
    - 9876543210
    - +919876543210
    - +1 202-555-0182
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Phone number is required.")

    compact = re.sub(r"[\s\-().]", "", cleaned)
    if compact.startswith("+"):
        digits = compact[1:]
        if not digits.isdigit():
            raise ValueError(
                "Phone number with country code may only contain digits after +."
            )
        if len(digits) < 8 or len(digits) > 15:
            raise ValueError(
                "Phone with country code must have 8 to 15 digits after + "
                "(example: +919876543210)."
            )
        # Country code 1–3 digits; remaining national number at least 6 digits
        if len(digits) < 7:
            raise ValueError("Phone number is too short for the country code.")
        return f"+{digits}"

    digits = re.sub(r"\D", "", compact)
    if not digits.isdigit() or len(digits) < 10 or len(digits) > 15:
        raise ValueError(
            "Phone number must have 10 to 15 digits, or use +country code "
            "(example: 9876543210 or +919876543210)."
        )
    return digits


def validate_image_url_value(value: str) -> str:
    """Require a direct image URL (file extension or known image host)."""
    cleaned = value.strip()
    if not cleaned.startswith(("http://", "https://")):
        raise ValueError("Image URL must start with http:// or https://")

    parsed = urlparse(cleaned)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or ""

    has_image_ext = bool(
        IMAGE_FILE_PATTERN.search(path) or IMAGE_FILE_PATTERN.search(cleaned)
    )
    known_host = any(
        host == allowed or host.endswith("." + allowed)
        for allowed in KNOWN_IMAGE_HOSTS
    )

    # Reject typical HTML product pages with no image extension
    if "/products/" in path.lower() and not has_image_ext and not known_host:
        raise ValueError(
            "Use a direct image link (ending in .png / .jpg / .webp), "
            "not a shop or product page URL."
        )

    if not has_image_ext and not known_host:
        raise ValueError(
            "Image URL must end with an image file type "
            "(.png, .jpg, .jpeg, .webp, .gif) "
            "or come from a known image host "
            "(placehold.co, ImgBB, Cloudinary, etc.)."
        )
    return cleaned


class MessageResponse(BaseModel):
    message: str


class WarehouseBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_code: str
    name: str
    location: str


class ManagerBrief(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    phone: str
    address: str | None = None
    joining_date: date
    role: str
    role_name: str
    is_active: bool
    last_login_at: datetime | None = None
    warehouse_id: UUID | None = None
    warehouse_code: str | None = None
    warehouse: WarehouseBrief | None = None


class TokenUserSummary(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str
    role: str
    role_name: str
    warehouse_id: UUID | None = None
    warehouse_code: str | None = None
    is_active: bool


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: TokenUserSummary


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
