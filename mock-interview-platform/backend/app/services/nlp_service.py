import re


class NLPService:
    """Lightweight, dependency-free answer analysis for local practice mode."""

    def analyze_answer_quality(self, answer, expected_answer):
        words = re.findall(r"[A-Za-z']+", answer)
        sentences = [sentence for sentence in re.split(r'[.!?]+', answer) if sentence.strip()]
        expected_words = {word.lower() for word in re.findall(r"[A-Za-z']+", expected_answer) if len(word) > 3}
        answer_words = {word.lower() for word in words}
        keyword_coverage = len(expected_words & answer_words) / len(expected_words) if expected_words else 0
        similarity_score = len(expected_words & answer_words) / len(expected_words | answer_words) if expected_words else 0
        grammar_score = self._grammar_score(answer, sentences)
        analysis = {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'sentiment': {'polarity': 0, 'subjectivity': 0},
            'keyword_coverage': keyword_coverage,
            'similarity_score': similarity_score,
            'grammar_score': grammar_score,
        }
        analysis['overall_quality'] = min(
            1.0,
            0.1 * min(len(words) / 75, 1) + 0.1 * min(len(sentences) / 5, 1)
            + 0.25 * keyword_coverage + 0.25 * similarity_score + 0.15 * grammar_score + 0.075,
        )
        return analysis

    @staticmethod
    def _grammar_score(answer, sentences):
        if not sentences:
            return 0
        complete_sentences = sum(1 for sentence in sentences if sentence.strip()[:1].isupper())
        terminal_punctuation = 1 if answer.strip().endswith(('.', '!', '?')) else 0
        return min(1.0, 0.75 * complete_sentences / len(sentences) + 0.25 * terminal_punctuation)
