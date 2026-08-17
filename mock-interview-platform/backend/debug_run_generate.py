import jwt,os,requests
from datetime import datetime,timedelta
secret='local-dev-secret-change-me'  # match backend .env JWT_SECRET_KEY
payload={'user_id':'demo_default','email':'demo@mockinterview.app','exp':datetime.utcnow()+timedelta(hours=2)}
token=jwt.encode(payload,secret,algorithm='HS256')
headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
url='http://127.0.0.1:5000/api/interview/generate-questions'
resp=requests.post(url,json={'job_role':'Backend Engineer','difficulty':'medium','num_questions':3},headers=headers,timeout=30)
print('status',resp.status_code)
print(resp.text)
