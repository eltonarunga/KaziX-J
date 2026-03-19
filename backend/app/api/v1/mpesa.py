"""
app/api/v1/mpesa.py
───────────────────
Daraja STK Push and callback handler (Task 8).

POST /v1/mpesa/stk-push    → initiate payment from client
POST /v1/mpesa/callback    → Safaricom calls this after payment
"""

import base64
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.supabase import get_admin_client
from app.services.notifications import create_notification

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


# ── Daraja helpers ───────────────────────────────────────────

async def get_daraja_access_token() -> str:
    """
    Fetches a short-lived OAuth2 access token from Safaricom Daraja.
    In production cache this for ~55 minutes.
    """
    url = f"{settings.mpesa_base_url}/oauth/v1/generate?grant_type=client_credentials"
    creds = base64.b64encode(
        f"{settings.mpesa_consumer_key}:{settings.mpesa_consumer_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Basic {creds}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]


def generate_mpesa_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """
    Daraja STK password = Base64(shortcode + passkey + timestamp)
    """
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


# ── Schemas ──────────────────────────────────────────────────

class STKPushRequest(BaseModel):
    booking_id: str
    phone:      str = Field(..., pattern=r"^\+254[0-9]{9}$")
    amount:     int = Field(..., ge=1)


# ── Routes ───────────────────────────────────────────────────

@router.post("/stk-push")
async def initiate_stk_push(body: STKPushRequest, user: CurrentUser):
    """
    Initiates an M-Pesa STK push to the client's phone.
    1. Verifies the booking belongs to the caller
    2. Calls Safaricom Daraja STK push API
    3. Creates a transactions row with status=pending
    4. Returns checkout_request_id to the frontend for polling
    """
    admin = get_admin_client()

    try:
        # Verify booking ownership
        booking = (
            admin.table("bookings")
            .select("id, client_id, agreed_amount, escrow_status")
            .eq("id", body.booking_id)
            .single()
            .execute()
        )
        if not booking.data:
            raise HTTPException(status_code=404, detail="Booking not found")
        b = booking.data
        if b["client_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Not your booking")
        if b["escrow_status"] == "held":
            raise HTTPException(status_code=400, detail="Escrow already held for this booking")

        # Build Daraja payload
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password  = generate_mpesa_password(
            settings.mpesa_shortcode, settings.mpesa_passkey, timestamp
        )
        # Daraja expects phone in 254XXXXXXXXX format (no +)
        phone_clean = body.phone.lstrip("+")

        stk_payload = {
            "BusinessShortCode": settings.mpesa_shortcode,
            "Password":          password,
            "Timestamp":         timestamp,
            "TransactionType":   "CustomerPayBillOnline",
            "Amount":            body.amount,
            "PartyA":            phone_clean,
            "PartyB":            settings.mpesa_shortcode,
            "PhoneNumber":       phone_clean,
            "CallBackURL":       settings.mpesa_callback_url,
            "AccountReference":  f"KaziX-{body.booking_id[:8].upper()}",
            "TransactionDesc":   "KaziX escrow payment",
        }

        try:
            access_token = await get_daraja_access_token()
            async with httpx.AsyncClient() as client_:
                resp = await client_.post(
                    f"{settings.mpesa_base_url}/mpesa/stkpush/v1/processrequest",
                    json=stk_payload,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=15,
                )
                resp.raise_for_status()
                daraja_response = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Daraja STK push failed", booking=body.booking_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="M-Pesa payment initiation failed. Please try again.",
            )

        checkout_request_id = daraja_response.get("CheckoutRequestID")
        if not checkout_request_id:
            raise HTTPException(status_code=502, detail="Invalid response from M-Pesa gateway")

        # Create pending transaction record
        tx_data = {
            "booking_id": body.booking_id,
            "type":       "escrow_in",
            "amount":     body.amount,
            "mpesa_ref":  checkout_request_id,  # update with real receipt on callback
            "from_phone": body.phone,
            "to_phone":   f"Paybill {settings.mpesa_shortcode}",
            "status":     "pending",
        }
        admin.table("transactions").insert(tx_data).execute()

        logger.info(
            "STK push initiated",
            booking=body.booking_id,
            checkout_id=checkout_request_id,
        )

        return {
            "success":              True,
            "checkout_request_id":  checkout_request_id,
            "message":              "M-Pesa prompt sent to your phone",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("STK push initiation failed", booking_id=body.booking_id, error=str(exc))
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/callback")
async def mpesa_callback(request: Request):
    """
    Safaricom calls this URL directly after STK push completes.
    No authentication header — Safaricom doesn't send one.
    We verify by matching the CheckoutRequestID to a known transaction.

    Success → update transaction to confirmed, escrow_status → held.
    Failure → update transaction to failed, notify client.
    """
    try:
        payload = await request.json()
    except Exception:
        logger.warning("M-Pesa callback: invalid JSON payload")
        return {"ResultCode": 1, "ResultDesc": "Invalid payload"}

    logger.info("M-Pesa callback received", raw=str(payload)[:200])

    body = payload.get("Body", {})
    stk  = body.get("stkCallback", {})

    result_code    = stk.get("ResultCode")
    checkout_id    = stk.get("CheckoutRequestID")
    result_desc    = stk.get("ResultDesc", "")

    if not checkout_id:
        logger.warning("M-Pesa callback missing CheckoutRequestID")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    admin = get_admin_client()

    try:
        # Find the transaction
        tx_result = (
            admin.table("transactions")
            .select("id, booking_id, amount")
            .eq("mpesa_ref", checkout_id)
            .maybe_single()
            .execute()
        )

        if not tx_result.data:
            logger.warning("M-Pesa callback: unknown transaction", checkout_id=checkout_id)
            return {"ResultCode": 0, "ResultDesc": "Accepted"}

        tx = tx_result.data

        if result_code == 0:
            # ── SUCCESS ─────────────────────────────────────────
            # Extract M-Pesa receipt number from callback metadata
            mpesa_receipt = None
            items = stk.get("CallbackMetadata", {}).get("Item", [])
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    mpesa_receipt = item.get("Value")
                    break

            # Update transaction → confirmed
            admin.table("transactions").update({
                "status":    "confirmed",
                "mpesa_ref": mpesa_receipt or checkout_id,
            }).eq("id", tx["id"]).execute()

            # Update booking escrow_status → held
            admin.table("bookings").update({
                "escrow_status":  "held",
                "escrow_held_at": datetime.utcnow().isoformat(),
                "mpesa_receipt":  mpesa_receipt,
                "status":         "in_progress",
            }).eq("id", tx["booking_id"]).execute()

            # Get client_id to notify
            bk = admin.table("bookings").select("client_id, fundi_id").eq("id", tx["booking_id"]).single().execute()
            if bk.data:
                import asyncio
                asyncio.create_task(create_notification(
                    user_id=bk.data["client_id"],
                    type_="payment",
                    title="Payment confirmed ✅",
                    body=f"KES {tx['amount']:,} held in escrow. Receipt: {mpesa_receipt}",
                    action_url="/my-hires.html",
                ))

            logger.info("M-Pesa payment confirmed", booking=tx["booking_id"], receipt=mpesa_receipt)

        else:
            # ── FAILURE ──────────────────────────────────────────
            admin.table("transactions").update({"status": "failed"}).eq("id", tx["id"]).execute()

            bk = admin.table("bookings").select("client_id").eq("id", tx["booking_id"]).single().execute()
            if bk.data:
                import asyncio
                asyncio.create_task(create_notification(
                    user_id=bk.data["client_id"],
                    type_="payment",
                    title="Payment failed ❌",
                    body=f"M-Pesa payment failed: {result_desc}. Please try again.",
                    action_url="/my-hires.html",
                ))

            logger.warning(
                "M-Pesa payment failed",
                booking=tx["booking_id"],
                reason=result_desc,
            )
    except Exception as exc:
        logger.error("Error processing M-Pesa callback", error=str(exc))
        # Even on error, we return 0 to Safaricom so they don't retry indefinitely
        # assuming we have logged the error for manual intervention.

    # Safaricom expects exactly this response
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
