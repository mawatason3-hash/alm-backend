from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import support_requests, users
from schemas import SupportRequestCreate
from auth import get_current_user, get_current_admin
import uuid
import sqlalchemy as sa

router = APIRouter()

@router.post("/requests")
async def submit_support_request(
    body: SupportRequestCreate,
    current_user=Depends(get_current_user)
):
    try:
        request_id = uuid.uuid4()
        await database.execute(
            support_requests.insert().values(
                id=request_id,
                user_id=current_user["id"],
                subject=body.subject,
                message=body.message,
                status="open",
            )
        )
        return {"success": True, "id": str(request_id), "message": "Support request submitted."}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/requests")
async def list_support_requests(admin=Depends(get_current_admin)):
    try:
        query = sa.text("""
            SELECT sr.id, sr.user_id, sr.subject, sr.message, sr.status, sr.created_at, sr.updated_at,
                   u.full_name AS user_full_name, u.email AS user_email
            FROM support_requests sr
            LEFT JOIN users u ON u.id = sr.user_id
            ORDER BY sr.created_at DESC
        """)
        result = await database.fetch_all(query)
        return [dict(r) for r in result]
    except Exception as e:
        raise HTTPException(500, str(e))

@router.patch("/requests/{request_id}")
async def update_support_request_status(
    request_id: str,
    status: str,
    admin=Depends(get_current_admin)
):
    if status not in {"open", "resolved", "closed"}:
        raise HTTPException(400, "Invalid status value")
    try:
        await database.execute(
            support_requests.update()
            .where(support_requests.c.id == request_id)
            .values(status=status)
        )
        return {"success": True, "status": status}
    except Exception as e:
        raise HTTPException(500, str(e))
