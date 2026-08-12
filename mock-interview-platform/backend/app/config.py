import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load variables from backend/.env for local development. In production the
# deployment platform injects these as real environment variables.
load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def _with_mongo_connect_timeout(uri, timeout_ms):
    """Avoid blocking API startup for the default 20-second DNS timeout."""
    if not uri.startswith('mongodb+srv://') or 'connectTimeoutMS=' in uri:
        return uri
    separator = '&' if '?' in uri else '?'
    return f'{uri}{separator}connectTimeoutMS={timeout_ms}'


class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # MongoDB Configuration
    MONGO_CONNECT_TIMEOUT_MS = int(os.getenv('MONGO_CONNECT_TIMEOUT_MS', '3000'))
    MONGO_URI = _with_mongo_connect_timeout(
        os.getenv('MONGODB_URI', 'mongodb://localhost:27017/mock_interview'),
        MONGO_CONNECT_TIMEOUT_MS,
    )

    # Google Gemini AI Configuration
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', '')
    GOOGLE_GEMINI_MODEL = os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-1.5-flash')
    # The app has useful local fallbacks. Keep the external provider opt-in so
    # an unavailable network service can never block an interview request.
    ENABLE_GEMINI = os.getenv('ENABLE_GEMINI', 'false').lower() == 'true'
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
            'features': {
                'basic_feedback': True,
                'advanced_feedback': False,
                'video_analysis': False,
                'unlimited_history': False,
                'custom_scenarios': False,
                'priority_support': False,
                'resume_review': False,
            }
        },
        'basic': {
            'name': 'Basic',
            'price': 5,
            'monthly_interviews': 15,
            'features': {
                'basic_feedback': True,
                'advanced_feedback': True,
                'video_analysis': True,
                'unlimited_history': True,
                'custom_scenarios': False,
                'priority_support': False,
                'resume_review': False,
            }
        },
        'pro': {
            'name': 'Pro',
            'price': 10,
            'monthly_interviews': float('inf'),  # Unlimited
            'features': {
                'basic_feedback': True,
                'advanced_feedback': True,
                'video_analysis': True,
                'unlimited_history': True,
                'custom_scenarios': True,
                'priority_support': True,
                'resume_review': True,
            }
        }
    }

    # Razorpay subscription order amounts in paise (100 paise = 1 INR).
    # Minimum order value supported by Razorpay is 100 paise.
    RAZORPAY_ORDER_AMOUNTS = {
        'basic': 37500,
        'pro': 75000,
    }
