"""
routers/auth.py  –  Login using auth_user + user_details tables
Supports: plain text, MD5, and Django PBKDF2-SHA256 passwords.
"""
from fastapi import APIRouter, HTTPException
from database import db_cursor
from models import LoginRequest, SessionUser
from auth import password_ok

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=SessionUser)
def login(body: LoginRequest):
    identity = (body.username or "").strip()
    if not identity or not body.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                u.username,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.is_staff,
                u.is_active,
                u.password,
                ISNULL(ud.password, '') AS details_password,
                ISNULL(ud.is_blocked, 0) AS is_blocked,
                ud.role AS details_role
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            WHERE u.username = ? OR u.email = ?
        """, identity, identity)
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    uid, username, full_name, is_staff, is_active, stored_pw, details_pw, is_blocked, details_role = row

    if not is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    if is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")

    if not (password_ok(body.password, stored_pw) or password_ok(body.password, details_pw)):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Role mapping: 'admin' is the HR user, staff are managers, and the rest are officers
    if username.lower() == "admin":
        role = "hr"
    elif is_staff:
        role = "manager"
    else:
        role = "officer"

    name = (full_name or "").strip() or username

    return SessionUser(id=uid, username=username, name=name, role=role)


@router.post("/logout")
def logout():
    return {"ok": True}
