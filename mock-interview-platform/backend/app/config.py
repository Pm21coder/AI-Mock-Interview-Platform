import os
from datetime import timedelta


class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/mock_interview')
    
    # Google Gemini AI Configuration
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', '')
    
    # Stripe Configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    # UPI Configuration (for Indian users)
    UPI_ID = os.getenv('UPI_ID', '9156727375@pthdfc')
    UPI_NAME = os.getenv('UPI_NAME', 'Pramod Ulhas Mane')
    
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
            'price': 9,
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
            'price': 19,
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
    
    # Stripe Price IDs (set these in your Stripe dashboard)
    STRIPE_PRICE_IDS = {
        'basic': os.getenv('STRIPE_BASIC_PRICE_ID', 'price_basic_monthly'),
        'pro': os.getenv('STRIPE_PRO_PRICE_ID', 'price_pro_monthly'),
    }