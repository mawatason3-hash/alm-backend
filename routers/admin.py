from fastapi import APIRouter, Depends, HTTPException, status
from database import database
from models import users, votes, audit_logs
from auth import get_current_admin
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/stats")
async def get_stats(admin=Depends(get_current_admin)):
    try:
        total_row = await database.fetch_one(
            sa.select(sa.func.count()).select_from(users).where(users.c.role == "member")
        )
        approved_row = await database.fetch_one(
            sa.select(sa.func.count()).select_from(users).where(
                sa.and_(users.c.role == "member", users.c.is_approved == True)
            )
        )
        total_votes_row = await database.fetch_one(
            sa.select(sa.func.count()).select_from(votes)
        )
        pending_row = await database.fetch_one(
            sa.select(sa.func.count()).select_from(users).where(
                sa.and_(users.c.role == "member", users.c.is_approved == False)
            )
        )

        total_members = int(total_row[0]) if total_row and total_row[0] is not None else 0
        approved_members = int(approved_row[0]) if approved_row and approved_row[0] is not None else 0
        total_votes = int(total_votes_row[0]) if total_votes_row and total_votes_row[0] is not None else 0
        pending_approvals = int(pending_row[0]) if pending_row and pending_row[0] is not None else 0
        turnout_value = round((total_votes / approved_members * 100) if approved_members > 0 else 0.0, 1)

        return {
            "success": True,
            "data": {
                "total_members": total_members,
                "approved_users": approved_members,
                "votes_cast": total_votes,
                "pending_approvals": pending_approvals,
                "turnout": f"{turnout_value}%",
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin stats failed: {str(e)}",
        )

@router.post("/reset-votes")
async def reset_votes(admin=Depends(get_current_admin)):
    try:
        await database.execute(votes.delete())
        await database.execute(
            audit_logs.insert().values(
                id=uuid.uuid4(),
                actor_id=admin["id"],
                action="VOTES_RESET",
                metadata={},
            )
        )
        return {"success": True, "message": "All votes reset"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vote reset failed: {str(e)}",
        )

@router.get("/audit-log")
async def get_audit_log(
    page: int = 1,
    limit: int = 20,
    admin=Depends(get_current_admin),
):
    try:
        offset = (page - 1) * limit
        query = sa.text(
            """
            SELECT al.id, al.action, al.metadata, al.created_at,
                   u.full_name AS actor_name, u.email AS actor_email
            FROM audit_logs al
            LEFT JOIN users u ON u.id = al.actor_id
            ORDER BY al.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        logs = await database.fetch_all(query.bindparams(limit=limit, offset=offset))
        total = await database.fetch_one(
            sa.select(sa.func.count()).select_from(audit_logs)
        )
        return {
            "logs": [dict(r) for r in logs],
            "total": int(total[0]) if total and total[0] is not None else 0,
            "page": page,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit log fetch failed: {str(e)}",
        )

@router.post("/seed")
async def seed_admin():
    try:
        from auth import hash_password

        existing = await database.fetch_one(
            users.select().where(users.c.email == "admin@alm.org")
        )
        if existing:
            return {"message": "Admin already exists"}

        await database.execute(
            users.insert().values(
                id=uuid.uuid4(),
                full_name="ALM Admin",
                email="admin@alm.org",
                phone="+250000000000",
                member_id="ALM-ADMIN-001",
                password_hash=hash_password("Admin@2024"),
                role="admin",
                is_approved=True,
            )
        )
        return {"message": "Admin created: admin@alm.org / Admin@2024"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin seed failed: {str(e)}",
        )
