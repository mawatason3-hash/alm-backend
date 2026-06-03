from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import database
from models import users
from auth import get_current_user
from utils import row_to_dict
from routers.email import send_otp_email, generate_otp

router = APIRouter()


class VerifyOtpRequest(BaseModel):
    otp_code: str

@router.get("/profile")
async def get_voter_profile(current_user=Depends(get_current_user)):
    user_row = await database.fetch_one(users.select().where(users.c.id == current_user["id"]))
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    user = row_to_dict(user_row)

    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "photo_url": user["photo_url"],
        "role": user["role"],
        "is_approved": user["is_approved"],
        "verified_by_admin": bool(user.get("verified_by_admin", False)),
        "admin_verified_at": str(user["admin_verified_at"]) if user.get("admin_verified_at") else None,
        "created_at": str(user["created_at"])
    }

@router.get("/verification-status")
async def get_verification_status(
    current_user=Depends(get_current_user)
):
    user_id = current_user.get("id")

    user_row = await database.fetch_one(
        users.select().where(users.c.id == user_id)
    )
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    user = row_to_dict(user_row)
    verified_by_admin = bool(user.get("verified_by_admin", False))
    otp_verified = bool(user.get("otp_verified", False))

    request_row = await database.fetch_one(
        """
        SELECT status FROM access_requests
        WHERE voter_id = :voter_id
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"voter_id": str(user_id)}
    )
    request_status = dict(request_row).get("status") if request_row else None

    is_verified = otp_verified or verified_by_admin

    return {
        "otp_verified": otp_verified,
        "verified_by_admin": verified_by_admin,
        "request_status": request_status,
        "can_access_ballot": is_verified,
        "admin_verified_at": str(user.get("admin_verified_at")) if user.get("admin_verified_at") else None
    }

@router.post("/send-otp")
async def send_otp(
    current_user=Depends(get_current_user)
):
    user_row = await database.fetch_one(users.select().where(users.c.id == current_user["id"]))
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    user = row_to_dict(user_row)
    if not user.get("email"):
        raise HTTPException(status_code=400, detail="Email address is required for verification.")

    generated_pin = generate_otp()
    otp_expires_at = datetime.utcnow() + timedelta(minutes=10)

    await database.execute(
        users.update()
        .where(users.c.id == current_user["id"])
        .values(
            otp_code=generated_pin,
            otp_expires_at=otp_expires_at,
            otp_verified=False
        )
    )

    sent = await send_otp_email(
        to_email=user["email"],
        voter_name=user.get("full_name", "Voter"),
        otp_code=generated_pin,
    )

    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Please contact admin."
        )

    return {
        "success": True,
        "message": "OTP sent"
    }

@router.post("/verify-otp")
async def verify_otp(body: VerifyOtpRequest, current_user=Depends(get_current_user)):
    user_row = await database.fetch_one(users.select().where(users.c.id == current_user["id"]))
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    user = row_to_dict(user_row)
    if user.get("otp_verified"):
        return {"success": True, "verified": True, "message": "Email already verified."}

    if not user.get("otp_code") or not user.get("otp_expires_at"):
        raise HTTPException(status_code=400, detail="No active OTP request. Please request a new code.")

    if datetime.utcnow() > user["otp_expires_at"]:
        raise HTTPException(status_code=400, detail="OTP expired, request new one")

    if body.otp_code.strip() != str(user["otp_code"]).strip():
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    await database.execute(
        users.update()
        .where(users.c.id == current_user["id"])
        .values(
            otp_verified=True,
            otp_verified_at=datetime.utcnow(),
            otp_code=None,
            otp_expires_at=None
        )
    )

    return {
        "success": True,
        "verified": True,
        "message": "Email verified. You can now proceed to vote."
    }

