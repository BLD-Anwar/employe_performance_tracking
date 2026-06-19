"""
routers/settings.py  –  Account settings
Tables: dbo.auth_user, dbo.user_details
"""
import hashlib
from fastapi import APIRouter, HTTPException
from database import db_cursor
from models import ProfileUpdate, PasswordChange
from auth import password_ok, md5_hash

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/profile/{user_id}")
def get_profile(user_id: int):
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.username,
                u.email,
                u.is_staff
            FROM dbo.auth_user u
            WHERE u.id = ?
        """, user_id)
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": row[0],
        "name": (row[1] or "").strip(),
        "username": row[2],
        "email": row[3],
        "role": "manager" if row[4] else "officer",
    }


@router.put("/profile/{user_id}")
def update_profile(user_id: int, body: ProfileUpdate):
    # Split name into first/last
    parts = (body.name or "").strip().split(" ", 1)
    first = parts[0]
    last  = parts[1] if len(parts) > 1 else ""

    with db_cursor() as cur:
        cur.execute(
            "UPDATE dbo.auth_user SET first_name=?, last_name=?, email=? WHERE id=?",
            first, last, body.email, user_id
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@router.post("/change-password/{user_id}")
def change_password(user_id: int, body: PasswordChange):
    with db_cursor() as cur:
        cur.execute("SELECT password FROM dbo.auth_user WHERE id=?", user_id)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        stored = row[0]
        if not password_ok(body.current_password, stored):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Store new password as MD5 hash
        new_hash = md5_hash(body.new_password)
        cur.execute("UPDATE dbo.auth_user SET password=? WHERE id=?", new_hash, user_id)

    return {"ok": True}
