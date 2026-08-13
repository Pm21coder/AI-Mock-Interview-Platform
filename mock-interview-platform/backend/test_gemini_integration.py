#!/usr/bin/env python3
"""
Test script for Gemini API integration.
Run this to verify that the Gemini service is working correctly.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from app.config import Config
from app.services.gemini_service import GeminiService


def test_gemini_service():
    """Test the GeminiService with sample data."""
    print("=" * 80)
    print("Gemini Service Integration Test")
    print("=" * 80)
    
    # Check configuration
    print("\n1. Configuration Check:")
    print(f"   ENABLE_GEMINI: {Config.ENABLE_GEMINI}")
    print(f"   GOOGLE_GEMINI_MODEL: {Config.GOOGLE_GEMINI_MODEL}")
    print(f"   API Key configured: {'Yes' if Config.GOOGLE_GEMINI_API_KEY and Config.GOOGLE_GEMINI_API_KEY != 'YOUR_GOOGLE_GEMINI_API_KEY_HERE' else 'No'}")
    print(f"   API Key preview: {Config.GOOGLE_GEMINI_API_KEY[:20]}...")
    
    # Initialize service
    print("\n2. Initializing GeminiService...")
    service = GeminiService()
    print(f"   Service available: {service.is_available}")
    print(f"   Model name: {service.model_name}")
    
    if not service.is_available:
        print("\n   ❌ Service is not available. Check:")
        print("      - GOOGLE_GEMINI_API_KEY is set in .env")
        print("      - google-generativeai library is installed")
        print("      - API key is valid")
        return False
    
    # Test generating questions
    print("\n3. Testing Question Generation...")
    try:
        questions = service.generate_questions(
            job_role="Software Engineer",
            category="technical",
            difficulty="medium",
            num_questions=2
        )
        print(f"   ✅ Successfully generated {len(questions)} questions")
        for i, q in enumerate(questions[:2], 1):
            print(f"      Q{i}: {q.get('question', 'N/A')[:60]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test analyzing answers
    print("\n4. Testing Answer Analysis...")
    try:
        feedback = service.analyze_answer(
            question="What is a REST API?",
            user_answer="It's an API that uses HTTP methods like GET, POST, PUT, DELETE.",
            expected_answer="REST is an architectural style using HTTP methods on resources identified by URIs."
        )
        print(f"   ✅ Successfully analyzed answer")
        print(f"      Overall Score: {feedback.get('overall_score', 'N/A')}")
        print(f"      Feedback: {feedback.get('detailed_feedback', 'N/A')[:60]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test resume analysis
    print("\n5. Testing Resume Analysis...")
    resume_text = """
    John Doe
    Software Engineer
    john@example.com
    
    EXPERIENCE:
    - Senior Software Engineer at TechCorp (2020-2024)
      * Led team of 5 engineers
      * Improved system performance by 40%
    
    SKILLS:
    - Python, JavaScript, React, Node.js
    - AWS, Docker, Kubernetes
    """
    
    try:
        analysis = service.analyze_resume(resume_text)
        print(f"   ✅ Successfully analyzed resume")
        print(f"      Overall Score: {analysis.get('overall_score', 'N/A')}")
        print(f"      Feedback: {analysis.get('detailed_feedback', 'N/A')[:60]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("✅ All tests passed! Gemini API is working correctly.")
    print("=" * 80)
    return True


if __name__ == '__main__':
    try:
        success = test_gemini_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
