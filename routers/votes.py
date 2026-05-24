from fastapi import APIRouter, Depends, HTTPException
from database import database
from models import votes, positions, election_settings, audit_logs
from schemas import VoteCreate
from auth import get_current_user
import sqlalchemy as sa
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.post("/")
async def cast_vote(body: VoteCreate, current_user=Depends(get_current_user)):
    try:
        # Check election is active
        settings = await database.fetch_one(
            election_settings.select().limit(1)
        )
        if not settings or not settings["is_active"]:
            raise HTTPException(403, "Voting is not currently open")

        # Check not already voted for this position
        existing = await database.fetch_one(
            votes.select().where(
                sa.and_(
                    votes.c.voter_id == current_user["id"],
                    votes.c.position_id == str(body.position_id)
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
            voted_at=datetime.now(timezone.utc),
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
            "voted_positions": [str(r["position_id"]) for r in result],
            "voted_candidates": [str(r["candidate_id"]) for r in result],
            "voted_titles": [str(r["position_title"]) for r in result],
        }
    except Exception as e:
        raise HTTPException(500, str(e))
