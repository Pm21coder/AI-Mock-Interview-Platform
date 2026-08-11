from datetime import datetime


class User:
    def __init__(self, email, password_hash, created_at=None, user_id=None, 
                 subscription_tier='free', subscription_status='active',
                 interviews_used_this_month=0, subscription_start_date=None,
                 subscription_end_date=None, stripe_customer_id=None,
                 stripe_subscription_id=None):
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()
        self.subscription_tier = subscription_tier  # free, basic, pro
        self.subscription_status = subscription_status  # active, canceled, past_due
        self.interviews_used_this_month = interviews_used_this_month
        self.subscription_start_date = subscription_start_date
        self.subscription_end_date = subscription_end_date
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id

    def to_dict(self):
        return {
            '_id': self.user_id,
            'email': self.email,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'subscription_tier': self.subscription_tier,
            'subscription_status': self.subscription_status,
            'interviews_used_this_month': self.interviews_used_this_month,
            'subscription_start_date': self.subscription_start_date,
            'subscription_end_date': self.subscription_end_date,
            'stripe_customer_id': self.stripe_customer_id,
            'stripe_subscription_id': self.stripe_subscription_id,
        }
