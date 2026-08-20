from app import create_app
import time

app = create_app()
client = app.test_client()

email = f"stress.test+{int(time.time())}@example.com"
print('registering', email)
rv = client.post('/api/auth/register', json={'email': email, 'password': 'TestPass1!'})
print('register', rv.status_code)
if rv.status_code not in (200,201):
    print(rv.get_data(as_text=True))
    raise SystemExit('register failed')

token = rv.get_json().get('token')
headers = {'Authorization': f'Bearer {token}'}

errors = []
for i in range(30):
    r = client.get('/api/subscription/status', headers=headers)
    if r.status_code == 429:
        errors.append((i, r.status_code, r.get_data(as_text=True)[:200]))
    if i % 5 == 0:
        print('iter', i, 'status', r.status_code)
    time.sleep(0.1)

print('done, errors:', errors)
