"""Groq LLM wrapper for LangChain integration."""

import logging
from typing import Optional, List, Any

from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from groq import Groq
from pydantic import Field

from backend.config import settings

logger = logging.getLogger(__name__)

STUDY_SYSTEM_PROMPT = """You are StudyBot, an intelligent AI study assistant. Your role is to help students learn effectively. Follow these guidelines:

1. **Accuracy**: Only provide information supported by the given context. If the context is insufficient, say so clearly.
2. **Clarity**: Explain concepts in a clear, structured manner. Use bullet points, numbered lists, and examples.
3. **Depth**: Adjust your explanation depth based on the question complexity — provide simple answers for simple questions and detailed breakdowns for complex ones.
4. **Study Techniques**: When helpful, suggest study strategies like mnemonics, analogies, or concept maps.
5. **Encouragement**: Maintain a supportive, encouraging tone to motivate learning.
6. **Citations**: When using provided context, reference where the information comes from.

Never fabricate information. If you don't know something, say so honestly."""


class GroqLLM(LLM):
    """Custom LangChain LLM that uses the Groq API."""

    model: str = Field(default=settings.GROQ_MODEL)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=4096)
    system_message: str = Field(default=STUDY_SYSTEM_PROMPT)
    _client: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = Groq(api_key=settings.GROQ_API_KEY)

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        """Call the Groq API with the given prompt."""
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": prompt},
        ]

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=stop or None,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = f"Groq API error: {str(e)}"
            logger.error(error_msg)
            if run_manager:
                run_manager.on_llm_error(e)
            return error_msg


def get_groq_client() -> Groq:
    """Return a raw Groq client for direct API calls (flashcard generation, etc.)."""
    return Groq(api_key=settings.GROQ_API_KEY)
