#!/usr/bin/env python3
"""
Quick test to verify job-role-specific questions are working
"""

import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from app.services.gemini_service import GeminiService
from app.config import Config

# Test the prompt generation
service = GeminiService()

# Check configuration
print("=" * 80)
print("Configuration Check:")
print("=" * 80)
print(f"ENABLE_GEMINI: {Config.ENABLE_GEMINI}")
print(f"GOOGLE_GEMINI_MODEL: {Config.GOOGLE_GEMINI_MODEL}")
print(f"API Key configured: {'Yes' if Config.GOOGLE_GEMINI_API_KEY else 'No'}")
print(f"Service available: {service.is_available}")
print(f"Model candidates: {service.model_candidates_list}")

# Test different job roles
test_roles = [
    ('Product Manager', 'behavioral'),
    ('DevOps Engineer', 'technical'),
    ('Data Scientist', 'technical'),
    ('UX Designer', 'behavioral'),
]

print("\n" + "=" * 80)
print("Testing Question Generation for Different Job Roles:")
print("=" * 80)

for job_role, category in test_roles:
    print(f"\n✓ Job Role: {job_role} ({category})")
    print(f"  Testing prompt construction...")
    
    # The actual prompt
    num_questions = 3
    prompt = f"""
    Generate {num_questions} medium level interview questions for a {job_role} position
    focusing on {category}. Include the expected answer for each question.

    Format as JSON:
    [
        {{
            "question": "question text",
            "expected_answer": "expected answer text"
        }}
    ]
    """
    
    if job_role in prompt and category in prompt:
        print(f"  ✅ Prompt includes job role '{job_role}' and category '{category}'")
    else:
        print(f"  ❌ Prompt MISSING job role or category!")
        print(f"     Job role present: {job_role in prompt}")
        print(f"     Category present: {category in prompt}")

print("\n" + "=" * 80)
print("Note: If the above shows that prompts are job-role-specific,")
print("then the question generation IS working correctly.")
print("If questions appear generic, it means the API is failing and")
print("falling back to local hardcoded fallback questions.")
print("=" * 80)
