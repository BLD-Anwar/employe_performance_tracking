"""
auth.py  –  Password verification utilities for AgriPulse
Supports: plain text, MD5, and Django PBKDF2-SHA256 passwords.
"""
import hashlib
import base64
import hmac


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
