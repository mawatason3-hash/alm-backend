from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import election_settings, users, audit_logs
from schemas import ElectionSettingsSchema
from auth import get_current_admin
from datetime import datetime
from typing import Optional
import uuid

router = APIRouter()


def normalize_datetime(value: Optional[datetime]):
    if value is None:
        return None
    return value.replace(tzinfo=None)

@router.get("/settings")
async def get_settings():
    try:
        row = await database.fetch_one(
            election_settings.select().limit(1)
        )
        if not row:
            admin = await database.fetch_one(
                users.select().where(users.c.role == "admin").limit(1)
            )
            settings_id = uuid.uuid4()
            await database.execute(election_settings.insert().values(
                id=settings_id,
                election_name="ALM General Elections",
                is_active=False,
                allow_registration=True,
                created_by=admin["id"] if admin else None,
            ))
            row = await database.fetch_one(
                election_settings.select().limit(1)
            )
        return dict(row)
    except Exception as e:
        raise HTTPException(500, str(e))

@router.patch("/settings")
async def update_settings(
    body: ElectionSettingsSchema,
    admin=Depends(get_current_admin)
):
    try:
        existing = await database.fetch_one(
            election_settings.select().limit(1)
        )
        if existing:
            await database.execute(
                election_settings.update()
                .where(election_settings.c.id == existing["id"])
                .values(
                    election_name=body.election_name,
                    is_active=body.is_active,
                    voting_start=normalize_datetime(body.voting_start),
                    voting_end=normalize_datetime(body.voting_end),
                    allow_registration=body.allow_registration,
                )
            )
        else:
            await database.execute(election_settings.insert().values(
                id=uuid.uuid4(),
                election_name=body.election_name,
                is_active=body.is_active,
                voting_start=normalize_datetime(body.voting_start),
                voting_end=normalize_datetime(body.voting_end),
                allow_registration=body.allow_registration,
                created_by=admin["id"],
            ))

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="SETTINGS_UPDATED",
            metadata={"is_active": body.is_active}
        ))

        return {"success": True, "message": "Settings saved"}
    except Exception as e:
        raise HTTPException(500, str(e))
