"""
app/api/v1/profiles.py
──────────────────────
Profile management and public profile views.
"""

from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser
from app.core.supabase import get_admin_client

router = APIRouter()

@router.get("/me")
async def get_my_profile(user: CurrentUser):
    """
    Returns the full private profile of the logged-in user.
    Includes fundi-specific profile data if applicable.
    """
    admin = get_admin_client()
    try:
        result = admin.table("profiles").select("*").eq("id", user.user_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        fundi = None
        if result.data["role"] == "fundi":
            fp = admin.table("fundi_profiles").select("*").eq("id", user.user_id).maybe_single().execute()
            fundi = fp.data
            
        return {"profile": result.data, "fundi_profile": fundi}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch your profile.")


@router.get("/{user_id}")
async def get_public_profile(user_id: str):
    """
    Publicly accessible profile view. 
    Restricts sensitive fields and focuses on fundi marketing data.
    """
    from app.core.supabase import get_anon_client
    client = get_anon_client()
    try:
        result = (
            client.table("profiles")
            .select("id, full_name, avatar_url, county, area, role, is_verified")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        p = result.data
        if p["role"] == "fundi":
            fp = client.table("fundi_profiles").select(
                "trade, bio, rate_min, rate_max, experience_years, "
                "skills, service_radius_km, rating_avg, jobs_completed, is_available, kyc_status"
            ).eq("id", user_id).maybe_single().execute()
            p["fundi_profile"] = fp.data
            
        return p
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch public profile.")
