from datetime import datetime

from app.utils.time import utc_now

class InterviewQuestion:
    def __init__(self, question, category, difficulty, expected_answer=None):
        self.question = question
        self.category = category
        self.difficulty = difficulty
        self.expected_answer = expected_answer

    def to_dict(self):
        return {
            'question': self.question,
            'category': self.category,
            'difficulty': self.difficulty,
            'expected_answer': self.expected_answer,
        }


class InterviewSession:
    def __init__(self, user_id, job_role, questions, created_at=None):
        self.user_id = user_id
        self.job_role = job_role
        self.questions = questions
        self.created_at = created_at or utc_now()
        self.responses = []
        self.feedback = []

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'job_role': self.job_role,
            'questions': [q.to_dict() for q in self.questions],
            'created_at': self.created_at,
            'responses': self.responses,
            'feedback': self.feedback,
        }
