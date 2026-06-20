from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import AuthExchangeRequest, AuthResponse, LoginRequest, RegisterRequest, UserResponse, UserUpdateRequest
from app.services import authenticate_user, get_user_by_email, register_user, update_user_profile, upsert_external_auth_user
from app.utils.supabase_auth import fetch_user_for_access_token, sign_in_with_email, sign_up_with_email, supabase_auth_enabled
from app.utils.auth import create_access_token


router = APIRouter()


def _issue_auth_response(user: User, message: str | None = None) -> AuthResponse:
    token, expires_in = create_access_token(str(user.id), user.role, user.email)
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
        message=message,
    )


def _profile_value(profile: dict[str, Any], *keys: str) -> str | None:
    metadata = profile.get("user_metadata") or {}
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in keys:
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def _exchange_supabase_token(access_token: str, db: AsyncSession) -> AuthResponse:
    profile = await fetch_user_for_access_token(access_token)
    email = profile.get("email")
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase did not return a valid email for this account.",
        )

    user = await upsert_external_auth_user(
        email=email,
        full_name=_profile_value(profile, "full_name", "name"),
        phone=_profile_value(profile, "phone"),
        organization=_profile_value(profile, "organization"),
        db=db,
    )
    return _issue_auth_response(user)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = await get_user_by_email(data.email, db)
    if existing and existing.role in {"admin", "staff"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This email is reserved for an internal staff account.",
        )

    if not supabase_auth_enabled():
        user = await register_user(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone=data.phone,
            organization=data.organization,
            db=db,
        )
        return _issue_auth_response(user, "Account created successfully.")

    signup = await sign_up_with_email(
        email=str(data.email),
        password=data.password,
        full_name=data.full_name,
        phone=data.phone,
        organization=data.organization,
    )
    access_token = signup.get("access_token")
    if isinstance(access_token, str) and access_token:
        response = await _exchange_supabase_token(access_token, db)
        response.message = "Account created successfully."
        return response

    return AuthResponse(
        requires_email_verification=True,
        message="Account created. Check your email to confirm your address, then continue from the confirmation link.",
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = await get_user_by_email(data.email, db)
    if existing and existing.role in {"admin", "staff"}:
        user = await authenticate_user(data.email, data.password, db)
        return _issue_auth_response(user)

    try:
        user = await authenticate_user(data.email, data.password, db)
        return _issue_auth_response(user)
    except HTTPException as local_error:
        if not supabase_auth_enabled():
            raise local_error

    signin = await sign_in_with_email(email=str(data.email), password=data.password)
    access_token = signin.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase did not return an access token for this login.",
        )
    return await _exchange_supabase_token(access_token, db)


@router.post("/exchange", response_model=AuthResponse)
async def exchange_supabase_session(
    data: AuthExchangeRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    return await _exchange_supabase_token(data.access_token, db)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await update_user_profile(current_user, data, db)
    return UserResponse.model_validate(user)
