"""
app/api/v1/auth.py
──────────────────
Phone OTP authentication flow (Tasks 4 & 5).

POST /v1/auth/send-otp     → sends 6-digit OTP via Supabase phone auth
POST /v1/auth/verify-otp   → verifies OTP, creates profile if new user
POST /v1/auth/oauth/start  → returns Supabase OAuth authorize URL
POST /v1/auth/oauth/exchange → exchanges OAuth code for Supabase session
POST /v1/auth/profile      → completes registration (step 4 form data)
GET  /v1/auth/session      → returns current user + profile in one call
GET  /v1/auth/bootstrap    → returns profile completion state for OAuth/OTP sessions
"""

import secrets
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from supabase import create_client

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.supabase import get_admin_client, get_anon_client

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()

_OAUTH_STATE_TTL_SECONDS = 600
_OAUTH_STATE_STORE: dict[str, dict[str, str | float]] = {}


# ── Schemas ──────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+254[0-9]{9}$", examples=["+254712345678"])


class VerifyOTPRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+254[0-9]{9}$")
    token: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class CreateProfileRequest(BaseModel):
    full_name: str      = Field(..., min_length=2, max_length=120)
    phone: str          = Field(..., pattern=r"^\+254[0-9]{9}$")
    email: str | None   = None
    county: str | None  = None
    area: str | None    = None
    role: Literal["client", "fundi"] = "client"
    mpesa_number: str | None = None
    preferred_language: Literal["en", "sw"] = "en"
    # Fundi-only fields
    trade: str | None           = None
    rate_min: int | None        = Field(None, ge=0)
    rate_max: int | None        = Field(None, ge=0)
    experience_years: int | None = Field(None, ge=0, le=60)
    bio: str | None             = None

    @field_validator("role")
    @classmethod
    def fundi_requires_trade(cls, role, info):
        # Full cross-field validation happens in the route handler
        return role


class OTPResponse(BaseModel):
    success: bool
    message: str


class SessionResponse(BaseModel):
    user_id: str
    role: str
    phone: str
    full_name: str
    is_verified: bool


class OAuthStartRequest(BaseModel):
    provider: Literal["google", "apple", "github"]
    redirect_to: str = Field(..., min_length=1)
    scopes: str | None = None


class OAuthStartResponse(BaseModel):
    provider: str
    url: str
    state: str


class OAuthExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    state: str = Field(..., min_length=8)
    redirect_to: str | None = None


class BootstrapResponse(BaseModel):
    is_new_user: bool
    redirect_to: str
    role: str
    profile: dict | None


