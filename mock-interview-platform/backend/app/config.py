import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


class Config:
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/mock_interview')
    # Flask-PyMongo reads MONGO_URI; retain MONGODB_URI for compatibility with
    # existing environment files.
    MONGO_URI = MONGODB_URI + ('&' if '?' in MONGODB_URI else '?') + 'serverSelectionTimeoutMS=2000'
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', 'demo-key')
    GOOGLE_GEMINI_MODEL = os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-flash-latest')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('FLASK_DEBUG', 'True') == 'True'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    MONGO_DBNAME = os.getenv('MONGO_DBNAME', 'mock_interview')
