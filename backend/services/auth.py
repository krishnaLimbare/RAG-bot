"""JWT authentication service for StudyBot."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from backend.config import settings
from backend.db.mongodb import MongoDB

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user signup, login, and JWT token management."""

    def __init__(self):
        self.db = MongoDB()

    # ── Password helpers ────────────────────────────────
    @staticmethod
    def hash_password(password: str) -> str:
        pw_bytes = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        pw_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hashed_bytes)

    # ── JWT helpers ─────────────────────────────────────
    @staticmethod
    def create_token(user_id: str, email: str, name: str) -> str:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "exp": expire,
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None

    # ── Business logic ──────────────────────────────────
    def signup(self, email: str, password: str, name: str) -> dict:
        """Create a new user account and return a JWT token."""
        existing = self.db.get_user_by_email(email)
        if existing:
            raise ValueError("An account with this email already exists")

        hashed = self.hash_password(password)
        user_id = self.db.create_user(email, hashed, name)

        token = self.create_token(user_id, email, name)
        return {"token": token, "user_name": name, "user_email": email}

    def login(self, email: str, password: str) -> dict:
        """Authenticate a user and return a JWT token."""
        user = self.db.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")

        if not self.verify_password(password, user["password_hash"]):
            raise ValueError("Invalid email or password")

        token = self.create_token(str(user["_id"]), user["email"], user["name"])
        return {"token": token, "user_name": user["name"], "user_email": user["email"]}

    def get_user_from_token(self, token: str) -> Optional[dict]:
        """Decode a JWT token and return user info."""
        payload = self.decode_token(token)
        if not payload:
            return None
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
        }
