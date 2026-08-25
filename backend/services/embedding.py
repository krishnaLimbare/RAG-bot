"""PDF processing, text chunking, and embedding service."""

import logging
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from langchain_text_splitters import CharacterTextSplitter
from langchain_voyageai import VoyageAIEmbeddings

from backend.config import settings
from backend.db.mongodb import MongoDB

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Handles PDF text extraction, chunking, embedding, and storage."""

    def __init__(self):
        self.db = MongoDB()
        self.embeddings_model = VoyageAIEmbeddings(
            voyage_api_key=settings.VOYAGE_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
        self.text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )

    # ── PDF Extraction ──────────────────────────────────────────

    def _extract_page(self, pdf_path: str, page_num: int, ocr: bool = True) -> str:
        """Extract text from a single PDF page (direct + OCR)."""
        parts = []
        try:
            with fitz.open(pdf_path) as doc:
                page = doc[page_num]
                text = page.get_text("text", sort=True, flags=fitz.TEXT_PRESERVE_WHITESPACE)
                if text.strip():
                    parts.append(text)

                if ocr:
                    zoom = 2
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(img, lang="eng", config="--oem 3 --psm 6")
                    if ocr_text.strip():
                        parts.append(ocr_text)
        except Exception as e:
            logger.error(f"Error extracting page {page_num}: {e}")
        return "\n".join(parts)

    def extract_pdf_text(self, pdf_path: str, ocr: bool = True) -> str:
        """Extract full text from a PDF sequentially."""
        try:
            results = []
            with fitz.open(pdf_path) as doc:
                for i in range(len(doc)):
                    results.append(self._extract_page(pdf_path, i, ocr))
            return "\n".join(filter(None, results))
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    # ── Chunking ────────────────────────────────────────────────

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        return self.text_splitter.split_text(text)

    # ── Embedding ───────────────────────────────────────────────

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of texts."""
        return self.embeddings_model.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Generate a vector embedding for a single query string."""
        return self.embeddings_model.embed_query(query)

    # ── Full pipeline ───────────────────────────────────────────

    def process_pdf(self, pdf_path: str, filename: str) -> dict:
        """Full pipeline: extract → chunk → embed → store. Returns document info."""
        logger.info(f"Processing PDF: {filename}")

        raw_text = self.extract_pdf_text(pdf_path)
        if not raw_text.strip():
            raise ValueError(f"No text could be extracted from {filename}")

        chunks = self.chunk_text(raw_text)
        logger.info(f"Created {len(chunks)} chunks from {filename}")

        embeddings = self.embed_texts(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings for {filename}")

        doc_id = self.db.store_document(filename, pdf_path, len(chunks))
        self.db.store_chunks(doc_id, chunks, embeddings)

        return {"document_id": doc_id, "filename": filename, "total_chunks": len(chunks)}

    def process_text(self, text: str, source_name: str) -> dict:
        """Process raw text (e.g. from web scraping) into embeddings."""
        chunks = self.chunk_text(text)
        if not chunks:
            raise ValueError("No text to process")

        embeddings = self.embed_texts(chunks)
        doc_id = self.db.store_document(source_name, f"web:{source_name}", len(chunks))
        self.db.store_chunks(doc_id, chunks, embeddings)

        return {"document_id": doc_id, "source": source_name, "total_chunks": len(chunks)}
