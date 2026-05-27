from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
import uuid
from auth import create_access_token, hash_password, verify_password

router = APIRouter()

# Pydantic schemas
class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    member_id: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

# Import database connection
from database import database
from models import users, audit_logs


@router.post("/register", status_code=201)
async def register(body: UserRegister):
    """
    Register a new member
    """
    try:
        # Check if email already exists
        existing_email = await database.fetch_one(
            users.select().where(users.c.email == body.email)
        )
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Check if member_id already exists
        existing_member_id = await database.fetch_one(
            users.select().where(users.c.member_id == body.member_id)
        )
        if existing_member_id:
            raise HTTPException(
                status_code=400,
                detail="Member ID already registered"
            )

        # Hash password
        password_hash = hash_password(body.password)

        # Create new user
        user_id = uuid.uuid4()
        query = users.insert().values(
            id=user_id,
            full_name=body.full_name,
            email=body.email,
            phone=body.phone,
            member_id=body.member_id,
            password_hash=password_hash,
            role="member",
            is_approved=False,
        )
        await database.execute(query)

        # Log registration
        audit_query = audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=user_id,
            action="MEMBER_REGISTERED",
            metadata={"email": body.email}
        )
        await database.execute(audit_query)

        return {
            "success": True,
            "message": "Registration submitted. Await admin approval.",
            "user_id": str(user_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    """
    Login and get access token
    """
    try:
        # Find user by email
        user = await database.fetch_one(
            users.select().where(users.c.email == body.email)
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(body.password, user["password_hash"]):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # Check if approved (except for admin)
        if not user["is_approved"] and user["role"] != "admin":
            raise HTTPException(
                status_code=403,
                detail="Account pending admin approval"
            )

        # Create access token
        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "role": user["role"]
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user["id"]),
                "name": user["full_name"],
                "email": user["email"],
                "role": user["role"],
                "is_approved": user["is_approved"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "auth"}
