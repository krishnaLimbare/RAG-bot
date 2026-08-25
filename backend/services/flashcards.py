"""Flashcard generation service using Groq LLM."""

import json
import logging
from typing import List, Optional

from backend.config import settings
from backend.db.mongodb import MongoDB
from backend.services.llm import get_groq_client

logger = logging.getLogger(__name__)

FLASHCARD_PROMPT = """You are a study assistant that creates high-quality flashcards for effective learning.

Given the following study material, create {count} flashcards. Each flashcard should have:
- A clear, specific question on the front
- A concise but complete answer on the back
- Focus on key concepts, definitions, relationships, and important details

Return your response as a valid JSON array of objects, each with "question" and "answer" keys.
Example format:
[
  {{"question": "What is photosynthesis?", "answer": "Photosynthesis is the process by which plants convert sunlight, water, and CO2 into glucose and oxygen using chlorophyll."}},
  {{"question": "What are the two stages of photosynthesis?", "answer": "The two stages are the light-dependent reactions (in thylakoids) and the Calvin cycle / light-independent reactions (in stroma)."}}
]

Return ONLY the JSON array, no additional text or markdown formatting.

Study Material:
{content}"""


class FlashcardService:
    """Generates and manages flashcard decks."""

    def __init__(self):
        self.db = MongoDB()
        self.client = get_groq_client()

    def generate_from_text(self, text: str, title: str, count: int = 10, source: str = "document", user_id: str = None) -> dict:
        """Generate flashcards from raw text using Groq."""
        # Truncate text if too long for context window
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated for processing...]"

        prompt = FLASHCARD_PROMPT.format(count=count, content=text)

        try:
            response = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a JSON-generating study assistant. Always return valid JSON arrays."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.5,
            )

            raw = response.choices[0].message.content.strip()

            # Try to extract JSON from the response
            cards = self._parse_cards(raw)
            if not cards:
                raise ValueError("Failed to parse flashcards from LLM response")

            # Store in database
            deck_id = self.db.store_flashcard_deck(title, cards, source, user_id=user_id)

            return {
                "deck_id": deck_id,
                "title": title,
                "cards": cards,
                "card_count": len(cards),
            }
        except Exception as e:
            logger.error(f"Flashcard generation error: {e}")
            raise

    def generate_from_topic(self, topic: str, count: int = 10, user_id: str = None) -> dict:
        """Generate flashcards from a topic using the LLM's own knowledge."""
        prompt = f"Create comprehensive study flashcards about: {topic}"
        full_prompt = FLASHCARD_PROMPT.format(count=count, content=prompt)

        try:
            response = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a JSON-generating study assistant. Always return valid JSON arrays."},
                    {"role": "user", "content": full_prompt},
                ],
                max_tokens=4096,
                temperature=0.5,
            )

            raw = response.choices[0].message.content.strip()
            cards = self._parse_cards(raw)
            if not cards:
                raise ValueError("Failed to parse flashcards from LLM response")

            deck_id = self.db.store_flashcard_deck(topic, cards, "topic", user_id=user_id)
            return {
                "deck_id": deck_id,
                "title": topic,
                "cards": cards,
                "card_count": len(cards),
            }
        except Exception as e:
            logger.error(f"Flashcard generation error: {e}")
            raise

    def _parse_cards(self, raw: str) -> Optional[List[dict]]:
        """Parse JSON flashcards from LLM response, handling common formatting issues."""
        # Try direct parse
        try:
            cards = json.loads(raw)
            if isinstance(cards, list):
                return [c for c in cards if "question" in c and "answer" in c]
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        import re
        json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if json_match:
            try:
                cards = json.loads(json_match.group(1))
                if isinstance(cards, list):
                    return [c for c in cards if "question" in c and "answer" in c]
            except json.JSONDecodeError:
                pass

        # Try finding the array in the text
        bracket_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if bracket_match:
            try:
                cards = json.loads(bracket_match.group(0))
                if isinstance(cards, list):
                    return [c for c in cards if "question" in c and "answer" in c]
            except json.JSONDecodeError:
                pass

        return None
    def list_decks(self, user_id: str = None) -> list:
        """List all flashcard decks."""
        return self.db.list_flashcard_decks(user_id=user_id)

    def get_deck(self, deck_id: str, user_id: str = None) -> Optional[dict]:
        """Get a full flashcard deck."""
        return self.db.get_flashcard_deck(deck_id, user_id=user_id)

    def delete_deck(self, deck_id: str, user_id: str = None) -> bool:
        """Delete a flashcard deck."""
        return self.db.delete_flashcard_deck(deck_id, user_id=user_id)

    def export_deck(self, deck_id: str, user_id: str = None) -> Optional[dict]:
        """Export a deck in a format compatible with Anki import."""
        deck = self.get_deck(deck_id, user_id=user_id)
        if not deck:
            return None
        return {
            "title": deck["title"],
            "cards": deck["cards"],
            "exported_at": deck.get("created_at", ""),
            "format": "studybot_v1",
        }
