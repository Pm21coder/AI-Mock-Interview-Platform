from datetime import datetime


class DashboardStats:
    """Structured representation of a user's dashboard statistics.

    This model mirrors the `dashboard_stats` collection in MongoDB and is
    used to persist pre-aggregated statistics so the dashboard endpoint can
    serve data quickly without recomputing on every request.
    """

    def __init__(
        self,
        user_id,
        interviews_completed=0,
        average_score=0,
        confidence_score=0,
        total_responses=0,
        recent_interviews=None,
        updated_at=None,
    ):
        self.user_id = user_id
        self.interviews_completed = interviews_completed
        self.average_score = average_score
        self.confidence_score = confidence_score
        self.total_responses = total_responses
        self.recent_interviews = recent_interviews or []
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'interviews_completed': self.interviews_completed,
            'average_score': self.average_score,
            'confidence_score': self.confidence_score,
            'total_responses': self.total_responses,
            'recent_interviews': self.recent_interviews,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data.get('user_id'),
            interviews_completed=data.get('interviews_completed', 0),
            average_score=data.get('average_score', 0),
            confidence_score=data.get('confidence_score', 0),
            total_responses=data.get('total_responses', 0),
            recent_interviews=data.get('recent_interviews', []),
            updated_at=data.get('updated_at'),
        )