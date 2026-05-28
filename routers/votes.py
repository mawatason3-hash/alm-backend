from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import votes, positions, election_settings, audit_logs, users
from schemas import VoteCreate, FaceDescriptorCreate
from auth import get_current_user
import sqlalchemy as sa
import uuid
from datetime import datetime, timezone
import json

router = APIRouter()
voter_router = APIRouter()

@router.post("/")
async def cast_vote(body: VoteCreate, current_user=Depends(get_current_user)):
    try:
        # Check election is active
        settings = await database.fetch_one(
            election_settings.select().limit(1)
        )
        if not settings or not settings["is_active"]:
            raise HTTPException(403, "Voting is not currently open")

        # Validate requested position and enforce one vote per position title across all teams
        position = await database.fetch_one(
            positions.select().where(positions.c.id == str(body.position_id))
        )
        if not position:
            raise HTTPException(404, "Position not found")

        position_title = position["title"] or position["display_name"]
        if not position_title:
            raise HTTPException(400, "Invalid position")

        existing = await database.fetch_one(
            sa.select(votes.c.id)
            .select_from(votes.join(positions, votes.c.position_id == positions.c.id))
            .where(
                sa.and_(
                    votes.c.voter_id == current_user["id"],
                    positions.c.title == position_title
                )
            )
        )
        if existing:
            raise HTTPException(409, "Already voted for this position")

        vote_id = uuid.uuid4()
        await database.execute(votes.insert().values(
            id=vote_id,
            voter_id=current_user["id"],
            candidate_id=str(body.candidate_id),
            position_id=str(body.position_id),
            team_id=str(body.team_id),
            voted_at=datetime.utcnow(),
        ))

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=current_user["id"],
            action="VOTE_CAST",
            metadata={
                "position_id": str(body.position_id),
                "candidate_id": str(body.candidate_id),
            }
        ))

        return {"success": True, "message": "Vote cast successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/my-votes")
async def get_my_votes(current_user=Depends(get_current_user)):
    try:
        result = await database.fetch_all(
            sa.select(
                votes.c.position_id,
                votes.c.candidate_id,
                positions.c.title.label('position_title')
            )
            .select_from(votes.join(positions, votes.c.position_id == positions.c.id))
            .where(votes.c.voter_id == current_user["id"])
        )

        return {
            "voted_positions": [str(r["position_title"]) for r in result],
            "voted_candidates": [str(r["candidate_id"]) for r in result],
            "voted_titles": [str(r["position_title"]) for r in result],
        }
    except Exception as e:
        raise HTTPException(500, str(e))

async def _get_face_descriptor(current_user=Depends(get_current_user)):
    """
    Get face descriptor or registration photo for facial recognition.
    Returns either:
    - A stored face_descriptor (from face enrollment)
    - A photo_url (registration photo) as fallback
    """
    try:
        user = await database.fetch_one(
            users.select().where(users.c.id == current_user["id"])
        )

        if not user:
            raise HTTPException(404, "User not found")

        response = {}

        # Return stored face descriptor if available
        if user["face_descriptor"]:
            try:
                descriptor = json.loads(user["face_descriptor"])
                response["descriptor"] = descriptor
            except (json.JSONDecodeError, TypeError):
                pass

        # Return photo URL as fallback
        if user["photo_url"] and "descriptor" not in response:
            response["photo_url"] = user["photo_url"]

        if not response:
            raise HTTPException(404, "No face reference available")

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/face-descriptor")
async def get_face_descriptor(current_user=Depends(get_current_user)):
    return await _get_face_descriptor(current_user)

@voter_router.get("/face-descriptor")
async def get_face_descriptor_voter(current_user=Depends(get_current_user)):
    return await _get_face_descriptor(current_user)

async def _save_face_descriptor(
    body: FaceDescriptorCreate,
    current_user=Depends(get_current_user)
):
    """
    Save a face descriptor for the currently authenticated voter.
    """
    try:
        descriptor = body.descriptor
        if not isinstance(descriptor, list) or len(descriptor) == 0:
            raise HTTPException(400, "Invalid face descriptor")

        await database.execute(
            users.update()
            .where(users.c.id == current_user["id"])
            .values(face_descriptor=json.dumps(descriptor))
        )

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=current_user["id"],
            action="FACE_DESCRIPTOR_ENROLLED",
            metadata={"descriptor_length": len(descriptor)}
        ))

        return {"success": True, "message": "Face descriptor saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/face-descriptor")
async def save_face_descriptor(
    body: FaceDescriptorCreate,
    current_user=Depends(get_current_user)
):
    return await _save_face_descriptor(body, current_user)

@voter_router.post("/face-descriptor")
async def save_face_descriptor_voter(
    body: FaceDescriptorCreate,
    current_user=Depends(get_current_user)
):
    return await _save_face_descriptor(body, current_user)
