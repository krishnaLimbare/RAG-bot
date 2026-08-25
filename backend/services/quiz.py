"""MCQ quiz generation and evaluation service using Groq LLM."""

import json
import logging
import re
from typing import List, Optional

from backend.config import settings
from backend.db.mongodb import MongoDB
from backend.services.llm import get_groq_client

logger = logging.getLogger(__name__)

QUIZ_PROMPT = """You are a quiz master that creates challenging multiple-choice questions for effective studying.

Given the topic: "{topic}"

Create {count} multiple-choice questions. Each question should have:
- A clear, specific question
- Exactly 4 options labeled A, B, C, D
- One correct answer

Return your response as a valid JSON array of objects with these exact keys:
- "question": the question text
- "options": array of exactly 4 option strings
- "correct": integer index (0-3) of the correct option

Example format:
[
  {{"question": "What is the capital of France?", "options": ["London", "Paris", "Berlin", "Madrid"], "correct": 1}},
  {{"question": "Which planet is closest to the Sun?", "options": ["Venus", "Earth", "Mercury", "Mars"], "correct": 2}}
]

Return ONLY the JSON array, no additional text or markdown formatting."""


WITTY_COMMENTS = {
    "perfect": [
        "You absolute legend! 🏆 Flawless victory!",
        "Are you secretly a professor? 🎓 Perfect score!",
        "100%! Your brain is basically a search engine 🔥",
    ],
    "excellent": [
        "Almost perfect — your brain cells are firing on all cylinders! 🔥",
        "So close to perfection! You clearly know your stuff 💪",
        "Impressive! Just a tiny slip, but you crushed it! 🚀",
    ],
    "good": [
        "Solid! You clearly paid attention… mostly 😏",
        "Not bad at all! A little more revision and you'll ace it 📚",
        "You're on the right track! Keep that momentum going 🎯",
    ],
    "average": [
        "Halfway there! Keep grinding 💪",
        "Room for improvement, but you've got the basics down ✊",
        "A decent attempt! Time to hit the books again 📖",
    ],
    "poor": [
        "Hmm… maybe re-read that chapter? 📖",
        "Don't worry, even Einstein had bad days… probably 😅",
        "Knowledge is a journey, not a destination. Keep going! 🛤️",
    ],
    "terrible": [
        "Did you just guess? Be honest 😂",
        "Well… at least you tried? 🤷‍♂️ Time to study!",
        "Rock bottom is a solid foundation to build on! 🏗️",
    ],
}


class QuizService:
    """Generates MCQ quizzes, evaluates answers, and stores results."""

    def __init__(self):
        self.db = MongoDB()
        self.client = get_groq_client()
        # In-memory store for active quiz sessions (quiz_id -> questions)
        self._active_quizzes: dict = {}

    def generate(self, topic: str, count: int = 10) -> dict:
        """Generate an MCQ quiz on a topic using Groq LLM."""
        prompt = QUIZ_PROMPT.format(topic=topic, count=count)

        try:
            response = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a JSON-generating quiz master. Always return valid JSON arrays."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.7,
            )

            raw = response.choices[0].message.content.strip()
            questions = self._parse_questions(raw)
            if not questions:
                raise ValueError("Failed to parse quiz questions from LLM response")

            # Generate a simple quiz ID and store questions in memory
            import time
            quiz_id = f"quiz_{int(time.time() * 1000)}"
            self._active_quizzes[quiz_id] = {
                "topic": topic,
                "questions": questions,
            }

            # Return questions WITHOUT correct answers
            safe_questions = []
            for q in questions:
                safe_questions.append({
                    "question": q["question"],
                    "options": q["options"],
                })

            return {
                "quiz_id": quiz_id,
                "topic": topic,
                "questions": safe_questions,
                "total": len(safe_questions),
            }
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            raise

    def submit(self, quiz_id: str, answers: List[int], user_id: str = "") -> dict:
        """Evaluate submitted answers and return the score with a witty comment."""
        quiz_data = self._active_quizzes.get(quiz_id)
        if not quiz_data:
            raise ValueError("Quiz not found or expired. Please generate a new quiz.")

        questions = quiz_data["questions"]
        topic = quiz_data["topic"]
        total = len(questions)
        score = 0
        review = []

        for i, q in enumerate(questions):
            user_answer = answers[i] if i < len(answers) else -1
            is_correct = user_answer == q["correct"]
            if is_correct:
                score += 1

            review.append({
                "question": q["question"],
                "options": q["options"],
                "user_answer": user_answer,
                "correct_answer": q["correct"],
                "is_correct": is_correct,
            })

        percentage = (score / total * 100) if total > 0 else 0
        comment = self._get_witty_comment(percentage)

        # Store in MongoDB if user is authenticated
        if user_id:
            self.db.store_quiz(user_id, topic, review, score, total, comment)

        # Clean up active quiz
        del self._active_quizzes[quiz_id]

        return {
            "quiz_id": quiz_id,
            "score": score,
            "total": total,
            "percentage": round(percentage, 1),
            "comment": comment,
            "review": review,
        }

    def get_history(self, user_id: str) -> list:
        """Get quiz history for a user."""
        return self.db.list_quiz_history(user_id)

    def get_quiz_detail(self, quiz_id: str, user_id: str) -> dict:
        """Get full quiz detail including user answers for review."""
        quiz = self.db.get_quiz_by_id(quiz_id, user_id)
        if not quiz:
            raise ValueError("Quiz not found")
        
        # Calculate percentage for frontend
        percentage = (quiz["score"] / quiz["total"] * 100) if quiz["total"] > 0 else 0
        quiz["percentage"] = round(percentage, 1)
        
        return quiz

    @staticmethod
    def _get_witty_comment(percentage: float) -> str:
        """Return a witty comment based on score percentage."""
        import random
        if percentage == 100:
            return random.choice(WITTY_COMMENTS["perfect"])
        elif percentage >= 80:
            return random.choice(WITTY_COMMENTS["excellent"])
        elif percentage >= 60:
            return random.choice(WITTY_COMMENTS["good"])
        elif percentage >= 40:
            return random.choice(WITTY_COMMENTS["average"])
        elif percentage >= 20:
            return random.choice(WITTY_COMMENTS["poor"])
        else:
            return random.choice(WITTY_COMMENTS["terrible"])

    def _parse_questions(self, raw: str) -> Optional[List[dict]]:
        """Parse JSON quiz questions from LLM response."""
        # Try direct parse
        try:
            questions = json.loads(raw)
            if isinstance(questions, list):
                return [q for q in questions if "question" in q and "options" in q and "correct" in q]
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if json_match:
            try:
                questions = json.loads(json_match.group(1))
                if isinstance(questions, list):
                    return [q for q in questions if "question" in q and "options" in q and "correct" in q]
            except json.JSONDecodeError:
                pass

        # Try finding array in text
        bracket_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if bracket_match:
            try:
                questions = json.loads(bracket_match.group(0))
                if isinstance(questions, list):
                    return [q for q in questions if "question" in q and "options" in q and "correct" in q]
            except json.JSONDecodeError:
                pass

        return None
