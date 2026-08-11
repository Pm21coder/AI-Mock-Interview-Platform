from datetime import datetime


class User:
    def __init__(self, email, password_hash, created_at=None, user_id=None):
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self):
        return {
            '_id': self.user_id,
            'email': self.email,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
        }
