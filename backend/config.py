"""Centralized configuration loader for StudyBot."""

import os
import secrets
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # JWT settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", secrets.token_hex(32))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # MongoDB collection names
    DB_NAME: str = "studybot"
    DOCUMENTS_COLLECTION: str = "documents"
    CHUNKS_COLLECTION: str = "text_chunks"
    FLASHCARDS_COLLECTION: str = "flashcards"
    USERS_COLLECTION: str = "users"
    QUIZZES_COLLECTION: str = "quizzes"
    CHAT_SESSIONS_COLLECTION: str = "chat_sessions"

    # Embedding settings
    EMBEDDING_MODEL: str = "voyage-3"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Retriever settings
    RETRIEVER_K: int = 5

    def validate(self):
        """Check that required settings are present."""
        missing = []
        if not self.MONGODB_URI:
            missing.append("MONGODB_URI")
        if not self.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if not self.VOYAGE_API_KEY:
            missing.append("VOYAGE_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
