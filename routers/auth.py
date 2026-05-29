from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
import traceback
import uuid
from auth import create_access_token, hash_password, verify_password
from upload_helper import upload_image

router = APIRouter()

# Pydantic schemas
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
async def register(
    full_name: str = Form(...),
    email: EmailStr = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    photo: UploadFile = File(...)
):
    """
    Register a new member with photo upload
    """
    try:
        # Check if email already exists
        existing_email = await database.fetch_one(
            users.select().where(users.c.email == email)
        )
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Save photo
        photo_url = None
        if photo:
            file_bytes = await photo.read()
            photo_url = upload_image(
                file_bytes=file_bytes,
                original_filename=photo.filename,
                folder="voters"
            )

        # Hash password
        password_hash = hash_password(password)

        # Create new user
        user_id = uuid.uuid4()
        query = users.insert().values(
            id=user_id,
            full_name=full_name,
            email=email,
            phone=phone,
            member_id=None,
            password_hash=password_hash,
            role="member",
            is_approved=False,
            photo_url=photo_url,
        )
        await database.execute(query)

        # Log registration
        audit_query = audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=user_id,
            action="MEMBER_REGISTERED",
            metadata={"email": email}
        )
        await database.execute(audit_query)

        return {
            "success": True,
            "message": "Registration submitted! Admin will review and approve your account.",
            "user_id": str(user_id),
            "photo_url": photo_url
        }

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Registration failed due to an internal server error."
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
                "full_name": user["full_name"],
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
