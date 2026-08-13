import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load variables from backend/.env for local development. In production the
# deployment platform injects these as real environment variables.
load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def _with_mongo_timeouts(uri, timeout_ms):
    """Avoid blocking API requests on long MongoDB server selection waits."""
    existing_uri = uri.lower()
    timeout_options = {
        'connectTimeoutMS': timeout_ms,
        'serverSelectionTimeoutMS': timeout_ms,
        'socketTimeoutMS': timeout_ms,
    }
    missing_options = [
        f'{key}={value}'
        for key, value in timeout_options.items()
        if f'{key.lower()}=' not in existing_uri
    ]
    if not missing_options:
        return uri
    separator = '&' if '?' in uri else '?'
    return f'{uri}{separator}' + '&'.join(missing_options)


class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # MongoDB Configuration
    MONGO_CONNECT_TIMEOUT_MS = int(os.getenv('MONGO_CONNECT_TIMEOUT_MS', '1500'))
    MONGO_URI = _with_mongo_timeouts(
        os.getenv('MONGODB_URI', 'mongodb://localhost:27017/mock_interview'),
        MONGO_CONNECT_TIMEOUT_MS,
    )

    # Google Gemini AI Configuration
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', '')
    # Use a stable Gemini model name that is supported by both the legacy and
    # modern Google SDKs. Strip any legacy `models/` prefix before use.
    GOOGLE_GEMINI_MODEL = os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-2.0-flash')
    # Use Gemini whenever a valid API key is configured. The service retains
    # local fallbacks for unavailable credentials or provider errors.
    ENABLE_GEMINI = os.getenv('ENABLE_GEMINI', 'true').lower() == 'true'
    # Keep interactive endpoints responsive when the external AI provider is
    # slow or unreachable; the service supplies local fallback responses.
    GEMINI_TIMEOUT_SECONDS = float(os.getenv('GEMINI_TIMEOUT_SECONDS', '10'))

    # Razorpay Configuration
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_CURRENCY = os.getenv('RAZORPAY_CURRENCY', 'INR')

    # Frontend URL
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    # Subscription Tiers Configuration
    SUBSCRIPTION_TIERS = {
        'free': {
            'name': 'Free',
            'price': 0,
            'monthly_interviews': 3,
            'feedback_history_days': 7,  # Free tier: 7-day history
            'question_categories': 'standard',  # standard categories only
            'features': {
                'basic_feedback': True,
                'advanced_feedback': False,
                'video_analysis': False,
                'unlimited_history': False,
                'custom_scenarios': False,
                'priority_support': False,
                'resume_review': False,
                'premium_ai_coaching': False,
                'advanced_analytics': False,
                'email_support': False,
                'all_question_categories': False,
            }
        },
        'basic': {
            'name': 'Basic',
            'price': 5,
            'monthly_interviews': 15,
            'feedback_history_days': None,  # Unlimited history
            'question_categories': 'all',  # All categories available
            'features': {
                'basic_feedback': True,
                'advanced_feedback': True,
                'video_analysis': True,
                'unlimited_history': True,
                'custom_scenarios': False,
                'priority_support': False,
                'resume_review': False,
                'premium_ai_coaching': False,
                'advanced_analytics': False,
                'email_support': True,
                'all_question_categories': True,
            }
        },
        'pro': {
            'name': 'Pro',
            'price': 10,
            'monthly_interviews': float('inf'),  # Unlimited
            'feedback_history_days': None,  # Unlimited history
            'question_categories': 'all',  # All categories available
            'features': {
                'basic_feedback': True,
                'advanced_feedback': True,
                'video_analysis': True,
                'unlimited_history': True,
                'custom_scenarios': True,
                'priority_support': True,
                'resume_review': True,
                'premium_ai_coaching': True,
                'advanced_analytics': True,
                'email_support': True,
                'all_question_categories': True,
            }
        }
    }

    # Razorpay subscription order amounts in paise (100 paise = 1 INR).
    # Minimum order value supported by Razorpay is 100 paise.
    RAZORPAY_ORDER_AMOUNTS = {
        'basic': 37500,
        'pro': 75000,
    }
