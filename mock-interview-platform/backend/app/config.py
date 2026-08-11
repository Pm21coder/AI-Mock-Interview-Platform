import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load variables from backend/.env for local development. In production the
# deployment platform injects these as real environment variables.
load_dotenv(Path(__file__).resolve().parent.parent / '.env')


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
    GOOGLE_GEMINI_MODEL = os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-1.5-flash')

    # Razorpay Configuration
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_CURRENCY = os.getenv('RAZORPAY_CURRENCY', 'INR')

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

    # Razorpay subscription order amounts in paise (100 paise = ₹1 INR).
    # Minimum order value supported by Razorpay is 100 paise.
    RAZORPAY_ORDER_AMOUNTS = {
        'basic': 37500,   # ₹375.00
        'pro': 75000,     # ₹750.00
    }

    # UPI Amounts in INR (approximate conversions)
    UPI_AMOUNTS = {
        'basic': '₹375',  # $5 USD ≈ ₹375 INR
        'pro': '₹750',    # $10 USD ≈ ₹750 INR
    }
