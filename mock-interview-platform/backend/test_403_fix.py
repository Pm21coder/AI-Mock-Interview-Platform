#!/usr/bin/env python3
"""Test the /analyze-answer endpoint to diagnose 403 response."""

from app import create_app
import json

app = create_app()

print("=" * 60)
print("Testing /api/interview/analyze-answer endpoint")
print("=" * 60)

with app.test_client() as client:
    # Test 1: Guest user with video_data=True (should get 403 with error message)
    print("\nTest 1: Guest user submitting with video_data=True")
    response = client.post(
        '/api/interview/analyze-answer',
        json={
            'question': 'Tell me about yourself',
            'answer': 'I am a software engineer with 5 years of experience',
            'expected_answer': 'Professional background',
            'session_id': 'test_session',
            'question_index': 0,
            'video_data': True,
        },
        headers={'Content-Type': 'application/json'}
    )
    print(f'  Status: {response.status_code}')
    print(f'  Content-Type: {response.headers.get("Content-Type")}')
    print(f'  Raw body: {response.data}')
    try:
        json_data = response.get_json()
        print(f'  Parsed JSON: {json.dumps(json_data, indent=2)}')
    except Exception as e:
        print(f'  JSON parse error: {e}')

    # Test 2: Guest user with video_data=False (should work)
    print("\nTest 2: Guest user submitting with video_data=False")
    response = client.post(
        '/api/interview/analyze-answer',
        json={
            'question': 'Tell me about yourself',
            'answer': 'I am a software engineer with 5 years of experience',
            'expected_answer': 'Professional background',
            'session_id': 'test_session',
            'question_index': 0,
            'video_data': False,
        },
        headers={'Content-Type': 'application/json'}
    )
    print(f'  Status: {response.status_code}')
    print(f'  Content-Type: {response.headers.get("Content-Type")}')
    try:
        json_data = response.get_json()
        print(f'  Keys in response: {list(json_data.keys()) if isinstance(json_data, dict) else "not a dict"}')
        if response.status_code == 200:
            print(f'  ✓ Success!')
        else:
            print(f'  Parsed JSON: {json.dumps(json_data, indent=2)[:200]}...')
    except Exception as e:
        print(f'  JSON parse error: {e}')

print("\n" + "=" * 60)
