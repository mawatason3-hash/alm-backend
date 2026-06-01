from fastapi import APIRouter, Depends, HTTPException
from database import database
from auth import get_current_user
from utils import row_to_dict

router = APIRouter()

@router.get("/admin/vote-choices")
async def get_all_vote_choices(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = await database.fetch_all(
        """
        SELECT
            voter_name,
            voter_email,
            candidate_name,
            position,
            team_name,
            running_mate,
            voted_at
        FROM vote_choices
        ORDER BY voter_name, voted_at
        """
    )
    return [dict(row) for row in rows]

@router.get("/admin/vote-choices/by-voter")
async def get_vote_choices_by_voter(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = await database.fetch_all(
        """
        SELECT
            voter_name,
            voter_email,
            json_agg(json_build_object(
                'position', position,
                'candidate_name', candidate_name,
                'team_name', team_name,
                'running_mate', running_mate,
                'voted_at', voted_at
            ) ORDER BY voted_at) AS choices
        FROM vote_choices
        GROUP BY voter_name, voter_email
        ORDER BY voter_name
        """
    )
    return [dict(row) for row in rows]

@router.get("/voter/my-votes")
async def get_my_vote_choices(current_user=Depends(get_current_user)):
    voter_id = str(current_user.get("id"))

    rows = await database.fetch_all(
        """
        SELECT
            candidate_name,
            position,
            team_name,
            running_mate,
            voted_at
        FROM vote_choices
        WHERE voter_id = :voter_id
        ORDER BY voted_at
        """,
        {"voter_id": voter_id}
    )

    return [dict(row) for row in rows]
