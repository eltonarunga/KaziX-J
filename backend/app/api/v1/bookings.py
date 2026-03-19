"""
app/api/v1/bookings.py
──────────────────────
POST /v1/bookings/hire          → client hires a fundi (creates booking)
GET  /v1/bookings/{id}          → get booking detail
POST /v1/bookings/{id}/complete → client marks job complete, triggers escrow release
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, ClientUser
from app.core.supabase import get_admin_client
from app.core.logging import get_logger
from app.services.notifications import create_notification

logger = get_logger(__name__)
router = APIRouter()


class HireRequest(BaseModel):
    application_id: str
    agreed_amount:  int = Field(..., ge=1)
    start_date:     str | None = None  # ISO date


@router.post("/hire", status_code=status.HTTP_201_CREATED)
async def hire_fundi(body: HireRequest, user: ClientUser):
    """
    Client hires a fundi:
    1. Validates application ownership
    2. Creates a booking row
    3. Updates application status → hired
    4. Updates job status → active
    5. Fires hired notification to fundi
    """
    admin = get_admin_client()

    try:
        # Fetch application + related job
        app_result = (
            admin.table("applications")
            .select("*, jobs!job_id(id, client_id, status, title)")
            .eq("id", body.application_id)
            .single()
            .execute()
        )
        if not app_result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        app_ = app_result.data
        job  = app_["jobs"]

        if job["client_id"] != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
        if job["status"] not in ("open", "reviewing"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is not available for hiring")
        if app_["status"] != "pending" and app_["status"] != "shortlisted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot hire — application is {app_['status']}")

        # Create booking
        booking_data = {
            "job_id":          job["id"],
            "application_id":  body.application_id,
            "client_id":       user.user_id,
            "fundi_id":        app_["fundi_id"],
            "agreed_amount":   body.agreed_amount,
            "start_date":      body.start_date,
            "status":          "confirmed",
            "escrow_status":   "pending",
        }

        try:
            booking_result = admin.table("bookings").insert(booking_data).execute()
        except Exception as exc:
            if "uq_booking_application" in str(exc):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A booking already exists for this application")
            logger.error("Booking creation failed", error=str(exc))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create booking")

        booking = booking_result.data[0]

        # Update application and job status
        admin.table("applications").update({"status": "hired"}).eq("id", body.application_id).execute()
        admin.table("jobs").update({"status": "active"}).eq("id", job["id"]).execute()

        # Notify fundi
        await create_notification(
            user_id=app_["fundi_id"],
            type_="hired",
            title="You've been hired! 🎉",
            body=f"You were hired for: {job['title']}. Check your bookings.",
            action_url=f"/worker-hires.html",
        )

        logger.info("Fundi hired", booking_id=booking["id"], fundi=app_["fundi_id"])
        return booking
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Hiring flow failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete hiring process.")


@router.get("/{booking_id}")
async def get_booking(booking_id: str, user: CurrentUser):
    admin = get_admin_client()
    try:
        result = (
            admin.table("bookings")
            .select(
                "*, "
                "jobs!job_id(title, trade, county, area), "
                "profiles!client_id(full_name, phone, avatar_url), "
                "profiles!fundi_id(full_name, phone, avatar_url), "
                "transactions(id, type, amount, mpesa_ref, status, created_at)"
            )
            .eq("id", booking_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        b = result.data
        if b["client_id"] != user.user_id and b["fundi_id"] != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")

        return b
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch booking", booking_id=booking_id, error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch booking.")


@router.post("/{booking_id}/complete")
async def confirm_job_complete(booking_id: str, user: ClientUser):
    """
    Client confirms job is done.
    Sets booking status → completed.
    M-Pesa escrow release is triggered separately by the mpesa router
    after payment confirmation.
    """
    admin = get_admin_client()
    try:
        booking = admin.table("bookings").select("*").eq("id", booking_id).single().execute()

        if not booking.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        b = booking.data

        if b["client_id"] != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the client can confirm completion")
        if b["status"] not in ("confirmed", "in_progress"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Booking is already {b['status']}")

        admin.table("bookings").update({
            "status": "completed",
        }).eq("id", booking_id).execute()

        # Notify fundi
        await create_notification(
            user_id=b["fundi_id"],
            type_="payment",
            title="Job confirmed complete ✅",
            body="The client has confirmed the job is done. Your M-Pesa payment is being released.",
            action_url="/worker-hires.html",
        )

        logger.info("Job confirmed complete", booking_id=booking_id, client=user.user_id)
        return {"success": True, "message": "Job marked complete. Escrow release initiated."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Job completion confirmation failed", booking_id=booking_id, error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to confirm job completion.")
