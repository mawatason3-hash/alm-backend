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
            u.full_name as voter_name,
            u.email as voter_email,
            c.full_name as candidate_name,
            p.title as position,
            t.name as team_name,
            c.running_mate_name as running_mate,
            v.voted_at
        FROM votes v
        JOIN users u ON v.voter_id = u.id
        JOIN candidates c ON v.candidate_id = c.id
        JOIN positions p ON v.position_id = p.id
        JOIN teams t ON v.team_id = t.id
        ORDER BY u.full_name, v.voted_at
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
            u.full_name as voter_name,
            u.email as voter_email,
            p.title as position,
            c.full_name as candidate_name,
            t.name as team_name,
            c.running_mate_name as running_mate,
            v.voted_at
        FROM votes v
        JOIN users u ON v.voter_id = u.id
        JOIN candidates c ON v.candidate_id = c.id
        JOIN positions p ON v.position_id = p.id
        JOIN teams t ON v.team_id = t.id
        ORDER BY u.full_name, v.voted_at
        """
    )
    
    # Group by voter in memory
    voter_map = {}
    for row in rows:
        voter_key = (row['voter_name'], row['voter_email'])
        if voter_key not in voter_map:
            voter_map[voter_key] = {'voter_name': row['voter_name'], 'voter_email': row['voter_email'], 'choices': []}
        voter_map[voter_key]['choices'].append({
            'position': row['position'],
            'candidate_name': row['candidate_name'],
            'team_name': row['team_name'],
            'running_mate': row['running_mate'],
            'voted_at': row['voted_at']
        })
    
    return list(voter_map.values())

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
