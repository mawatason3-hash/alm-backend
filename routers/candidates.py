from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from database import database
from models import candidates, audit_logs
from auth import get_current_admin
from upload_helper import save_upload_file
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/")
async def get_candidates():
    try:
        query = sa.text("""
            SELECT c.*,
                   t.name as team_name,
                   p.display_name as position_name,
                   p.title as position_title,
                   p.is_combined
            FROM candidates c
            JOIN teams t ON t.id = c.team_id
            JOIN positions p ON p.id = c.position_id
            ORDER BY t.name, p.title
        """)
        result = await database.fetch_all(query)
        return [dict(r) for r in result]
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/")
async def add_candidate(
    team_id: str = Form(...),
    position_id: str = Form(...),
    full_name: str = Form(...),
    party_affiliation: str = Form(""),
    previous_leadership: str = Form(""),
    letter_of_intent: str = Form(""),
    bio: str = Form(""),
    running_mate_name: str = Form(""),
    running_mate_party: str = Form(""),
    running_mate_previous_leadership: str = Form(""),
    running_mate_letter_of_intent: str = Form(""),
    running_mate_bio: str = Form(""),
    profile_picture: Optional[UploadFile] = File(None),
    running_mate_picture: Optional[UploadFile] = File(None),
    profile_picture_url: Optional[str] = Form(None),
    running_mate_picture_url: Optional[str] = Form(None),
    admin=Depends(get_current_admin)
):
    try:
        profile_url = None
        if profile_picture:
            profile_url = await save_upload_file(profile_picture)
        elif profile_picture_url:
            profile_url = profile_picture_url

        mate_url = None
        if running_mate_picture:
            mate_url = await save_upload_file(running_mate_picture)
        elif running_mate_picture_url:
            mate_url = running_mate_picture_url

        candidate_id = uuid.uuid4()
        await database.execute(candidates.insert().values(
            id=candidate_id,
            team_id=team_id,
            position_id=position_id,
            full_name=full_name,
            profile_picture=profile_url,
            party_affiliation=party_affiliation or None,
            previous_leadership=previous_leadership or None,
            letter_of_intent=letter_of_intent or None,
            bio=bio or None,
            running_mate_name=running_mate_name or None,
            running_mate_picture=mate_url,
            running_mate_party=running_mate_party or None,
            running_mate_previous_leadership=running_mate_previous_leadership or None,
            running_mate_letter_of_intent=running_mate_letter_of_intent or None,
            running_mate_bio=running_mate_bio or None,
        ))

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="CANDIDATE_ADDED",
            metadata={"candidate_name": full_name}
        ))

        return {"success": True, "candidate_id": str(candidate_id)}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: str,
    admin=Depends(get_current_admin)
):
    try:
        await database.execute(
            candidates.delete()
            .where(candidates.c.id == candidate_id)
        )
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="CANDIDATE_DELETED",
            metadata={"candidate_id": candidate_id}
        ))
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))
