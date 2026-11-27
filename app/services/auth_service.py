from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import (
    access_token_expires_in_seconds,
    create_access_token,
    generate_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import PasswordResetToken, RefreshToken, Role, User, UserWarehouse
from app.models.constants import RoleCode
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateMeRequest,
)
from app.schemas.common import AuthTokenResponse, AccessTokenResponse, MessageResponse
from app.services.user_serializers import serialize_token_user, serialize_user


def _get_role(db: Session, code: str) -> Role:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System roles are not configured. Please contact support.",
        )
    return role


def _load_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .where(func.lower(User.email) == email.lower())
        .options(
            joinedload(User.role),
            joinedload(User.warehouse_assignment).joinedload(
                UserWarehouse.warehouse
            ),
        )
    )


def _load_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            joinedload(User.role),
            joinedload(User.warehouse_assignment).joinedload(
                UserWarehouse.warehouse
            ),
        )
    )


def _warehouse_id_for(user: User) -> UUID | None:
    if user.warehouse_assignment is None:
        return None
    return user.warehouse_assignment.warehouse_id


def _issue_tokens(db: Session, user: User) -> AuthTokenResponse:
    warehouse_id = _warehouse_id_for(user)
    access = create_access_token(
        user_id=user.id,
        role_code=user.role.code,
        warehouse_id=warehouse_id,
    )
    refresh_plain = generate_refresh_token()
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_plain),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_row)
    db.commit()
    return AuthTokenResponse(
        access_token=access,
        refresh_token=refresh_plain,
        expires_in=access_token_expires_in_seconds(),
        user=serialize_token_user(user),
    )


def register_user(db: Session, payload: RegisterRequest):
    existing = _load_user_by_email(db, str(payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    staff_role = _get_role(db, RoleCode.STAFF)
    user = User(
        role_id=staff_role.id,
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        phone=payload.phone.strip(),
        address=payload.address,
        password_hash=hash_password(payload.password),
        joining_date=date.today(),
        is_active=True,
    )
    db.add(user)
    db.commit()
    user = _load_user_by_id(db, user.id)
    assert user is not None
    return serialize_user(user)


def login_user(db: Session, payload: LoginRequest) -> AuthTokenResponse:
    user = _load_user_by_email(db, str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This account has been deactivated. "
                "Please contact your administrator."
            ),
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    user = _load_user_by_id(db, user.id)
    assert user is not None
    return _issue_tokens(db, user)


def refresh_access_token(db: Session, refresh_token: str) -> AccessTokenResponse:
    token_row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(refresh_token)
        )
    )
    now = datetime.now(timezone.utc)
    if (
        token_row is None
        or token_row.revoked_at is not None
        or token_row.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = _load_user_by_id(db, token_row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to refresh session. Please sign in again.",
        )

    access = create_access_token(
        user_id=user.id,
        role_code=user.role.code,
        warehouse_id=_warehouse_id_for(user),
    )
    return AccessTokenResponse(
        access_token=access,
        expires_in=access_token_expires_in_seconds(),
    )


def logout_user(db: Session, user_id: UUID, refresh_token: str) -> MessageResponse:
    token_row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.user_id == user_id,
        )
    )
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        db.add(token_row)
        db.commit()
    return MessageResponse(message="You have been logged out successfully.")


def change_password(
    db: Session,
    user: User,
    payload: ChangePasswordRequest,
) -> MessageResponse:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if payload.new_password == payload.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )
    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
    return MessageResponse(message="Password changed successfully.")


def forgot_password(db: Session, email: str) -> ForgotPasswordResponse:
    """Same message whether or not the email exists (no 404 enumeration)."""
    generic_message = (
        "If an account exists for this email, a password reset token has been generated."
    )
    user = _load_user_by_email(db, email)
    if user is None:
        return ForgotPasswordResponse(message=generic_message)

    plain = generate_password_reset_token()
    row = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(plain),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.password_reset_expire_minutes),
    )
    db.add(row)
    db.commit()
    # Dev-friendly: include token when user exists so Swagger testing works.
    return ForgotPasswordResponse(
        message=generic_message,
        reset_token=plain,
        expires_in_minutes=settings.password_reset_expire_minutes,
    )


def reset_password(db: Session, payload: ResetPasswordRequest) -> MessageResponse:
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(payload.token)
        )
    )
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.password_hash = hash_password(payload.new_password)
    row.used_at = now
    db.add(user)
    db.add(row)
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return MessageResponse(message="Password has been reset successfully.")


def update_me(db: Session, user: User, payload: UpdateMeRequest):
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.address is not None:
        user.address = payload.address
    db.add(user)
    db.commit()
    refreshed = _load_user_by_id(db, user.id)
    assert refreshed is not None
    return serialize_user(refreshed)


def get_me(db: Session, user_id: UUID):
    user = _load_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return serialize_user(user)
