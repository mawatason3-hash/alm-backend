from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from database import database
from models import teams, positions, candidates, audit_logs
from schemas import TeamCreate, TeamUpdate
from auth import get_current_admin
from upload_helper import save_upload_file
import sqlalchemy as sa
import uuid

router = APIRouter()

@router.get("/")
async def get_teams():
    try:
        query = sa.text("""
            SELECT t.id, t.name, t.description, t.created_at,
                   COUNT(c.id) as candidate_count
            FROM teams t
            LEFT JOIN candidates c ON c.team_id = t.id
            GROUP BY t.id, t.name, t.description, t.created_at
            ORDER BY t.created_at ASC
        """)
        result = await database.fetch_all(query)
        return [dict(r) for r in result]
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/")
async def create_team(body: TeamCreate, admin=Depends(get_current_admin)):
    try:
        existing = await database.fetch_one(
            teams.select().where(teams.c.name == body.name)
        )
        if existing:
            raise HTTPException(400, "Team name already exists")

        team_id = uuid.uuid4()
        await database.execute(teams.insert().values(
            id=team_id,
            name=body.name,
            description=body.description,
        ))

        # Create 3 positions for this team automatically
        position_data = [
            {
                "id": uuid.uuid4(),
                "title": "president_vp",
                "display_name": "President & Vice President",
                "is_combined": True,
                "team_id": team_id,
            },
            {
                "id": uuid.uuid4(),
                "title": "general_secretary",
                "display_name": "General Secretary",
                "is_combined": False,
                "team_id": team_id,
            },
            {
                "id": uuid.uuid4(),
                "title": "financial_secretary",
                "display_name": "Financial Secretary",
                "is_combined": False,
                "team_id": team_id,
            },
        ]
        await database.execute_many(
            positions.insert(), position_data
        )

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="TEAM_CREATED",
            metadata={"team_name": body.name}
        ))

        return {"id": str(team_id), "name": body.name,
                "description": body.description, "candidate_count": 0}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/full")
async def create_full_team(
    name: str = Form(...),
    description: str = Form(None),
    president_name: str = Form(...),
    vp_name: str = Form(...),
    secretary_name: str = Form(...),
    financial_secretary_name: str = Form(...),
    president_image: UploadFile | None = File(None),
    vp_image: UploadFile | None = File(None),
    secretary_image: UploadFile | None = File(None),
    financial_secretary_image: UploadFile | None = File(None),
    president_image_url: str | None = Form(None),
    vp_image_url: str | None = Form(None),
    secretary_image_url: str | None = Form(None),
    financial_secretary_image_url: str | None = Form(None),
    admin=Depends(get_current_admin),
):
    try:
        # create team
        existing = await database.fetch_one(
            teams.select().where(teams.c.name == name)
        )
        if existing:
            raise HTTPException(400, "Team name already exists")

        team_id = uuid.uuid4()
        await database.execute(teams.insert().values(
            id=team_id,
            name=name,
            description=description,
        ))

        # create positions
        position_data = [
            {
                "id": uuid.uuid4(),
                "title": "president_vp",
                "display_name": "President & Vice President",
                "is_combined": True,
                "team_id": team_id,
            },
            {
                "id": uuid.uuid4(),
                "title": "general_secretary",
                "display_name": "General Secretary",
                "is_combined": False,
                "team_id": team_id,
            },
            {
                "id": uuid.uuid4(),
                "title": "financial_secretary",
                "display_name": "Financial Secretary",
                "is_combined": False,
                "team_id": team_id,
            },
        ]
        await database.execute_many(positions.insert(), position_data)

        # upload images (if provided)
        pres_url = None
        vp_url = None
        sec_url = None
        fin_url = None
        if president_image:
            pres_url = await save_upload_file(president_image)
        elif president_image_url:
            pres_url = president_image_url

        if vp_image:
            vp_url = await save_upload_file(vp_image)
        elif vp_image_url:
            vp_url = vp_image_url

        if secretary_image:
            sec_url = await save_upload_file(secretary_image)
        elif secretary_image_url:
            sec_url = secretary_image_url

        if financial_secretary_image:
            fin_url = await save_upload_file(financial_secretary_image)
        elif financial_secretary_image_url:
            fin_url = financial_secretary_image_url

        # insert candidates
        # find the position ids we just created
        pos_rows = await database.fetch_all(
            positions.select().where(positions.c.team_id == team_id)
        )
        pos_map = {p['title']: p['id'] for p in pos_rows}

        # President + VP as one candidate row in president_vp
        pres_cand_id = uuid.uuid4()
        await database.execute(candidates.insert().values(
            id=pres_cand_id,
            team_id=team_id,
            position_id=pos_map.get('president_vp'),
            full_name=president_name,
            profile_picture=pres_url,
            running_mate_name=vp_name,
            running_mate_picture=vp_url,
        ))

        # Secretary
        await database.execute(candidates.insert().values(
            id=uuid.uuid4(),
            team_id=team_id,
            position_id=pos_map.get('general_secretary'),
            full_name=secretary_name,
            profile_picture=sec_url,
        ))

        # Financial Secretary
        await database.execute(candidates.insert().values(
            id=uuid.uuid4(),
            team_id=team_id,
            position_id=pos_map.get('financial_secretary'),
            full_name=financial_secretary_name,
            profile_picture=fin_url,
        ))

        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin['id'],
            action='TEAM_CREATED_FULL',
            metadata={'team_name': name}
        ))

        return {"id": str(team_id), "name": name, "description": description}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.put("/{team_id}")
async def update_team(
    team_id: str,
    body: TeamUpdate,
    admin=Depends(get_current_admin)
):
    try:
        await database.execute(
            teams.update()
            .where(teams.c.id == team_id)
            .values(name=body.name, description=body.description)
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    admin=Depends(get_current_admin)
):
    try:
        count = await database.fetch_one(
            sa.select(sa.func.count())
            .where(candidates.c.team_id == team_id)
        )
        if count[0] > 0:
            raise HTTPException(
                400, "Remove all candidates from this team first"
            )
        await database.execute(
            teams.delete().where(teams.c.id == team_id)
        )
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=admin["id"],
            action="TEAM_DELETED",
            metadata={"team_id": team_id}
        ))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
