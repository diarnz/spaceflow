from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import settings


def supabase_auth_enabled() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


def frontend_auth_callback_url() -> str | None:
    if not settings.allowed_origins_list:
        return None
    preferred = next(
        (origin for origin in settings.allowed_origins_list if "5173" in origin),
        settings.allowed_origins_list[0],
    )
    return preferred.rstrip("/") + "/auth/callback"


def _headers(access_token: str | None = None) -> dict[str, str]:
    if not supabase_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured.",
        )
    headers = {
        "apikey": str(settings.SUPABASE_ANON_KEY),
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _extract_error(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("msg", "error_description", "message", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return "Supabase authentication request failed."


def _raise_for_supabase_error(status_code: int, payload: Any) -> None:
    detail = _extract_error(payload)
    lowered = detail.lower()

    if "email not confirmed" in lowered:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Check your email and confirm your account before signing in.",
        )
    if "invalid login credentials" in lowered:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if "user already registered" in lowered or "already been registered" in lowered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if "signup is disabled" in lowered:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign up is currently unavailable.",
        )

    mapped_status = (
        status.HTTP_401_UNAUTHORIZED
        if status_code in {400, 401}
        else status.HTTP_409_CONFLICT
        if status_code == 409
        else status.HTTP_400_BAD_REQUEST
    )
    raise HTTPException(status_code=mapped_status, detail=detail)


async def _request_json(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    if not settings.SUPABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured.",
        )

    url = settings.SUPABASE_URL.rstrip("/") + path
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.request(
            method,
            url,
            headers=_headers(access_token),
            json=json_body,
        )

    try:
        payload = response.json()
    except ValueError:
        payload = response.text

    if response.status_code >= 400:
        _raise_for_supabase_error(response.status_code, payload)

    if isinstance(payload, dict):
        return payload
    return {}


async def sign_up_with_email(
    *,
    email: str,
    password: str,
    full_name: str,
    phone: str | None,
    organization: str | None,
) -> dict[str, Any]:
    metadata = {
        "full_name": full_name,
        "phone": phone,
        "organization": organization,
    }
    metadata = {key: value for key, value in metadata.items() if value not in (None, "")}

    options: dict[str, Any] = {}
    redirect_to = frontend_auth_callback_url()
    if redirect_to:
        options["emailRedirectTo"] = redirect_to
    if metadata:
        options["data"] = metadata

    body: dict[str, Any] = {
        "email": email,
        "password": password,
    }
    if options:
        body["options"] = options

    return await _request_json("POST", "/auth/v1/signup", json_body=body)


async def sign_in_with_email(*, email: str, password: str) -> dict[str, Any]:
    return await _request_json(
        "POST",
        "/auth/v1/token?grant_type=password",
        json_body={"email": email, "password": password},
    )


async def fetch_user_for_access_token(access_token: str) -> dict[str, Any]:
    return await _request_json(
        "GET",
        "/auth/v1/user",
        access_token=access_token,
    )
