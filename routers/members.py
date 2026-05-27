from fastapi import APIRouter, Depends, HTTPException, Body
from database import database
from models import users, votes, audit_logs, reset_tokens, election_settings
from auth import get_current_admin, hash_password
from schemas import TeamCreate, TeamUpdate, AdminCreateMember, AdminUpdateMember
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/")
async def get_members(admin=Depends(get_current_admin)):
    try:
        query = sa.text("""
            SELECT u.id, u.full_name, u.email, u.phone, 
                   u.member_id, u.role, u.is_approved, u.created_at,
                   COUNT(DISTINCT v.position_id) as positions_voted
            FROM users u
            LEFT JOIN votes v ON v.voter_id = u.id
            WHERE u.role = 'member'
            GROUP BY u.id, u.full_name, u.email, u.phone,
                     u.member_id, u.role, u.is_approved, u.created_at
            ORDER BY u.created_at DESC
        """)
        result = await database.fetch_all(query)
        return [dict(r) for r in result]
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/")
async def create_member(body: AdminCreateMember, admin=Depends(get_current_admin)):
    try:
        existing = await database.fetch_one(
            users.select().where(users.c.email == body.email)
        )
        if existing:
            raise HTTPException(400, "Email already exists")

        pwd = body.password or 'ChangeMe123'
        hashed = hash_password(pwd)

        new_id = uuid.uuid4()
        await database.execute(users.insert().values(
            id=new_id,
            full_name=body.full_name,
            email=body.email,
            phone=body.phone,
            member_id=body.member_id,
            password_hash=hashed,
            role='member',
            is_approved=bool(body.password) or True,
        ))

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin['id'],
            action='MEMBER_CREATED',
            metadata={'member_id': str(new_id), 'email': body.email}
        ))

        return {"success": True, "id": str(new_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/{member_id}")
async def update_member(member_id: str, body: AdminUpdateMember = Body(...), admin=Depends(get_current_admin)):
    try:
        update_data = {}
        if body.full_name is not None:
            update_data['full_name'] = body.full_name
        if body.email is not None:
            update_data['email'] = body.email
        if body.phone is not None:
            update_data['phone'] = body.phone
        if body.member_id is not None:
            update_data['member_id'] = body.member_id
        if body.is_approved is not None:
            update_data['is_approved'] = body.is_approved

        if not update_data:
            raise HTTPException(400, 'No fields to update')

        await database.execute(
            users.update().where(users.c.id == member_id).values(**update_data)
        )

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin['id'],
            action='MEMBER_UPDATED',
            metadata={'member_id': member_id}
        ))

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.patch("/{member_id}/approve")
async def approve_member(
    member_id: str,
    admin=Depends(get_current_admin)
):
    try:
        await database.execute(
            users.update()
            .where(users.c.id == member_id)
            .values(is_approved=True)
        )
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="MEMBER_APPROVED",
            metadata={"approved_id": member_id}
        ))
        return {"success": True, "member_id": member_id}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/{member_id}")
async def delete_member(
    member_id: str,
    admin=Depends(get_current_admin)
):
    try:
        # Remove child records that reference this user to avoid FK constraint errors
        # Delete votes cast by the user
        await database.execute(votes.delete().where(votes.c.voter_id == member_id))
        # Delete any reset tokens for the user
        try:
            await database.execute(reset_tokens.delete().where(reset_tokens.c.user_id == member_id))
        except Exception:
            # reset_tokens table may not exist in older schemas; ignore if absent
            pass

        # Remove audit log entries authored by the user
        await database.execute(audit_logs.delete().where(audit_logs.c.actor_id == member_id))

        # Nullify created_by on election_settings if it references this user
        try:
            await database.execute(
                election_settings.update().where(election_settings.c.created_by == member_id).values(created_by=None)
            )
        except Exception:
            # election_settings may not reference created_by in some installs; ignore errors
            pass

        # Finally delete the user row
        await database.execute(
            users.delete().where(
                sa.and_(users.c.id == member_id, users.c.role == "member")
            )
        )
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="MEMBER_DELETED",
            metadata={"deleted_id": member_id}
        ))
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))
