from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import verification_logs, users
from schemas import VerificationLogCreate
from auth import get_current_user, get_current_admin
from utils import row_to_dict, rows_to_list
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.post("/")
async def create_verification_log(body: VerificationLogCreate, current_user=Depends(get_current_user)):
    try:
        await database.execute(
            verification_logs.insert().values(
                id=uuid.uuid4(),
                voter_id=current_user["id"],
                result=body.result,
                distance=body.distance,
                upload_url=body.upload_url,
            )
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/")
async def list_verification_logs(admin=Depends(get_current_admin)):
    try:
        query = sa.text("""
            SELECT
                u.id as voter_id,
                u.full_name as voter_name,
                u.email as voter_email,
                CASE 
                    WHEN u.verified_by_admin = true THEN 'Admin Approved'
                    WHEN u.otp_verified = true THEN 'Email OTP'
                    ELSE 'Unverified'
                END as verification_method,
                COALESCE(u.admin_verified_at, u.otp_verified_at) as verification_timestamp
            FROM users u
            WHERE u.verified_by_admin = true OR u.otp_verified = true
            ORDER BY COALESCE(u.admin_verified_at, u.otp_verified_at) DESC
        """)

        rows = rows_to_list(await database.fetch_all(query))
        return rows
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/{log_id}/grant-access")
async def grant_access(log_id: str, admin=Depends(get_current_admin)):
    try:
        log_entry = row_to_dict(await database.fetch_one(
            verification_logs.select().where(verification_logs.c.id == log_id)
        ))
        if not log_entry:
            raise HTTPException(status_code=404, detail="Verification log entry not found")

        await database.execute(
            users.update()
            .where(users.c.id == log_entry["voter_id"])
            .values(is_approved=True)
        )
        return {"success": True, "message": "Access granted for this voter."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
