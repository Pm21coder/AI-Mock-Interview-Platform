import requests
import json

data = {
    'name': 'Test User',
    'email': 'test@example.com',
    'subject': 'Test Contact Form',
    'message': 'This is a test message.'
}

try:
    print("Testing contact form endpoint...")
    response = requests.post('http://localhost:5000/api/send-email', json=data, timeout=10)
    print(f'Status Code: {response.status_code}')
    result = response.json()
    print(f'Response: {json.dumps(result, indent=2)}')
except Exception as e:
    print(f'Error: {str(e)}')
