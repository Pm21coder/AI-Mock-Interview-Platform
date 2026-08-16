from app import create_app

app = create_app()
client = app.test_client()

health = client.get('/health')
print('HEALTH_STATUS=', health.status_code)
print('HEALTH_JSON=', health.get_json())

login = client.post('/api/auth/login', json={'email': 'demo@mockinterview.app', 'password': 'demo12345'})
print('LOGIN_STATUS=', login.status_code)
print('LOGIN_JSON=', login.get_json())
