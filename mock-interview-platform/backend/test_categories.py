import requests
import json

# Test question categories endpoint with a token
test_token = "test-token-12345"

try:
    print("Testing question categories endpoint...")
    response = requests.get(
        'http://localhost:5000/api/subscription/question-categories',
        headers={'Authorization': f'Bearer {test_token}'},
        timeout=10
    )
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'Error: {str(e)}')
