from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import positions, teams, candidates, audit_logs
from schemas import PositionCreate, PositionUpdate
from auth import get_current_admin
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/")
async def get_positions():
    try:
        query = sa.text("""
            SELECT p.id, p.title, p.display_name, p.is_combined,
                   p.team_id, t.name as team_name,
                   COUNT(c.id) as candidate_count
            FROM positions p
            LEFT JOIN teams t ON t.id = p.team_id
            LEFT JOIN candidates c ON c.position_id = p.id
            GROUP BY p.id, p.title, p.display_name, p.is_combined, p.team_id, t.name
            ORDER BY t.name, p.title
        """)
        result = await database.fetch_all(query)
        return [dict(r) for r in result]
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/")
async def create_position(body: PositionCreate, admin=Depends(get_current_admin)):
    try:
        existing = await database.fetch_one(
            positions.select().where(
                sa.and_(
                    positions.c.team_id == body.team_id,
                    positions.c.title == body.title
                )
            )
        )
        if existing:
            raise HTTPException(400, "A position with that title already exists for this team")

        position_id = uuid.uuid4()
        await database.execute(positions.insert().values(
            id=position_id,
            title=body.title,
            display_name=body.display_name,
            is_combined=body.is_combined,
            team_id=body.team_id,
        ))
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="POSITION_CREATED",
            metadata={"position_title": body.title, "team_id": body.team_id}
        ))
        return {"success": True, "id": str(position_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.put("/{position_id}")
async def update_position(position_id: str, body: PositionUpdate, admin=Depends(get_current_admin)):
    try:
        await database.execute(
            positions.update()
            .where(positions.c.id == position_id)
            .values(
                title=body.title,
                display_name=body.display_name,
                is_combined=body.is_combined,
            )
        )
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="POSITION_UPDATED",
            metadata={"position_id": position_id}
        ))
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/{position_id}")
async def delete_position(position_id: str, admin=Depends(get_current_admin)):
    try:
        count = await database.fetch_one(
            sa.select(sa.func.count()).select_from(candidates)
            .where(candidates.c.position_id == position_id)
        )
        if count[0] > 0:
            raise HTTPException(400, "Remove candidates assigned to this position first")
        await database.execute(positions.delete().where(positions.c.id == position_id))
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="POSITION_DELETED",
            metadata={"position_id": position_id}
        ))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