def _resolve_profile_state(admin, user_id: str) -> tuple[dict | None, bool, str]:
    """
    Shared profile state resolver for OTP/OAuth flows.
    """
    existing = (
        admin.table("profiles")
        .select("id, role, full_name, phone, is_verified")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    profile = existing.data if existing else None
    is_new_user = profile is None or profile.get("full_name") == "User"
    role = profile.get("role") if profile else "client"
    redirect_to = "complete-registration" if is_new_user else f"{role}-dashboard"
    return profile, is_new_user, redirect_to


def _cleanup_oauth_state(now_ts: float) -> None:
    expired = [
        state
        for state, payload in _OAUTH_STATE_STORE.items()
        if now_ts - float(payload.get("created_at", 0)) > _OAUTH_STATE_TTL_SECONDS
    ]
    for state in expired:
        _OAUTH_STATE_STORE.pop(state, None)


def _put_oauth_state(state: str, code_verifier: str) -> None:
    now_ts = time.time()
    _cleanup_oauth_state(now_ts)
    _OAUTH_STATE_STORE[state] = {
        "code_verifier": code_verifier,
        "created_at": now_ts,
    }


def _pop_oauth_code_verifier(state: str) -> str | None:
    now_ts = time.time()
    _cleanup_oauth_state(now_ts)
    payload = _OAUTH_STATE_STORE.pop(state, None)
    if not payload:
        return None
    return str(payload.get("code_verifier") or "")


# ── Routes ───────────────────────────────────────────────────

@router.post("/send-otp", response_model=OTPResponse, status_code=200)
async def send_otp(body: SendOTPRequest):
    """
    Send a 6-digit OTP to the given phone number.
    Supabase phone auth handles both sign-up and sign-in with the same call.
    SMS delivery is via Africa's Talking (configured in Supabase dashboard).
    """
    client = get_anon_client()
    try:
        # Supabase signInWithOtp — works for new and existing users
        # Note: signInWithOtp returns an AuthResponse which contains user/session
        # but for OTP send, we mostly care if it didn't raise an exception.
        client.auth.sign_in_with_otp({"phone": body.phone})
        logger.info("OTP dispatched", phone=body.phone[-4:])  # log last 4 digits only
        return OTPResponse(success=True, message="OTP sent successfully")
    except Exception as exc:
        logger.error("OTP dispatch failed", phone=body.phone[-4:], error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send OTP. Please try again.",
        )


@router.post("/verify-otp", status_code=200)
async def verify_otp(body: VerifyOTPRequest):
    """
    Verify OTP token.
    Returns Supabase session (access_token, refresh_token) + is_new_user flag.
    Frontend uses is_new_user to decide whether to show the profile completion form.
    """
    client = get_anon_client()
    try:
        response = client.auth.verify_otp({
            "phone": body.phone,
            "token": body.token,
            "type": "sms",
        })
    except Exception as exc:
        logger.warning("OTP verification failed", phone=body.phone[-4:], error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP.",
        )

    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP verification did not produce a session.",
        )

    user_id = response.user.id
    admin = get_admin_client()

    try:
        _, is_new_user, redirect_to = _resolve_profile_state(admin, user_id)
    except Exception as exc:
        logger.error("Profile check failed", user_id=user_id, error=str(exc))
        is_new_user = True
        redirect_to = "complete-registration"

    return {
        "access_token":  response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "token_type":    "bearer",
        "expires_in":    response.session.expires_in,
        "is_new_user":   is_new_user,
        "redirect_to":   redirect_to,
    }


@router.post("/oauth/start", response_model=OAuthStartResponse, status_code=200)
async def start_oauth(body: OAuthStartRequest):
    """
    Returns a Supabase OAuth authorization URL for the selected provider.
    Frontend should redirect the browser to the returned URL.
    """
    # Build an isolated auth client per request so we can safely capture
    # this login's PKCE code verifier without cross-user collisions.
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    state = secrets.token_urlsafe(24)

    options = {"redirect_to": body.redirect_to, "query_params": {"state": state}}
    if body.scopes:
        options["scopes"] = body.scopes

    try:
        response = client.auth.sign_in_with_oauth(
            {"provider": body.provider, "options": options}
        )

        storage = getattr(client.auth, "_storage", None)
        code_verifier = getattr(storage, "storage", {}).get(
            "supabase.auth.token-code-verifier"
        )
        if not code_verifier:
            raise RuntimeError("Missing PKCE code verifier for OAuth start")

        _put_oauth_state(state, str(code_verifier))
        return OAuthStartResponse(provider=response.provider, url=response.url, state=state)
    except Exception as exc:
        logger.error("OAuth start failed", provider=body.provider, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize OAuth login.",
        )


