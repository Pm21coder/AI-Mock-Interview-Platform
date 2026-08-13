#!/usr/bin/env python3
"""End-to-end test of interview question generation and answer analysis."""

import os
import json
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, mongo
from app.services.gemini_service import GeminiService
from app.services.nlp_service import NLPService

load_dotenv()

print("=" * 70)
print("E2E Test: Interview Generation & Analysis")
print("=" * 70)

# Initialize Flask app and services
app = create_app()
with app.app_context():
    gemini_service = GeminiService()
    nlp_service = NLPService()
    
    print(f"\n[1] Service Status")
    print(f"  Gemini available: {gemini_service.is_available}")
    print(f"  API key set: {'✅' if os.getenv('GOOGLE_GEMINI_API_KEY') else '❌'}")
    print(f"  MongoDB available: {mongo.db is not None}")
    
    # Test 1: Generate questions
    print(f"\n[2] Generate Questions (Software Engineer, Technical)")
    try:
        questions = gemini_service.generate_questions(
            job_role="Software Engineer",
            category="technical",
            difficulty="medium",
            num_questions=3
        )
        print(f"  ✅ Generated {len(questions)} questions")
        for i, q in enumerate(questions[:1], 1):
            print(f"     Q{i}: {q.get('question', 'N/A')[:70]}...")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
        questions = []
    
    # Test 2: Analyze answer
    if questions:
        print(f"\n[3] Analyze Answer")
        try:
            feedback = gemini_service.analyze_answer(
                question=questions[0]['question'],
                user_answer="I would use a load balancer and horizontal scaling with microservices architecture.",
                expected_answer="Discuss scalability patterns like load balancing, caching, and database optimization."
            )
            print(f"  ✅ Analysis complete")
            print(f"     Overall score: {feedback.get('overall_score', 'N/A')}")
            print(f"     Feedback: {feedback.get('detailed_feedback', 'N/A')[:100]}...")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
    
    # Test 3: NLP Analysis
    print(f"\n[4] NLP Analysis")
    try:
        nlp_result = nlp_service.analyze_answer_quality(
            "I would implement caching and use CDN",
            "Discuss performance optimization strategies"
        )
        print(f"  ✅ NLP analysis complete")
        print(f"     Confidence: {nlp_result.get('confidence_score', 'N/A')}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
    
    # Test 4: Resume analysis (if available)
    print(f"\n[5] Resume Analysis")
    try:
        resume_text = """
        John Doe
        Software Engineer
        
        Experience:
        - Built microservices using Python and Kubernetes
        - Optimized database queries, reducing latency by 40%
        - Led team of 5 engineers on critical infrastructure project
        
        Skills: Python, Go, Docker, Kubernetes, PostgreSQL
        """
        analysis = gemini_service.analyze_resume(resume_text)
        print(f"  ✅ Resume analysis complete")
        print(f"     Overall score: {analysis.get('overall_score', 'N/A')}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
    
    # Test 5: Fallback for different job roles
    print(f"\n[6] Job Role Fallback Test")
    for role in ["Product Manager", "Data Scientist", "DevOps Engineer", "Custom Role XYZ"]:
        try:
            q = gemini_service.generate_questions(role, "behavioral", "medium", 1)
            if q and len(q) > 0:
                print(f"  ✅ {role}: {q[0].get('question', 'N/A')[:60]}...")
            else:
                print(f"  ⚠️  {role}: No questions generated")
        except Exception as e:
            print(f"  ❌ {role}: {type(e).__name__}")

print("\n" + "=" * 70)
print("E2E Test Complete")
print("=" * 70)
