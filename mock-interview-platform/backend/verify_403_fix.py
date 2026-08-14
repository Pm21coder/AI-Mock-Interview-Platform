#!/usr/bin/env python3
"""Verify the /analyze-answer endpoint now works for guest users with video_data."""

import sys
sys.path.insert(0, '.')

from app import create_app
import json

app = create_app()

print("=" * 70)
print("TESTING: Guest user can now submit answers with video_data=True")
print("=" * 70)

with app.test_client() as client:
    # Test 1: Guest user WITH video data (should now work, not 403)
    print("\n✓ Test 1: Guest user submitting with video_data=True")
    response = client.post(
        '/api/interview/analyze-answer',
        json={
            'question': 'Tell me about your experience with APIs',
            'answer': 'I have designed and maintained REST APIs using Python and Flask',
            'expected_answer': 'Professional API design experience',
            'session_id': 'test_session_001',
            'question_index': 0,
            'video_data': True,
        }
    )
    print(f"  Status: {response.status_code}")
    if response.status_code in (200, 201):
        print("  ✓ SUCCESS - Request accepted")
        data = response.get_json()
        
        # Check response structure
        if 'cv_analysis' in data:
            cv = data['cv_analysis']
            if 'upgrade_note' in cv:
                print(f"  ✓ Video data noted: {cv['upgrade_note']}")
            else:
                print(f"  ✓ Video analysis provided")
        
        if 'gemini_feedback' in data:
            print(f"  ✓ Gemini feedback included")
        if 'nlp_analysis' in data:
            print(f"  ✓ NLP analysis included")
            
    elif response.status_code == 403:
        print("  ✗ FAILED - Still getting 403")
        print(f"  Response: {response.get_json()}")
    else:
        print(f"  ? Unexpected status: {response.status_code}")
        print(f"  Response: {response.data}")

    # Test 2: Guest user WITHOUT video data (should still work)
    print("\n✓ Test 2: Guest user submitting with video_data=False")
    response = client.post(
        '/api/interview/analyze-answer',
        json={
            'question': 'How do you handle errors in production?',
            'answer': 'I use comprehensive logging, monitoring, and alerting',
            'expected_answer': 'Error handling practices',
            'session_id': 'test_session_002',
            'question_index': 0,
            'video_data': False,
        }
    )
    print(f"  Status: {response.status_code}")
    if response.status_code in (200, 201):
        print("  ✓ SUCCESS - Request accepted")
    else:
        print(f"  ✗ FAILED - Status: {response.status_code}")

print("\n" + "=" * 70)
print("Test completed!")
print("=" * 70)
