from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=200)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=3, max_length=30)  # manager | employee (future-proof)

    # Optional
    is_active: bool = True


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None


class TokenPayload(BaseModel):
    user_id: int
    username: str
    role: str
    exp: Optional[int] = None

