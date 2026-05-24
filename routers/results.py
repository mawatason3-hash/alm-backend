from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer
from database import database
from models import election_settings
from auth import get_current_user, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
import sqlalchemy as sa
from datetime import datetime, timezone

router = APIRouter()
oauth2_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", auto_error=False
)

@router.get("/")
async def get_results(token: str = Depends(oauth2_optional)):
    try:
        is_admin = False
        if token:
            try:
                payload = jwt.decode(
                    token, SECRET_KEY, algorithms=[ALGORITHM]
                )
                is_admin = payload.get("role") == "admin"
            except JWTError:
                pass

        if not is_admin:
            settings = await database.fetch_one(
                election_settings.select().limit(1)
            )
            if settings and settings["voting_end"]:
                voting_end = settings["voting_end"]
                if voting_end.tzinfo is None:
                    voting_end = voting_end.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) < voting_end:
                    raise HTTPException(
                        403, "Results not available until election ends"
                    )

        results_query = sa.text("""
            SELECT
                c.id, c.full_name, c.profile_picture,
                c.running_mate_name, c.running_mate_picture,
                c.party_affiliation,
                t.name as team_name,
                p.display_name as position_name,
                p.title as position_title,
                p.is_combined,
                COUNT(v.id) as vote_count
            FROM candidates c
            JOIN teams t ON t.id = c.team_id
            JOIN positions p ON p.id = c.position_id
            LEFT JOIN votes v ON v.candidate_id = c.id
            GROUP BY c.id, c.full_name, c.profile_picture,
                     c.running_mate_name, c.running_mate_picture,
                     c.party_affiliation, t.name,
                     p.display_name, p.title, p.is_combined
            ORDER BY p.title, vote_count DESC
        """)
        candidates_result = await database.fetch_all(results_query)

        response = {"candidates": [dict(r) for r in candidates_result]}

        if is_admin:
            voters_query = sa.text("""
                SELECT
                    v.id, v.voted_at,
                    u.full_name as voter_name,
                    u.member_id,
                    c.full_name as voted_for,
                    p.display_name as position
                FROM votes v
                JOIN users u ON u.id = v.voter_id
                JOIN candidates c ON c.id = v.candidate_id
                JOIN positions p ON p.id = v.position_id
                ORDER BY v.voted_at DESC
            """)
            voters = await database.fetch_all(voters_query)
            response["voters"] = [dict(r) for r in voters]

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get('/export/csv')
async def export_results_csv(token: str = Depends(oauth2_optional)):
    # Admin-only CSV export. Duplicates combined-ticket rows into President/Vice President
    try:
        if not token:
            raise HTTPException(401, 'Authentication required')
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get('role') != 'admin':
                raise HTTPException(403, 'Admin privileges required')
        except JWTError:
            raise HTTPException(401, 'Invalid token')

        results_query = sa.text("""
            SELECT
                c.id, c.full_name, c.profile_picture,
                c.running_mate_name, c.running_mate_picture,
                c.party_affiliation,
                t.name as team_name,
                p.display_name as position_name,
                p.title as position_title,
                p.is_combined,
                COUNT(v.id) as vote_count
            FROM candidates c
            JOIN teams t ON t.id = c.team_id
            JOIN positions p ON p.id = c.position_id
            LEFT JOIN votes v ON v.candidate_id = c.id
            GROUP BY c.id, c.full_name, c.profile_picture,
                     c.running_mate_name, c.running_mate_picture,
                     c.party_affiliation, t.name,
                     p.display_name, p.title, p.is_combined
            ORDER BY p.title, vote_count DESC
        """)
        candidates_result = await database.fetch_all(results_query)

        # Build CSV lines
        lines = ["Team,Position,Candidate Name,Votes"]
        for r in candidates_result:
            team = r['team_name'] or ''
            is_combined = bool(r.get('is_combined'))
            votes = int(r.get('vote_count') or 0)
            if is_combined:
                # For combined tickets, output President and Vice President rows
                pres_name = r.get('full_name') or ''
                vp_name = r.get('running_mate_name') or ''
                lines.append(f'"{team}","President","{pres_name}",{votes}')
                lines.append(f'"{team}","Vice President","{vp_name}",{votes}')
            else:
                pos = r.get('position_name') or r.get('position_title') or ''
                cand = r.get('full_name') or ''
                lines.append(f'"{team}","{pos}","{cand}",{votes}')

        content = "\n".join(lines)
        return Response(content=content, media_type='text/csv')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
