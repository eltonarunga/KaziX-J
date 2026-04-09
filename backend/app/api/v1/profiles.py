"""
app/api/v1/profiles.py
──────────────────────
Profile management and public profile views.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from postgrest.exceptions import APIError as PostgrestAPIError
from pydantic import BaseModel, Field, field_validator

from app.api.deps import CurrentSession, CurrentUser
from app.core.supabase import get_admin_client, get_anon_client, get_user_client

router = APIRouter()


class UpdateMyProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = None
    county: str | None = None
    area: str | None = None
    mpesa_number: str | None = Field(default=None, pattern=r"^\+254[0-9]{9}$")
    preferred_language: Literal["en", "sw"] | None = None
    avatar_url: str | None = None
    trade: str | None = None
    bio: str | None = None
    rate_min: int | None = Field(default=None, ge=0)
    rate_max: int | None = Field(default=None, ge=0)
    experience_years: int | None = Field(default=None, ge=0, le=60)
    skills: list[str] | None = None
    service_radius_km: int | None = Field(default=None, ge=0, le=1000)
    is_available: bool | None = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in value:
            skill = str(raw or "").strip()
            if not skill:
                continue
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(skill[:60])
        return cleaned[:20]


def _profile_update_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PostgrestAPIError):
        error_blob = " ".join(
            str(part or "")
            for part in (exc.code, exc.message, exc.details, exc.hint)
        ).lower()
        if exc.code in {"23505"} and ("uq_profiles_phone" in error_blob or "phone" in error_blob):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "That phone number is already linked to another account. "
                    "Sign in instead or use a different number."
                ),
            )
        if exc.code in {"23502", "23514", "22P02"} and ("mpesa_number" in error_blob or "phone" in error_blob):
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Enter a valid Kenyan phone number in +2547XXXXXXXX format.",
            )

    return HTTPException(status_code=500, detail="Failed to save profile changes.")


def _collect_profile_sections(admin, user_id: str, *, public: bool) -> dict:
    profile = (
        admin.table("profiles")
        .select(
            (
                "id, role, full_name, phone, email, county, area, mpesa_number, "
                "preferred_language, avatar_url, is_verified, created_at, updated_at"
            )
            if not public
            else (
                "id, role, full_name, county, area, preferred_language, avatar_url, "
                "is_verified, created_at, updated_at"
            )
        )
        .eq("id", user_id)
        .single()
        .execute()
    )

    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    payload = {"profile": profile.data, "fundi_profile": None}

    if profile.data["role"] == "fundi":
        fundi = (
            admin.table("fundi_profiles")
            .select(
                "trade, bio, rate_min, rate_max, experience_years, "
                "skills, service_radius_km, rating_avg, jobs_completed, "
                "is_available, kyc_status, created_at, updated_at"
            )
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        payload["fundi_profile"] = fundi.data

    return payload


@router.get("/me")
async def get_my_profile(user: CurrentUser):
    """
    Returns the full private profile of the logged-in user.
    Includes fundi-specific profile data if applicable.
    """
    admin = get_admin_client()
    try:
        return _collect_profile_sections(admin, user.user_id, public=False)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch your profile.")


@router.patch("/me")
async def update_my_profile(body: UpdateMyProfileRequest, user: CurrentUser, session: CurrentSession):
    """
    Updates the authenticated user's profile.
    """
    provided_fields = set(body.model_fields_set)
    if not provided_fields:
        raise HTTPException(status_code=400, detail="No profile fields were provided.")

    admin = get_admin_client()
    client = get_user_client(session.access_token)

    try:
        current = _collect_profile_sections(admin, user.user_id, public=False)
        current_profile = current["profile"]
        current_fundi = current["fundi_profile"] or {}
        role = current_profile["role"]

        profile_fields = {
            "full_name",
            "email",
            "county",
            "area",
            "mpesa_number",
            "preferred_language",
            "avatar_url",
        }
        fundi_fields = {
            "trade",
            "bio",
            "rate_min",
            "rate_max",
            "experience_years",
            "skills",
            "service_radius_km",
            "is_available",
        }

        if role != "fundi" and provided_fields & fundi_fields:
            raise HTTPException(
                status_code=422,
                detail="Only fundi accounts can update trade, rates, skills, or availability.",
            )

        profile_updates = {
            field: getattr(body, field)
            for field in profile_fields
            if field in provided_fields
        }

        if profile_updates:
            client.table("profiles").update(profile_updates).eq("id", user.user_id).execute()

        if role == "fundi":
            next_rate_min = body.rate_min if "rate_min" in provided_fields else current_fundi.get("rate_min")
            next_rate_max = body.rate_max if "rate_max" in provided_fields else current_fundi.get("rate_max")
            if next_rate_min is not None and next_rate_max is not None and next_rate_max < next_rate_min:
                raise HTTPException(
                    status_code=422,
                    detail="Maximum rate must be greater than or equal to minimum rate.",
                )

            fundi_updates = {
                field: getattr(body, field)
                for field in fundi_fields
                if field in provided_fields
            }
            if fundi_updates:
                client.table("fundi_profiles").upsert(
                    {"id": user.user_id, **fundi_updates},
                    on_conflict="id",
                ).execute()

        return _collect_profile_sections(admin, user.user_id, public=False)
    except HTTPException:
        raise
    except Exception as exc:
        raise _profile_update_http_error(exc)


@router.get("/{user_id}")
async def get_public_profile(user_id: str):
    """
    Publicly accessible profile view.
    Restricts sensitive fields and focuses on data other users can safely view.
    """
    client = get_anon_client()
    try:
        public_profile = _collect_profile_sections(client, user_id, public=True)
        return public_profile
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch public profile.")
