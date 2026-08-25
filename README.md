# StudyBot — AI-Powered Study Assistant

An intelligent study companion that helps you learn effectively using RAG (Retrieval-Augmented Generation), web research, and AI-generated flashcards.

## Features

- **📚 Document Upload** — Upload PDFs; text is extracted (with OCR), chunked, and embedded into a vector store  
- **💬 Study Chat** — Ask questions about your study materials with 3 modes: Explain, Quiz, Summarize  
- **🌐 Web Research** — Search the web for any topic and add relevant content to your knowledge base  
- **🃏 Flashcards** — Auto-generate flashcard decks from topics or documents; study with flip animations and keyboard shortcuts  
- **📤 Export** — Download flashcard decks as JSON (Anki-compatible)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vanilla HTML/CSS/JS — Dark glassmorphism SPA |
| **Backend** | FastAPI (Python) |
| **LLM** | Groq (Llama 3.3 70B) |
| **Embeddings** | Voyage AI (`voyage-3`) |
| **Vector Store** | MongoDB Atlas with `$vectorSearch` |
| **Scraping** | crawl4ai + DuckDuckGo |
| **PDF Processing** | PyMuPDF + Tesseract OCR |

## Setup

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Configure environment** — edit `.env`:
   ```env
   MONGODB_URI="your-mongodb-atlas-uri"
   VOYAGE_API_KEY="your-voyage-key"
   GROQ_API_KEY="your-groq-key"
   GROQ_MODEL="llama-3.3-70b-versatile"
   ```

3. **MongoDB Atlas Vector Index** — create a `vector_index` on the `text_chunks` collection in the `studybot` database with the field `embedding`.

4. **Run the server**:
   ```bash
   python -m uvicorn backend.main:app --reload --port 8000
   ```

5. **Open** → [http://localhost:8000](http://localhost:8000)

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app & routes
│   ├── config.py            # Settings loader
│   ├── models.py            # Pydantic schemas
│   ├── db/mongodb.py        # MongoDB handler
│   └── services/
│       ├── embedding.py     # PDF → chunks → embeddings
│       ├── retriever.py     # Vector search retriever
│       ├── llm.py           # Groq LLM wrapper
│       ├── rag.py           # RAG chain orchestrator
│       ├── scraper.py       # Web scraping
│       └── flashcards.py    # Flashcard generation
├── frontend/
│   ├── index.html           # SPA shell
│   ├── css/styles.css       # Design system
│   └── js/                  # Modules (api, chat, upload, scraper, flashcards, app)
├── .env                     # Environment variables
└── pyproject.toml           # Dependencies
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in chat |
| `Space` | Flip flashcard |
| `←` / `→` | Navigate flashcards |
