from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import database
from models import users, verification_logs
from auth import get_current_user
from upload_helper import upload_image
from rekognition import compare_faces, decode_image_base64
import uuid

router = APIRouter()


class VerifySelfieRequest(BaseModel):
    selfie_base64: str

@router.get("/profile")
async def get_voter_profile(current_user=Depends(get_current_user)):
    user = await database.fetch_one(users.select().where(users.c.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "photo_url": user["photo_url"],
        "role": user["role"],
        "is_approved": user["is_approved"],
        "created_at": str(user["created_at"])
    }

@router.post("/verify-selfie")
async def verify_selfie(
    body: VerifySelfieRequest,
    current_user=Depends(get_current_user)
):
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        user_data = dict(current_user)
        user_id = user_data.get('id') or user_data.get('sub')
        print("=== VERIFY SELFIE START ===")
        print(f"User ID: {user_id}")

        user = await database.fetch_one(
            users.select().where(users.c.id == user_id)
        )
        print(f"User found: {user is not None}")

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Voter not found"
            )

        photo_url = user.get("photo_url")
        print(f"Photo URL: {photo_url}")

        if not photo_url:
            raise HTTPException(
                status_code=400,
                detail="No registration photo found. Contact admin to update your profile."
            )

        selfie_base64 = body.selfie_base64
        print(f"Selfie base64 length: {len(selfie_base64 or '')}")

        if not isinstance(selfie_base64, str) or not selfie_base64.strip():
            raise HTTPException(status_code=400, detail="Selfie image data is required.")

        try:
            selfie_bytes = decode_image_base64(selfie_base64)
        except ValueError as exc:
            logger.error(f"Base64 decode error: {exc}")
            raise HTTPException(status_code=400, detail=str(exc))

        filename = f"{uuid.uuid4()}.jpg"

        print("Calling AWS Rekognition...")
        result = compare_faces(
            source_image_url=photo_url,
            target_image_base64=selfie_base64,
            similarity_threshold=75.0
        )
        print(f"AWS Result: {result}")

        status = "success" if result.get("match") else "failed"
        try:
            await database.execute(
                verification_logs.insert().values(
                    id=uuid.uuid4(),
                    voter_id=str(user_id),
                    voter_name=user.get("full_name", ""),
                    result=status,
                    confidence=result.get("confidence") or 0,
                    created_at=datetime.utcnow(),
                )
            )
        except Exception as log_err:
            print(f"Log error (non-fatal): {log_err}")

        return {
            "verified": result.get("match"),
            "confidence": result.get("confidence", 0),
            "message": result.get("message", ""),
            "selfie_url": None,
        }

    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        print(f"=== VERIFY SELFIE ERROR: {str(exc)} ===")
        raise HTTPException(
            status_code=500,
            detail=f"Verification service error: {str(exc)}"
        )
