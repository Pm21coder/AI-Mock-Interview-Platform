import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load variables from backend/.env for local development. In production the
# deployment platform injects these as real environment variables.
# Use override=True so the checked-in local config file can win over stale
# shell environment values that may still point at an old Atlas DB.
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)


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
    # Prefer the local project MongoDB for development so the app does not
    # silently fall back to guest mode when a remote Atlas SRV endpoint is not
    # reachable from the current machine. Atlas stays available only when an
    # explicit opt-in is set, which avoids broken SRV URLs taking down local
    # development.
    # A single browser action can trigger multiple dependent Mongo reads. Keep
    # each server-selection attempt short so an unavailable database does not
    # turn into a 30-second-or-longer API request.
    MONGO_CONNECT_TIMEOUT_MS = min(
        max(int(os.getenv('MONGO_CONNECT_TIMEOUT_MS', '5000')), 250),
        5000,
    )
    DEFAULT_LOCAL_MONGO_URI = 'mongodb://admin:password123@localhost:27017/mock_interview?authSource=admin'
    use_atlas = os.getenv('USE_ATLAS_MONGO', 'false').lower() == 'true'
    env_uri = os.getenv('MONGODB_URI')

    if use_atlas and env_uri:
        mongo_uri = env_uri
    elif env_uri and ('mongodb://localhost' in env_uri.lower() or 'mongodb://127.0.0.1' in env_uri.lower() or 'mongodb://admin:' in env_uri.lower()):
        mongo_uri = env_uri
    elif env_uri and '.mongodb.net' in env_uri.lower():
        mongo_uri = DEFAULT_LOCAL_MONGO_URI
    else:
        mongo_uri = env_uri or DEFAULT_LOCAL_MONGO_URI

    MONGO_URI = _with_mongo_timeouts(mongo_uri, MONGO_CONNECT_TIMEOUT_MS)

    # Google Gemini AI Configuration
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', '')
    # Use a stable Gemini model name that is supported by both the legacy and
    # modern Google SDKs. Strip any legacy `models/` prefix before use.
    GOOGLE_GEMINI_MODEL = os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-3.6-flash')
    # By default prefer a generic HTTP LLM provider (e.g., Deepseek) over
    # the Google Gemini SDK for interview generation and analysis. Set
    # ENABLE_GEMINI=true only if you explicitly want to use Google Gemini.
    ENABLE_GEMINI = os.getenv('ENABLE_GEMINI', 'false').lower() == 'true'
    # Keep interactive endpoints responsive when the external AI provider is
    # slow or unreachable; the service supplies local fallback responses.
    GEMINI_TIMEOUT_SECONDS = float(os.getenv('GEMINI_TIMEOUT_SECONDS', '10'))
    # Number of retries to attempt for Gemini provider calls (retries on timeout/network errors)
    GEMINI_RETRIES = int(os.getenv('GEMINI_RETRIES', '1'))

    # Razorpay Configuration
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_CURRENCY = os.getenv('RAZORPAY_CURRENCY', 'INR')
    RAZORPAY_TIMEOUT_SECONDS = min(
        max(float(os.getenv('RAZORPAY_TIMEOUT_SECONDS', '8')), 1.0),
        15.0,
    )

    # CORS Configuration
    # Restrict to specific origins for security. Prevents unauthorized cross-origin requests.
    # Strip whitespace from origins to avoid matching issues
    CORS_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')]
    
    # Rate Limiting Configuration
    # Protect against brute force and DoS attacks
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = os.getenv('RATELIMIT_STRATEGY', 'fixed-window')

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
            'monthly_interviews': None,  # None = unlimited
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

    # Optional LLM provider configuration (OpenAI or a generic HTTP LLM provider)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    # Generic provider: set LLM_API_KEY and LLM_API_URL to enable HTTP-based LLMs
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    LLM_API_URL = os.getenv('LLM_API_URL', '')
    # Optionally hint at provider name (e.g., 'deepseek') for logging/metrics
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', '')

