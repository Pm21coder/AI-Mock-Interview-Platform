import logging
import json
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    # Optional: prefer OpenAI SDK when available for LLM feedback
    import openai
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

try:
    # DeepFace is optional on servers; we handle absence gracefully
    from deepface import DeepFace
    _HAS_DEEPFACE = True
except Exception:
    _HAS_DEEPFACE = False

# sklearn is used for a lightweight TF-IDF similarity check
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _HAS_SKLEARN = True
except Exception:
    _HAS_SKLEARN = False

from app.config import Config


class AnswerGenerator:
    """Generates a model answer using OpenAI if available, otherwise a simple template."""

    def __init__(self, model_name=None):
        self.model = model_name or getattr(Config, 'OPENAI_MODEL', 'gpt-3.5-turbo')

    def generate_answer(self, question, max_tokens=300):
        if _HAS_OPENAI:
            try:
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": f"Provide a concise, professional answer to the interview question:\n\n{question}"}],
                    max_tokens=max_tokens,
                    temperature=0.6,
                )
                content = resp['choices'][0]['message']['content'].strip()
                return content
            except Exception as exc:
                logger.exception('OpenAI generation failed, falling back to template: %s', exc)

        # Fallback deterministic template
        template = (
            "Start with a short summary that answers the question, then provide 2-3 supporting bullets.")
        return f"{template}\n\n[Sample answer for: {question}]"


class AnswerAnalyzer:
    """Analyze an answer by computing a TF-IDF similarity and requesting LLM feedback when possible."""

    def __init__(self, model_name=None):
        self.model = model_name or getattr(Config, 'OPENAI_MODEL', 'gpt-3.5-turbo')

    def _semantic_similarity(self, text1, text2):
        if not _HAS_SKLEARN:
            return 0.0
        try:
            vect = TfidfVectorizer().fit_transform([text1 or '', text2 or ''])
            sims = cosine_similarity(vect[0:1], vect[1:2])[0][0]
            return float(sims)
        except Exception:
            return 0.0

    def analyze(self, question, user_answer, model_answer):
        sim = self._semantic_similarity(user_answer or '', model_answer or '')

        feedback_text = None
        if _HAS_OPENAI:
            try:
                prompt = (
                    f"You are an expert interview coach.\nQuestion: {question}\nModel Answer: {model_answer}\n"
                    f"Candidate Answer: {user_answer}\nProvide concise constructive feedback under 150 words, focusing on content relevance, structure, and improvement suggestions."
                )
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.2,
                )
                feedback_text = resp['choices'][0]['message']['content'].strip()
            except Exception as exc:
                logger.exception('OpenAI feedback generation failed: %s', exc)

        if not feedback_text:
            # Deterministic fallback feedback
            feedback_text = (
                "Feedback: Could not generate LLM feedback (no OpenAI).\n"
                "Check that your answer covers the question, is structured (Situation, Task, Action, Result) and includes specific outcomes."
            )

        return {
            'similarity_score': round(sim, 3),
            'feedback': feedback_text,
        }


class ExpressionAnalyzer:
    """Analyze a single image (bytes) and return emotion detection results using DeepFace."""

    def analyze_image_bytes(self, image_bytes):
        if not _HAS_DEEPFACE:
            return {'error': 'DeepFace not available on server'}

        try:
            import numpy as np
            import cv2
            arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return {'error': 'Unable to decode image'}

            # Use DeepFace for emotion analysis; enforce_detection=False to avoid failing when face not found
            result = DeepFace.analyze(img_path=img, actions=['emotion'], enforce_detection=False, silent=True)
            # DeepFace returns list or dict depending on version; normalize
            if isinstance(result, list) and len(result) > 0:
                r = result[0]
            else:
                r = result
            dominant = r.get('dominant_emotion') if isinstance(r, dict) else None
            emotions = r.get('emotion') if isinstance(r, dict) else None
            return {
                'dominant_emotion': dominant,
                'emotions': emotions,
            }
        except Exception as exc:
            logger.exception('Expression analysis failed: %s', exc)
            return {'error': 'Expression analysis failed', 'detail': str(exc)}
