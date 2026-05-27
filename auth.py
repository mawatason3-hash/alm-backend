from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import uuid
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import database
from models import users
import sqlalchemy as sa

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

if SECRET_KEY == "fallback-secret":
    print("[WARNING] SECRET_KEY is not set; auth tokens will be signed with a fallback secret.")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    if not isinstance(password, str):
        raise ValueError("Password must be a string")
    password = password.strip()
    if len(password) > 72:
        raise ValueError("Password cannot be longer than 72 characters")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if not isinstance(plain, str):
        return False
    return pwd_context.verify(plain.strip(), hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    query = users.select().where(users.c.id == user_uuid)
    user = await database.fetch_one(query)
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(
    current_user = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
