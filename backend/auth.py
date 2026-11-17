"""
SaulGPT — Authentication Layer
===============================
JWT token creation/verification + bcrypt password hashing.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt

# Signing secret comes from the JWT_SECRET environment variable (a Space secret in production).
# If it is missing we generate a random one per process: tokens then stop working on restart,
# which is safe (no known default that could be used to forge a login) but logs everyone out.
SECRET_KEY = os.getenv("JWT_SECRET", "").strip()
if len(SECRET_KEY) < 32:
    SECRET_KEY = secrets.token_urlsafe(48)
    print("[Auth] WARNING: JWT_SECRET missing or shorter than 32 chars; using a random per-process secret.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except (JWTError, ValueError, TypeError):  # ValueError: a link token ("link:...") is not a login
        return None


def make_link_token(resource: str, minutes: int = 24 * 60) -> str:
    """Short-lived signed token that lets a plain download link work without a login header."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": f"link:{resource}", "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def link_token_ok(token: str, resource: str) -> bool:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub") == f"link:{resource}"
    except JWTError:
        return False
