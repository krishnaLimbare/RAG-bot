"""MongoDB vector search retriever for LangChain integration."""

import logging
from typing import List, Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from backend.config import settings
from backend.db.mongodb import MongoDB
from backend.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class MongoDBRetriever(BaseRetriever):
    """Custom LangChain retriever using MongoDB Atlas $vectorSearch."""

    k: int = Field(default=settings.RETRIEVER_K, description="Number of documents to retrieve")
    _db: Any = None
    _embedding_service: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self._db = MongoDB()
        self._embedding_service = EmbeddingService()

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve relevant document chunks via vector similarity search."""
        query_embedding = self._embedding_service.embed_query(query)

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": self.k * 10,
                    "limit": self.k,
                }
            }
        ]

        results = self._db.chunks.aggregate(pipeline)
        documents = []
        for result in results:
            doc = Document(
                page_content=result["text"],
                metadata={
                    "document_id": result.get("document_id", ""),
                    "chunk_index": result.get("chunk_index", 0),
                },
            )
            documents.append(doc)

        logger.info(f"Retrieved {len(documents)} chunks for query")
        return documents

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Async wrapper (delegates to sync)."""
        return self._get_relevant_documents(query)
