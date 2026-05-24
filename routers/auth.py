from fastapi import APIRouter, HTTPException, status, Depends
from database import database
from models import users, audit_logs, reset_tokens
from schemas import UserRegister, UserLogin, TokenResponse, ForgotPassword, ResetPassword
from auth import hash_password, verify_password, create_access_token, get_current_user
import sqlalchemy as sa
import uuid
import secrets
from datetime import datetime, timedelta, timezone

router = APIRouter()

@router.post("/register")
async def register(body: UserRegister):
    try:
        # Check email unique
        existing_email = await database.fetch_one(
            users.select().where(users.c.email == body.email)
        )
        if existing_email:
            raise HTTPException(400, "Email already registered")

        # Check member ID unique
        existing_member = await database.fetch_one(
            users.select().where(users.c.member_id == body.member_id)
        )
        if existing_member:
            raise HTTPException(400, "Member ID already registered")

        hashed = hash_password(body.password)

        # Insert user
        user_id = uuid.uuid4()
        await database.execute(users.insert().values(
            id=user_id,
            full_name=body.full_name,
            email=body.email,
            phone=body.phone,
            member_id=body.member_id,
            password_hash=hashed,
            role="member",
            is_approved=False,
        ))

        # Log
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=user_id,
            action="MEMBER_REGISTERED",
            metadata={
                "email": body.email,
                "phone": body.phone,
                "member_id": body.member_id,
            }
        ))

        return {"message": "Registration submitted. Await admin approval."}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Registration failed: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    try:
        user = await database.fetch_one(
            users.select().where(users.c.email == body.email)
        )

        if not user:
            raise HTTPException(401, "Invalid email or password")

        if not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Invalid email or password")

        if not user["is_approved"] and user["role"] != "admin":
            raise HTTPException(403, "Account pending admin approval")

        token = create_access_token({"sub": str(user["id"]), "role": user["role"]})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": dict(user)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login failed: {str(e)}")


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return dict(current_user)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPassword):
    try:
        user = await database.fetch_one(
            users.select().where(users.c.email == body.email)
        )
        # Always return same message for security
        if user:
            token = secrets.token_hex(32)
            expires = datetime.now(timezone.utc) + timedelta(hours=1)
            await database.execute(
                reset_tokens.delete().where(
                    reset_tokens.c.user_id == user["id"]
                )
            )
            await database.execute(reset_tokens.insert().values(
                id=uuid.uuid4(),
                user_id=user["id"],
                token=token,
                expires_at=expires,
                used=False,
            ))
            # TODO: Send email with reset link
            # reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
        return {"message": "If email exists a reset link has been sent."}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/reset-password")
async def reset_password(body: ResetPassword):
    try:
        token_row = await database.fetch_one(
            reset_tokens.select().where(
                sa.and_(
                    reset_tokens.c.token == body.token,
                    reset_tokens.c.used == False,
                    reset_tokens.c.expires_at > datetime.now(timezone.utc)
                )
            )
        )
        if not token_row:
            raise HTTPException(400, "Invalid or expired reset link")

        if not isinstance(body.password, str):
            raise HTTPException(400, "Password must be a string")
        if len(body.password.encode('utf-8')) > 72:
            raise HTTPException(400, "Password cannot be longer than 72 bytes")
        if body.password.startswith(("$2a$", "$2b$", "$2y$")) and len(body.password) >= 60:
            raise HTTPException(400, "Password appears to already be hashed; submit plain-text password")

        hashed = hash_password(body.password)
        await database.execute(
            users.update()
            .where(users.c.id == token_row["user_id"])
            .values(password_hash=hashed)
        )
        await database.execute(
            reset_tokens.update()
            .where(reset_tokens.c.id == token_row["id"])
            .values(used=True)
        )
        await database.execute(audit_logs.insert().values(
            id=uuid.uuid4(),
            actor_id=token_row["user_id"],
            action="PASSWORD_RESET",
            metadata={}
        ))
        return {"message": "Password reset successful"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