@router.post("/oauth/exchange", status_code=200)
async def exchange_oauth_code(body: OAuthExchangeRequest):
    """
    Exchanges Supabase OAuth callback code for a session using the stored PKCE verifier.
    """
    code_verifier = _pop_oauth_code_verifier(body.state)
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth state is invalid or expired. Please start login again.",
        )

    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    exchange_payload = {
        "auth_code": body.code,
        "code_verifier": code_verifier,
    }
    if body.redirect_to:
        exchange_payload["redirect_to"] = body.redirect_to

    try:
        response = client.auth.exchange_code_for_session(exchange_payload)
    except Exception as exc:
        logger.error("OAuth exchange failed", state=body.state[:8], error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to complete OAuth login.",
        )

    if not response.session or not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth login did not return a session.",
        )

    user_id = response.user.id
    admin = get_admin_client()
    try:
        _, is_new_user, redirect_to = _resolve_profile_state(admin, user_id)
    except Exception as exc:
        logger.error("OAuth profile check failed", user_id=user_id, error=str(exc))
        is_new_user = True
        redirect_to = "complete-registration"

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "token_type": "bearer",
        "expires_in": response.session.expires_in,
        "is_new_user": is_new_user,
        "redirect_to": redirect_to,
    }


@router.post("/profile", status_code=201)
async def create_profile(body: CreateProfileRequest, user: CurrentUser):
    """
    Complete profile creation after OTP verification (register.html step 4).
    Idempotent — returns existing profile if one already exists.
    Creates a fundi_profiles row automatically when role == 'fundi'.
    """
    if body.role == "fundi" and not body.trade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Trade is required for fundi registration.",
        )

    admin = get_admin_client()

    # Upsert profiles row (idempotent)
    profile_data = {
        "id":                 user.user_id,
        "role":               body.role,
        "full_name":          body.full_name,
        "phone":              body.phone,
        "email":              body.email,
        "county":             body.county,
        "area":               body.area,
        "mpesa_number":       body.mpesa_number or body.phone,
        "preferred_language": body.preferred_language,
    }

    try:
        profile_result = (
            admin.table("profiles")
            .upsert(profile_data, on_conflict="id")
            .execute()
        )
    except Exception as exc:
        logger.error("Profile upsert failed", user_id=user.user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save profile. Please try again.",
        )

    # Create fundi_profiles row if applicable
    if body.role == "fundi":
        fundi_data = {
            "id":               user.user_id,
            "trade":            body.trade,
            "bio":              body.bio,
            "rate_min":         body.rate_min,
            "rate_max":         body.rate_max,
            "experience_years": body.experience_years,
            "kyc_status":       "pending",
        }
        try:
            admin.table("fundi_profiles").upsert(fundi_data, on_conflict="id").execute()
        except Exception as exc:
            logger.error("Fundi profile upsert failed", user_id=user.user_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not save fundi profile.",
            )

    logger.info("Profile created", user_id=user.user_id, role=body.role)
    return {"success": True, "profile": profile_result.data[0] if profile_result.data else {}}


@router.get("/session", response_model=SessionResponse)
async def get_session(user: CurrentUser):
    """
    Returns the current user's profile in a single call.
    Import and call from every authenticated page on load.
    """
    admin = get_admin_client()
    try:
        result = (
            admin.table("profiles")
            .select("id, role, phone, full_name, is_verified")
            .eq("id", user.user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        p = result.data
        return SessionResponse(
            user_id=p["id"],
            role=p["role"],
            phone=p["phone"],
            full_name=p["full_name"],
            is_verified=p["is_verified"],
        )
    except Exception as exc:
        logger.error("Session fetch failed", user_id=user.user_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to fetch session data.")


@router.get("/bootstrap", response_model=BootstrapResponse, status_code=200)
async def bootstrap_auth(user: CurrentUser):
    """
    Returns profile completion state for any authenticated Supabase session
    (OTP or OAuth), allowing frontend to route users after login.
    """
    admin = get_admin_client()
    try:
        profile, is_new_user, redirect_to = _resolve_profile_state(admin, user.user_id)
        role = profile.get("role") if profile else "client"
        return BootstrapResponse(
            is_new_user=is_new_user,
            redirect_to=redirect_to,
            role=role,
            profile=profile,
        )
    except Exception as exc:
        logger.error("Auth bootstrap failed", user_id=user.user_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to bootstrap auth state.")
