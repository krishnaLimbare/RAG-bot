"""FastAPI application — StudyBot backend."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from backend.models import (
    ChatRequest,
    ChatResponse,
    ScrapeRequest,
    ScrapeResponse,
    AddToKnowledgeBaseRequest,
    FlashcardGenerateRequest,
    SignupRequest,
    LoginRequest,
    AuthResponse,
    QuizGenerateRequest,
    QuizSubmitRequest,
)
from backend.services.rag import StudyRAG
from backend.services.embedding import EmbeddingService
from backend.services.scraper import WebScraper
from backend.services.flashcards import FlashcardService
from backend.services.auth import AuthService
from backend.services.quiz import QuizService
from backend.db.mongodb import MongoDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────

app = FastAPI(title="StudyBot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Service singletons (lazy-initialized) ────────────────────────

_rag: StudyRAG | None = None
_embedding: EmbeddingService | None = None
_scraper: WebScraper | None = None
_flashcards: FlashcardService | None = None
_auth: AuthService | None = None
_quiz: QuizService | None = None
_db: MongoDB | None = None


def get_rag() -> StudyRAG:
    global _rag
    if _rag is None:
        _rag = StudyRAG()
    return _rag


def get_embedding() -> EmbeddingService:
    global _embedding
    if _embedding is None:
        _embedding = EmbeddingService()
    return _embedding


def get_scraper() -> WebScraper:
    global _scraper
    if _scraper is None:
        _scraper = WebScraper()
    return _scraper


def get_flashcards() -> FlashcardService:
    global _flashcards
    if _flashcards is None:
        _flashcards = FlashcardService()
    return _flashcards


def get_auth() -> AuthService:
    global _auth
    if _auth is None:
        _auth = AuthService()
    return _auth


def get_quiz() -> QuizService:
    global _quiz
    if _quiz is None:
        _quiz = QuizService()
    return _quiz


def get_db() -> MongoDB:
    global _db
    if _db is None:
        _db = MongoDB()
    return _db


# ── Auth dependency ──────────────────────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract user info from JWT token in Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    auth = get_auth()
    user = auth.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "StudyBot"}


# ── Auth Routes ──────────────────────────────────────────────────

@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    try:
        auth = get_auth()
        result = auth.signup(req.email, req.password, req.name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        auth = get_auth()
        result = auth.login(req.email, req.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"user_name": user["name"], "user_email": user["email"]}


# ── Chat ─────────────────────────────────────────────────────────

@app.get("/api/chat/history")
async def get_chat_history_sidebar(user: dict = Depends(get_current_user)):
    try:
        db = get_db()
        return db.get_chat_sessions_list(user["user_id"])
    except Exception as e:
        logger.error(f"Chat history fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/thread")
async def get_chat_thread(session_id: str = "default", user: dict = Depends(get_current_user)):
    try:
        db = get_db()
        return db.get_chat_history(user["user_id"], limit=50, session_id=session_id)
    except Exception as e:
        logger.error(f"Chat thread fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        rag = get_rag()

        # Modify system behaviour based on mode
        mode_prefix = ""
        if req.mode == "quiz":
            mode_prefix = "Act as a quiz master. Ask follow-up questions to test understanding. "
        elif req.mode == "summarize":
            mode_prefix = "Provide a concise summary. Use bullet points. "

        question = mode_prefix + req.message if mode_prefix else req.message
        
        # Pass the session_id so the LLM keeps its conversation contexts separate
        result = rag.query(
            question, 
            user_id=user["user_id"], 
            session_id=req.session_id or "default"
        )

        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/clear")
async def clear_chat(user: dict = Depends(get_current_user)):
    try:
        rag = get_rag()
        rag.clear_memory(user_id=user["user_id"])
        return {"status": "ok", "message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/session/{session_id}")
async def delete_chat_session(session_id: str, user: dict = Depends(get_current_user)):
    try:
        db = get_db()
        db.clear_chat_history(user["user_id"], session_id=session_id)
        return {"status": "ok", "message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Chat session delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# ── Document Upload ──────────────────────────────────────────────

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        embedding = get_embedding()
        result = embedding.process_pdf(tmp_path, file.filename)

        # Clean up temp file
        os.unlink(tmp_path)

        return result
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    try:
        db = get_db()
        return db.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    try:
        db = get_db()
        success = db.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "ok", "message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Web Scraping ─────────────────────────────────────────────────

@app.post("/api/scrape")
async def scrape(req: ScrapeRequest, user: dict = Depends(get_current_user)):
    try:
        scraper = get_scraper()
        result = await scraper.search_and_scrape(req.topic, req.max_results)
        return result
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape/add-to-kb")
async def add_to_knowledge_base(req: AddToKnowledgeBaseRequest, user: dict = Depends(get_current_user)):
    try:
        scraper = get_scraper()
        result = scraper.add_to_knowledge_base(req.content, req.source_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Flashcards ───────────────────────────────────────────────────

@app.post("/api/flashcards/generate")
async def generate_flashcards(req: FlashcardGenerateRequest, user: dict = Depends(get_current_user)):
    try:
        fc = get_flashcards()
        if req.text:
            result = fc.generate_from_text(
                text=req.text,
                title=req.title or "Untitled Deck",
                count=req.count,
                source="document",
                user_id=user["user_id"]
            )
        elif req.topic:
            result = fc.generate_from_topic(topic=req.topic, count=req.count, user_id=user["user_id"])
        else:
            raise HTTPException(status_code=400, detail="Provide either 'topic' or 'text'")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flashcard generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flashcards")
async def list_flashcard_decks(user: dict = Depends(get_current_user)):
    try:
        fc = get_flashcards()
        return fc.list_decks(user_id=user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flashcards/{deck_id}")
async def get_flashcard_deck(deck_id: str, user: dict = Depends(get_current_user)):
    try:
        fc = get_flashcards()
        deck = fc.get_deck(deck_id, user_id=user["user_id"])
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        return deck
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/flashcards/{deck_id}")
async def delete_flashcard_deck(deck_id: str, user: dict = Depends(get_current_user)):
    try:
        fc = get_flashcards()
        success = fc.delete_deck(deck_id, user_id=user["user_id"])
        if not success:
            raise HTTPException(status_code=404, detail="Deck not found or you don't have permission")
        return {"status": "ok", "message": "Deck deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flashcards/{deck_id}/export")
async def export_flashcard_deck(deck_id: str, user: dict = Depends(get_current_user)):
    try:
        fc = get_flashcards()
        data = fc.export_deck(deck_id)
        if not data:
            raise HTTPException(status_code=404, detail="Deck not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Quiz ─────────────────────────────────────────────────────────

@app.post("/api/quiz/generate")
async def generate_quiz(req: QuizGenerateRequest, user: dict = Depends(get_current_user)):
    try:
        quiz = get_quiz()
        result = quiz.generate(req.topic, req.count)
        return result
    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quiz/submit")
async def submit_quiz(req: QuizSubmitRequest, user: dict = Depends(get_current_user)):
    try:
        quiz = get_quiz()
        result = quiz.submit(req.quiz_id, req.answers, user_id=user["user_id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Quiz submit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quiz/history")
async def quiz_history(user: dict = Depends(get_current_user)):
    try:
        quiz = get_quiz()
        return quiz.get_history(user["user_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quiz/{quiz_id}")
async def get_quiz_detail(quiz_id: str, user: dict = Depends(get_current_user)):
    try:
        quiz = get_quiz()
        return quiz.get_quiz_detail(quiz_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Quiz detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve frontend ───────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.get("/login")
async def serve_login():
    return FileResponse(str(FRONTEND_DIR / "login.html"))


@app.get("/app")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/login")
