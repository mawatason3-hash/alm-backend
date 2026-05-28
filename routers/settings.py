from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import settings
from schemas import AdminContactInfo, AdminContactUpdate
from auth import get_current_admin
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/admin-contact", response_model=AdminContactInfo)
async def get_admin_contact():
    try:
        query = sa.select(settings.c.key, settings.c.value).where(
            settings.c.key.in_(["admin_phone", "admin_whatsapp", "admin_hours"])
        )
        rows = await database.fetch_all(query)
        result = {"admin_phone": "", "admin_whatsapp": "", "admin_hours": ""}
        for row in rows:
            result[row["key"]] = row["value"] or ""
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@router.patch("/admin-contact")
async def update_admin_contact(body: AdminContactUpdate, admin=Depends(get_current_admin)):
    try:
        items = [
            ("admin_phone", body.admin_phone or ""),
            ("admin_whatsapp", body.admin_whatsapp or ""),
            ("admin_hours", body.admin_hours or ""),
        ]
        for key, value in items:
            await database.execute(
                sa.text(
                    "INSERT INTO settings (id, key, value, updated_at) "
                    "VALUES (:id, :key, :value, NOW()) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()"
                ),
                {"id": str(uuid.uuid4()), "key": key, "value": value}
            )
        return {"success": True, "message": "Admin contact information saved."}
    except Exception as e:
        raise HTTPException(500, str(e))
