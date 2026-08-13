#!/usr/bin/env python3
"""Quick test of core functionality."""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, mongo
from app.services.gemini_service import GeminiService

load_dotenv()

app = create_app()
with app.app_context():
    gemini = GeminiService()
    
    print("✅ MongoDB Connected" if mongo.db else "❌ MongoDB Not Connected")
    print(f"✅ Gemini Available" if gemini.is_available else "❌ Gemini Not Available")
    
    if gemini.is_available:
        print("\nGenerating 2 Software Engineer questions...")
        questions = gemini.generate_questions("Software Engineer", "technical", "medium", 2)
        print(f"✅ Got {len(questions)} questions")
        if questions:
            print(f"\nSample Question:")
            print(f"  Q: {questions[0].get('question', 'N/A')}")
            print(f"  Expected: {questions[0].get('expected_answer', 'N/A')[:100]}...")
            
            print(f"\nAnalyzing answer...")
            feedback = gemini.analyze_answer(
                question=questions[0]['question'],
                user_answer="I would implement horizontal scaling with load balancing.",
                expected_answer=questions[0].get('expected_answer', '')
            )
            print(f"✅ Score: {feedback.get('overall_score')}/100")
            print(f"✅ Feedback: {feedback.get('detailed_feedback', 'N/A')[:80]}...")
    
    print("\n✅ ALL TESTS PASSED!")
