import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
import pyodbc
from fastapi import HTTPException, status

from backend.models.auth_models import LoginResponse, RegisterRequest, TokenPayload, UserPublic


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("Missing env var: JWT_SECRET_KEY")
    return secret


def _jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _jwt_exp_minutes() -> int:
    v = os.getenv("JWT_EXPIRE_MINUTES", "60")
    try:
        return int(v)
    except ValueError:
        return 60


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_user_public(row) -> UserPublic:
    # pyodbc returns tuple-like row.
    # Column names may vary; map using attributes when present.
    def _get(name: str, idx: int):
        try:
            return getattr(row, name)
        except Exception:
            return row[idx]

    return UserPublic(
        id=int(_get("id", 0)),
        username=str(_get("username", 1)),
        password=str(_get("password", 2)) if False else "",  # ignored; UserPublic has no password
        email=_get("email", 3),
        full_name=_get("full_name", 4),
        role=str(_get("role", 5)),
        is_active=bool(_get("is_active", 6)),
        created_at=_get("created_at", 7),
    )


def _fetch_user_by_username(conn: pyodbc.Connection, username: str) -> Optional[pyodbc.Row]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password, email, full_name, role, is_active, created_at FROM app_users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def register_user(conn: pyodbc.Connection, req: RegisterRequest) -> UserPublic:
    existing = _fetch_user_by_username(conn, req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    hashed = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt())

    cur = conn.cursor()
    # created_at default to GETUTCDATE()/GETDATE() can exist in schema.
    # We'll still pass created_at as UTC now to be safe.
    cur.execute(
        """
        INSERT INTO app_users (username, password, email, full_name, role, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            req.username,
            hashed.decode("utf-8"),
            req.email,
            req.full_name,
            req.role,
            1 if req.is_active else 0,
            _now_utc(),
        ),
    )

    conn.commit()

    row = _fetch_user_by_username(conn, req.username)
    cur.close()

    if not row:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Build UserPublic without password
    return UserPublic(
        id=int(getattr(row, "id", row[0])),
        username=str(getattr(row, "username", row[1])),
        email=getattr(row, "email", row[3]),
        full_name=getattr(row, "full_name", row[4]),
        role=str(getattr(row, "role", row[5])),
        is_active=bool(getattr(row, "is_active", row[6])),
        created_at=getattr(row, "created_at", row[7])
        if len(row) > 7
        else None,
    )


def authenticate_user(conn: pyodbc.Connection, username: str, password: str) -> LoginResponse:
    row = _fetch_user_by_username(conn, username)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    is_active_val = getattr(row, "is_active", row[6])
    if not bool(is_active_val):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    stored_hash = getattr(row, "password", row[2])
    if stored_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    ok = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_id = int(getattr(row, "id", row[0]))
    user_username = str(getattr(row, "username", row[1]))
    role = str(getattr(row, "role", row[5]))

    exp = _now_utc() + timedelta(minutes=_jwt_exp_minutes())

    payload = {
        "user_id": user_id,
        "username": user_username,
        "role": role,
        "exp": exp,
    }

    token = jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())

    user = UserPublic(
        id=user_id,
        username=user_username,
        email=getattr(row, "email", row[3]),
        full_name=getattr(row, "full_name", row[4]),
        role=role,
        is_active=bool(is_active_val),
        created_at=getattr(row, "created_at", row[7]) if len(row) > 7 else None,
    )

    return LoginResponse(access_token=token, user=user)


def decode_token(token: str) -> TokenPayload:
    try:
        decoded = jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])
        return TokenPayload(
            user_id=int(decoded["user_id"]),
            username=str(decoded["username"]),
            role=str(decoded["role"]),
            exp=decoded.get("exp"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

