"""
auth.py  –  Password verification and JWT utilities for AgriPulse
Supports: plain text, MD5, and Django PBKDF2-SHA256 passwords.
Also provides JWT token generation and endpoint verification.
"""
import hashlib
import base64
import hmac
import jwt
import os
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "agripulse_secret_key_2026")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def md5_hash(plain: str) -> str:
    """Compute MD5 hex digest of a plain password."""
    return hashlib.md5(plain.encode()).hexdigest()


def verify_django_pbkdf2(password: str, stored: str) -> bool:
    """Verify Django-style pbkdf2_sha256$iterations$salt$hash passwords."""
    if not stored or not stored.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, iterations_str, salt, hash_value = stored.split("$", 3)
        iterations = int(iterations_str)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            iterations,
        )
        encoded_hash = base64.b64encode(password_hash).decode("ascii")
        return hmac.compare_digest(encoded_hash, hash_value)
    except Exception:
        return False


def password_ok(plain: str, stored: str | None) -> bool:
    """Check a plain-text password against a stored hash (plain, MD5, or PBKDF2)."""
    if not stored:
        return False
    # Plain text match
    if plain == stored:
        return True
    # MD5 match
    if stored == md5_hash(plain):
        return True
    # Django PBKDF2-SHA256 match
    if verify_django_pbkdf2(plain, stored):
        return True
    return False


def create_access_token(user_id: int, role: str) -> str:
    """Generate a JWT token for a specific user ID and role."""
    payload = {
        "user_id": user_id,
        "role": role
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), token: Optional[str] = None):
    """FastAPI dependency to verify bearer token."""
    if not credentials and not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    actual_token = credentials.credentials if credentials else token
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired authorization token")


def require_role(*allowed_roles):
    def checker(payload: dict = Depends(verify_token)):
        if payload.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return payload
    return checker

