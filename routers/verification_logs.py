from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import verification_logs, users
from schemas import VerificationLogCreate
from auth import get_current_user, get_current_admin
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
                selfie_url=body.selfie_image_url,
            )
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/")
async def list_verification_logs(admin=Depends(get_current_admin)):
    try:
        query = sa.select(
            verification_logs.c.id,
            verification_logs.c.voter_id,
            users.c.full_name.label("voter_name"),
            users.c.email.label("voter_email"),
            users.c.photo_url.label("registration_photo_url"),
            verification_logs.c.result,
            verification_logs.c.distance,
            verification_logs.c.selfie_url,
            verification_logs.c.created_at,
        ).select_from(
            verification_logs.join(users, verification_logs.c.voter_id == users.c.id)
        ).order_by(verification_logs.c.created_at.desc())

        rows = await database.fetch_all(query)
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/{log_id}/grant-access")
async def grant_access(log_id: str, admin=Depends(get_current_admin)):
    try:
        log_entry = await database.fetch_one(
            verification_logs.select().where(verification_logs.c.id == log_id)
        )
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
