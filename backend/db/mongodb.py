"""MongoDB connection handler for StudyBot."""

import logging
from datetime import datetime
from typing import List, Optional

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from backend.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """Singleton MongoDB client managing all collections."""

    _instance: Optional["MongoDB"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            self.client = MongoClient(
                settings.MONGODB_URI,
                server_api=ServerApi("1"),
                tls=True,
                tlsAllowInvalidCertificates=True,
            )
            self.db = self.client[settings.DB_NAME]
            self.documents = self.db[settings.DOCUMENTS_COLLECTION]
            self.chunks = self.db[settings.CHUNKS_COLLECTION]
            self.flashcards = self.db[settings.FLASHCARDS_COLLECTION]
            self.users = self.db[settings.USERS_COLLECTION]
            self.quizzes = self.db[settings.QUIZZES_COLLECTION]
            self.chat_sessions = self.db[settings.CHAT_SESSIONS_COLLECTION]

            # Ensure unique email index
            self.users.create_index("email", unique=True)

            self._initialized = True
            logger.info("MongoDB connected successfully.")
        except Exception as e:
            logger.error(f"MongoDB initialization error: {e}")
            raise

    def ping(self) -> bool:
        """Test the MongoDB connection."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False

    # ── Document operations ──────────────────────────────────────

    def store_document(self, filename: str, full_path: str, total_chunks: int) -> str:
        """Store document metadata, return inserted ID as string."""
        doc = {
            "filename": filename,
            "full_path": full_path,
            "total_chunks": total_chunks,
            "processed_date": datetime.now(),
        }
        result = self.documents.insert_one(doc)
        return str(result.inserted_id)

    def list_documents(self) -> list:
        """Return all stored documents."""
        docs = self.documents.find({}, {"_id": 1, "filename": 1, "total_chunks": 1, "processed_date": 1})
        results = []
        for d in docs:
            results.append({
                "id": str(d["_id"]),
                "filename": d["filename"],
                "total_chunks": d.get("total_chunks", 0),
                "processed_date": d.get("processed_date", "").isoformat() if d.get("processed_date") else None,
            })
        return results

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its chunks."""
        from bson import ObjectId

        oid = ObjectId(doc_id)
        self.chunks.delete_many({"document_id": doc_id})
        result = self.documents.delete_one({"_id": oid})
        return result.deleted_count > 0

    # ── Chunk operations ─────────────────────────────────────────

    def store_chunks(self, doc_id: str, chunks: List[str], embeddings: List[List[float]]):
        """Store text chunks with their vector embeddings."""
        chunk_docs = []
        for i, (text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_docs.append({
                "document_id": doc_id,
                "chunk_index": i,
                "text": text,
                "embedding": embedding,
                "created_at": datetime.now(),
            })
        if chunk_docs:
            self.chunks.insert_many(chunk_docs)
            logger.info(f"Stored {len(chunk_docs)} chunks for document {doc_id}")

    # ── Flashcard operations ─────────────────────────────────────

    def store_flashcard_deck(self, title: str, cards: list, source: str = "topic", user_id: str = None) -> str:
        """Store a flashcard deck, return its ID."""
        deck = {
            "title": title,
            "user_id": user_id,
            "cards": cards,
            "source": source,
            "created_at": datetime.now(),
        }
        result = self.flashcards.insert_one(deck)
        return str(result.inserted_id)

    def list_flashcard_decks(self, user_id: str = None) -> list:
        """Return all flashcard decks for a user."""
        query = {"user_id": user_id} if user_id else {}
        decks = self.flashcards.find(query)
        results = []
        for d in decks:
            results.append({
                "id": str(d["_id"]),
                "title": d["title"],
                "card_count": len(d.get("cards", [])),
                "source": d.get("source", ""),
                "created_at": d.get("created_at", "").isoformat() if d.get("created_at") else None,
            })
        return results

    def get_flashcard_deck(self, deck_id: str, user_id: str = None) -> Optional[dict]:
        """Return a full flashcard deck by ID."""
        from bson import ObjectId

        query = {"_id": ObjectId(deck_id)}
        if user_id:
            query["user_id"] = user_id

        deck = self.flashcards.find_one(query)
        if deck:
            return {
                "id": str(deck["_id"]),
                "title": deck["title"],
                "cards": deck.get("cards", []),
                "source": deck.get("source", ""),
                "created_at": deck.get("created_at", "").isoformat() if deck.get("created_at") else None,
            }
        return None

    def delete_flashcard_deck(self, deck_id: str, user_id: str = None) -> bool:
        """Delete a flashcard deck."""
        from bson import ObjectId

        query = {"_id": ObjectId(deck_id)}
        if user_id:
            query["user_id"] = user_id

        result = self.flashcards.delete_one(query)
        return result.deleted_count > 0

    # ── User operations ──────────────────────────────────────────

    def create_user(self, email: str, password_hash: str, name: str) -> str:
        """Create a new user, return inserted ID as string."""
        user = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.now(),
        }
        result = self.users.insert_one(user)
        return str(result.inserted_id)

    def get_user_by_email(self, email: str):
        """Find a user by email."""
        return self.users.find_one({"email": email})

    # ── Chat session operations ──────────────────────────────────

    def store_chat_message(self, user_id: str, role: str, content: str, session_id: str = "default"):
        """Append a chat message for a user."""
        self.chat_sessions.insert_one({
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(),
        })

    def get_chat_history(self, user_id: str, limit: int = 50, session_id: str = "default") -> list:
        """Return chat messages for a user's session."""
        messages = self.chat_sessions.find(
            {"user_id": user_id, "session_id": session_id},
            {"_id": 0, "role": 1, "content": 1},
        ).sort("created_at", 1).limit(limit)
        return list(messages)

    def clear_chat_history(self, user_id: str, session_id: str = None):
        """Delete chat messages. If session_id is provided, delete only that session."""
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        self.chat_sessions.delete_many(query)

    def get_chat_sessions_list(self, user_id: str, limit: int = 20) -> list:
        """Return recent chat sessions grouped for sidebar display."""
        import collections
        messages = self.chat_sessions.find(
            {"user_id": user_id, "role": "user"},
            {"_id": 1, "content": 1, "created_at": 1, "session_id": 1},
        ).sort("created_at", -1)
        
        seen_sessions = set()
        results = []
        for msg in messages:
            sid = msg.get("session_id", "default")
            if sid in seen_sessions:
                continue
            seen_sessions.add(sid)
            
            preview = msg["content"][:60] + ("..." if len(msg["content"]) > 60 else "")
            results.append({
                "id": sid,
                "preview": preview,
                "created_at": msg.get("created_at", "").isoformat() if msg.get("created_at") else None,
            })
            if len(results) >= limit:
                break
        return results

    # ── Quiz operations ──────────────────────────────────────────

    def store_quiz(self, user_id: str, topic: str, review: list, score: int, total: int, comment: str) -> str:
        """Store a completed quiz result."""
        quiz = {
            "user_id": user_id,
            "topic": topic,
            "review": review,
            "score": score,
            "total": total,
            "comment": comment,
            "created_at": datetime.now(),
        }
        result = self.quizzes.insert_one(quiz)
        return str(result.inserted_id)

    def list_quiz_history(self, user_id: str) -> list:
        """Return past quizzes for a user."""
        quizzes = self.quizzes.find(
            {"user_id": user_id},
            {"_id": 1, "topic": 1, "score": 1, "total": 1, "comment": 1, "created_at": 1},
        ).sort("created_at", -1).limit(20)
        results = []
        for q in quizzes:
            results.append({
                "id": str(q["_id"]),
                "topic": q["topic"],
                "score": q["score"],
                "total": q["total"],
                "comment": q["comment"],
                "created_at": q.get("created_at", "").isoformat() if q.get("created_at") else None,
            })
        return results

    def get_quiz_by_id(self, quiz_id: str, user_id: str):
        """Return full quiz details by ID."""
        from bson import ObjectId
        quiz = self.quizzes.find_one({"_id": ObjectId(quiz_id), "user_id": user_id})
        if not quiz:
            return None
        review = quiz.get("review")
        if not review:
            # Fallback for old quizzes format
            questions = quiz.get("questions", [])
            review = []
            for q in questions:
                review.append({
                    "question": q.get("question", ""),
                    "options": q.get("options", []),
                    "correct_answer": q.get("correct"),
                })

        return {
            "id": str(quiz["_id"]),
            "topic": quiz["topic"],
            "review": review,
            "score": quiz["score"],
            "total": quiz["total"],
            "comment": quiz["comment"],
            "created_at": quiz.get("created_at", "").isoformat() if quiz.get("created_at") else None,
        }
