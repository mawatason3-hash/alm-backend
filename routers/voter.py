from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from database import database
from models import users, verification_logs
from auth import get_current_user
from upload_helper import upload_image
from rekognition import compare_faces, decode_image_base64, fetch_image_bytes
import uuid

router = APIRouter()

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
    request: Request,
    current_user=Depends(get_current_user),
    selfie: UploadFile | None = File(None)
):
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        if not current_user.get("photo_url"):
            raise HTTPException(
                status_code=400,
                detail="No registration photo found. Please contact admin to update your profile."
            )

        selfie_bytes = None
        filename = None

        if selfie is not None:
            selfie_bytes = await selfie.read()
            filename = selfie.filename or f"{uuid.uuid4()}.jpg"
            if not selfie_bytes:
                raise HTTPException(status_code=400, detail="Uploaded selfie is empty.")
        else:
            payload = await request.json()
            selfie_base64 = payload.get("selfie_base64")
            if not isinstance(selfie_base64, str) or not selfie_base64.strip():
                raise HTTPException(status_code=400, detail="Selfie image data is required.")
            try:
                selfie_bytes = decode_image_base64(selfie_base64)
            except ValueError as exc:
                logger.error(f"Base64 decode error: {exc}")
                raise HTTPException(status_code=400, detail=str(exc))
            filename = f"{uuid.uuid4()}.jpg"

        logger.info(f"User {current_user['id']} attempting verification with {len(selfie_bytes)} bytes")

        try:
            reference_bytes = fetch_image_bytes(current_user["photo_url"])
            logger.info(f"Fetched reference image: {len(reference_bytes)} bytes")
            
            comparison = compare_faces(reference_bytes, selfie_bytes, similarity_threshold=75.0)
            logger.info(f"Comparison result: {comparison.get('match')}, similarity: {comparison.get('similarity')}")
        except HTTPException as he:
            logger.error(f"HTTP Exception during comparison: {he.detail}")
            raise
        except Exception as exc:
            logger.error(f"Comparison error: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Identity verification failed: {exc}")

        selfie_url = upload_image(selfie_bytes, filename, folder="verification-selfies")
        if not selfie_url:
            selfie_url = None

        result = "success" if comparison.get("match") else "failed"
        try:
            await database.execute(
                verification_logs.insert().values(
                    id=uuid.uuid4(),
                    voter_id=current_user["id"],
                    result=result,
                    distance=comparison.get("distance"),
                    selfie_url=selfie_url,
                )
            )
            logger.info(f"Verification log created: {result}")
        except Exception as exc:
            logger.error(f"Unable to save verification record: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unable to save verification record: {exc}")

        return {
            "verified": comparison.get("match"),
            "confidence": comparison.get("similarity"),
            "message": comparison.get("message"),
            "selfie_url": selfie_url,
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in verify_selfie: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verification service error. Please try again.")
