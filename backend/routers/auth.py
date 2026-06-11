from fastapi import APIRouter, Depends
import pyodbc

from backend.database import get_db

from backend.models.auth_models import LoginRequest, LoginResponse, RegisterRequest, TokenPayload, UserPublic
from backend.services.auth_service import authenticate_user, register_user
from backend.middleware.jwt_auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic)
def register(
    req: RegisterRequest,
    conn: pyodbc.Connection = Depends(get_db),
):
    return register_user(conn, req)


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    conn: pyodbc.Connection = Depends(get_db),
):
    return authenticate_user(conn, req.username, req.password)


@router.get("/me", response_model=TokenPayload)
def me(current_user: TokenPayload = Depends(get_current_user)):
    return current_user

