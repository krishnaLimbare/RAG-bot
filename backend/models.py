"""Pydantic models for API request/response validation."""

from typing import List, Optional
from pydantic import BaseModel


# ── Auth ─────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_name: str
    user_email: str


# ── Chat ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    mode: str = "explain"
    session_id: Optional[str] = None  # explain | quiz | summarize


class SourceDoc(BaseModel):
    text: str
    document_id: str
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDoc] = []


# ── Documents ────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    id: str
    filename: str
    total_chunks: int
    processed_date: Optional[str] = None


# ── Scraper ──────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    topic: str
    max_results: int = 3


class ScrapeResult(BaseModel):
    url: str
    title: str
    content: str
    full_length: int = 0


class ScrapeResponse(BaseModel):
    success: bool
    topic: str = ""
    results: List[ScrapeResult] = []
    error: str = ""


class AddToKnowledgeBaseRequest(BaseModel):
    content: str
    source_name: str


# ── Flashcards ───────────────────────────────────────────────────

class FlashcardGenerateRequest(BaseModel):
    topic: str = ""
    text: str = ""
    title: str = ""
    count: int = 10


class FlashcardItem(BaseModel):
    question: str
    answer: str


class FlashcardDeck(BaseModel):
    id: str = ""
    title: str
    cards: List[FlashcardItem] = []
    card_count: int = 0
    source: str = ""
    created_at: Optional[str] = None


class FlashcardDeckSummary(BaseModel):
    id: str
    title: str
    card_count: int
    source: str
    created_at: Optional[str] = None


# ── Quiz ─────────────────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    topic: str
    count: int = 10


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: List[int]  # index of selected option for each question


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct: int  # index of correct option


class QuizResult(BaseModel):
    quiz_id: str
    score: int
    total: int
    percentage: float
    comment: str
    review: List[dict]  # question + user_answer + correct_answer + is_correct
