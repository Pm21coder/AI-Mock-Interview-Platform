import jwt
import requests
import json
from time import sleep

BASE='http://127.0.0.1:5000'
SECRET='your-secret-key-change-in-production'
user_id='demo_test_local'
# Create a real token via the auth register endpoint instead of crafting one
print('Registering a temporary user to obtain a valid token...')
reg_payload = {'email': 'smoketest+' + 'user@example.com', 'password': 'TestPass1!'}
try:
    reg = requests.post(BASE + '/api/auth/register', json=reg_payload)
    if reg.status_code in (200,201):
        token = reg.json().get('token')
    else:
        print('Register failed', reg.status_code, reg.text)
            # Try login if the user already exists
            try:
                login = requests.post(BASE + '/api/auth/login', json={'email': reg_payload['email'], 'password': reg_payload['password']})
                if login.status_code == 200:
                    token = login.json().get('token')
                else:
                    print('Login also failed', login.status_code, login.text)
                    token = None
            except Exception as le:
                print('Login error', le)
                token = None
    except Exception as exc:
        print('Register error', exc)
        token = None

    if not token:
        print('Could not obtain token, aborting smoke test')
        raise SystemExit(1)

headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}

print('Using token, proceeding with generate/analyze/get-feedback')

# 1) generate-questions (let server create a session)
print('Posting generate-questions...')
r = requests.post(BASE + '/api/interview/generate-questions', headers=headers, json={'job_role':'Software Engineer'})
print('generate status', r.status_code, r.text)
if r.status_code != 200:
    print('generate failed, aborting')
    raise SystemExit(1)
resp = r.json()
session_id = resp.get('session_id')
questions = resp.get('questions', [])
if not session_id or not questions:
    print('No session_id or questions returned, aborting')
    raise SystemExit(1)

question0 = questions[0]
question_text = question0.get('question')
expected_answer = question0.get('expected_answer', '')
print('Session:', session_id)
print('Question:', question_text)

# 2) analyze-answer (simulate response) - provide required fields
print('Posting analyze-answer...')
answer_payload = {
    'session_id': session_id,
    'question_index': 0,
    'question': question_text,
    'answer': 'This is a test answer to the question',
    'expected_answer': expected_answer,
}
r2 = requests.post(BASE + '/api/interview/analyze-answer', headers=headers, json=answer_payload)
print('analyze status', r2.status_code, r2.text)

# give server a moment to persist
sleep(1)

# 3) get-feedback
print('Requesting get-feedback...')
r3 = requests.get(BASE + f'/api/interview/get-feedback/{session_id}', headers=headers)
print('get-feedback status', r3.status_code)
print('get-feedback body:', r3.text)
