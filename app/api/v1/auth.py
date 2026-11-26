from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user
from app.database.connection import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateMeRequest,
)
from app.schemas.common import (
    AccessTokenResponse,
    AuthTokenResponse,
    MessageResponse,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.register_user(db, payload)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.login_user(db, payload)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.refresh_access_token(db, payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.logout_user(db, current.id, payload.refresh_token)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.change_password(db, current.user, payload)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.forgot_password(db, str(payload.email))


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.reset_password(db, payload)


@router.get("/me", response_model=UserPublic)
def me(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.get_me(db, current.id)


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UpdateMeRequest,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return auth_service.update_me(db, current.user, payload)
