import json
import requests

payload = {
    'question': 'Tell me about a time you solved a problem.',
    'answer': 'I looked at the issue, broke it down, and worked with my team to fix the root cause.',
    'expected_answer': 'A strong answer describes a specific issue, actions taken, and measurable outcome.',
    'session_id': 's1',
    'question_index': 0,
}

response = requests.post(
    'http://127.0.0.1:5000/api/interview/analyze-answer',
    json=payload,
    timeout=30,
)
print('STATUS', response.status_code)
print(response.text[:2000])
