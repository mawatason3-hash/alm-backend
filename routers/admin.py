from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import users, votes, audit_logs
from schemas import StatsResponse
from auth import get_current_admin
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/stats", response_model=StatsResponse)
async def get_stats(admin=Depends(get_current_admin)):
    try:
        total = await database.fetch_one(
            sa.select(sa.func.count()).select_from(users)
            .where(users.c.role == "member")
        )
        approved = await database.fetch_one(
            sa.select(sa.func.count()).select_from(users)
            .where(
                sa.and_(users.c.role == "member",
                        users.c.is_approved == True)
            )
        )
        total_votes = await database.fetch_one(
            sa.select(sa.func.count()).select_from(votes)
        )
        distinct_voters = await database.fetch_one(
            sa.select(sa.func.count(sa.distinct(votes.c.voter_id))).select_from(votes)
        )
        pending = await database.fetch_one(
            sa.select(sa.func.count()).select_from(users)
            .where(
                sa.and_(users.c.role == "member",
                        users.c.is_approved == False)
            )
        )

        approved_count = approved[0]
        votes_count = total_votes[0]
        unique_voter_count = distinct_voters[0]
        turnout = round(
            (unique_voter_count / approved_count * 100) 
            if approved_count > 0 else 0, 1
        )

        return {
            "total_members": total[0],
            "approved_members": approved_count,
            "total_votes": votes_count,
            "pending_approvals": pending[0],
            "turnout": turnout,
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/reset-votes")
async def reset_votes(admin=Depends(get_current_admin)):
    try:
        await database.execute(votes.delete())
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="VOTES_RESET",
            metadata={}
        ))
        return {"success": True, "message": "All votes reset"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/audit-log")
async def get_audit_log(
    page: int = 1,
    limit: int = 20,
    admin=Depends(get_current_admin)
):
    try:
        offset = (page - 1) * limit
        query = sa.text(f"""
            SELECT al.id, al.action, al.metadata, al.created_at,
                   u.full_name as actor_name, u.email as actor_email
            FROM audit_logs al
            LEFT JOIN users u ON u.id = al.actor_id
            ORDER BY al.created_at DESC
            LIMIT {limit} OFFSET {offset}
        """)
        logs = await database.fetch_all(query)
        total = await database.fetch_one(
            sa.select(sa.func.count()).select_from(audit_logs)
        )
        return {
            "logs": [dict(r) for r in logs],
            "total": total[0],
            "page": page,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/seed")
async def seed_admin():
    try:
        from auth import hash_password
        existing = await database.fetch_one(
            users.select().where(users.c.email == "admin@alm.org")
        )
        if existing:
            return {"message": "Admin already exists"}

        await database.execute(users.insert().values(
            id=uuid.uuid4(),
            full_name="ALM Admin",
            email="admin@alm.org",
            phone="+250000000000",
            member_id="ALM-ADMIN-001",
            password_hash=hash_password("Admin@2024"),
            role="admin",
            is_approved=True,
        ))
        return {"message": "Admin created: admin@alm.org / Admin@2024"}
    except Exception as e:
        raise HTTPException(500, str(e))
