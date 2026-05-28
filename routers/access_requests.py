from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import access_requests
from schemas import AccessRequestCreate, AccessRequestResponse, AccessRequestUpdate
from auth import get_current_user, get_current_admin
import uuid
import sqlalchemy as sa

router = APIRouter()

@router.post("/")
async def create_access_request(body: AccessRequestCreate, current_user=Depends(get_current_user)):
    try:
        request_id = uuid.uuid4()
        await database.execute(
            access_requests.insert().values(
                id=request_id,
                voter_id=current_user["id"],
                voter_name=body.voter_name or current_user["full_name"],
                voter_email=body.voter_email or current_user["email"],
                message=body.message,
                status="pending",
                denial_reason=None,
            )
        )
        return {
            "success": True,
            "id": str(request_id),
            "message": "Access request submitted successfully.",
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/", response_model=list[AccessRequestResponse])
async def list_access_requests(admin=Depends(get_current_admin)):
    try:
        result = await database.fetch_all(
            sa.select(access_requests).order_by(access_requests.c.created_at.desc())
        )
        return [dict(r) for r in result]
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/status")
async def get_access_request_status(voter_id: str | None = None, current_user=Depends(get_current_user)):
    try:
        if voter_id:
            if str(current_user["id"]) != voter_id and current_user["role"] != "admin":
                raise HTTPException(403, "Access denied")
            query = access_requests.select().where(access_requests.c.voter_id == voter_id)
        else:
            query = access_requests.select().where(access_requests.c.voter_id == current_user["id"])

        query = query.order_by(access_requests.c.created_at.desc()).limit(1)
        request = await database.fetch_one(query)
        if not request:
            raise HTTPException(404, "No access request found")
        return dict(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/my-status")
async def get_current_user_access_request_status(current_user=Depends(get_current_user)):
    try:
        query = access_requests.select().where(access_requests.c.voter_id == current_user["id"]).order_by(access_requests.c.created_at.desc()).limit(1)
        request = await database.fetch_one(query)
        if not request:
            raise HTTPException(404, "No access request found")
        return dict(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.patch("/{request_id}")
async def update_access_request(request_id: str, body: AccessRequestUpdate, admin=Depends(get_current_admin)):
    if body.status not in {"approved", "denied", "pending"}:
        raise HTTPException(400, "Invalid status value")
    if body.status == "denied" and not body.reason:
        raise HTTPException(400, "A denial reason is required when denying a request")
    try:
        update_values = {
            "status": body.status,
            "updated_at": sa.func.now(),
        }
        if body.reason:
            update_values["denial_reason"] = body.reason
        await database.execute(
            access_requests.update()
            .where(access_requests.c.id == request_id)
            .values(**update_values)
        )
        return {"success": True, "status": body.status}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/pending-count")
async def pending_access_requests_count(admin=Depends(get_current_admin)):
    try:
        count = await database.fetch_one(
            sa.select(sa.func.count()).select_from(access_requests).where(access_requests.c.status == "pending")
        )
        return {"pending_count": int(count[0] or 0)}
    except Exception as e:
        raise HTTPException(500, str(e))
