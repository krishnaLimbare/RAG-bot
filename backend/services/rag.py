"""RAG chain orchestrator for study-focused Q&A.

Uses a direct approach instead of the deprecated ConversationalRetrievalChain.
Manually retrieves documents and calls the Groq LLM with context.
"""

import logging
from typing import Dict, Any, List

from backend.db.mongodb import MongoDB
from backend.services.retriever import MongoDBRetriever
from backend.services.llm import GroqLLM

logger = logging.getLogger(__name__)

STUDY_QA_TEMPLATE = """You are a study assistant. Use the following context extracted from the student's study materials to answer their question.

If the context doesn't contain enough information, say so clearly and suggest what topics the student might want to upload or research.

When answering:
- Structure your response clearly with headers and bullet points
- Provide examples when helpful
- If the question is about a concept, explain it step by step
- Reference which parts of the context support your answer

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Helpful Study Answer:"""


class StudyRAG:
    """Manages the RAG pipeline: retriever → LLM with persistent conversation history."""

    def __init__(self):
        self.retriever = MongoDBRetriever()
        self.llm = GroqLLM()
        self.db = MongoDB()

    def query(self, question: str, user_id: str = "", session_id: str = "default") -> Dict[str, Any]:
        """Process a study question and return the answer with sources."""
        try:
            # Retrieve relevant documents
            docs = self.retriever.invoke(question)

            # Format context
            context_text = "\n\n".join(
                [f"[Source {i + 1}]:\n{doc.page_content}" for i, doc in enumerate(docs)]
            )

            # Get recent chat history
            chat_history_text = "No previous history."
            if user_id:
                history = self.db.get_chat_history(user_id, limit=5, session_id=session_id)
                if history:
                    chat_history_text = "\n".join(
                        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in history]
                    )

            # Generate answer
            prompt = STUDY_QA_TEMPLATE.format(
                context=context_text,
                chat_history=chat_history_text,
                question=question,
            )
            response = self.llm.invoke(prompt)

            # Store in DB if user is provided
            if user_id:
                self.db.store_chat_message(user_id, "user", question, session_id=session_id)
                self.db.store_chat_message(user_id, "assistant", response, session_id=session_id)

            # Build sources list
            sources = []
            for doc in docs:
                text = doc.page_content
                sources.append({
                    "text": text[:300] + "..." if len(text) > 300 else text,
                    "document_id": doc.metadata.get("document_id", ""),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                })

            return {
                "answer": response,
                "sources": sources,
            }
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            raise

    def clear_memory(self, user_id: str = ""):
        """Clear conversation history for a user."""
        if user_id:
            self.db.clear_chat_history(user_id)

    def get_history(self, user_id: str = "") -> List[dict]:
        """Return conversation history for a user."""
        if user_id:
            return self.db.get_chat_history(user_id)
        return []
