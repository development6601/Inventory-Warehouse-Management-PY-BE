from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import validate_password_value


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str
    address: str | None = None

    @field_validator("password")
    @classmethod
    def password_rules(cls, value: str) -> str:
        return validate_password_value(value)

    @field_validator("name", "phone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_rules(cls, value: str) -> str:
        return validate_password_value(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_rules(cls, value: str) -> str:
        return validate_password_value(value)


class UpdateMeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = None


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str
    expires_in_minutes: int
