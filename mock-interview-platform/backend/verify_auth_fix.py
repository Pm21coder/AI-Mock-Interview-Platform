import os

os.chdir(r'C:\Users\dell\OneDrive\Desktop\AI Mock Interview Platform\mock-interview-platform\backend')

from app import create_app
from app.routes import auth as auth_routes

email = 'persistdemo@example.com'
password = 'StrongPass!123'
weak_password = 'Password123'

store = auth_routes.load_local_auth_users()
store.pop(email, None)
auth_routes.save_local_auth_users(store)

app = create_app()
client = app.test_client()

weak = client.post('/api/auth/register', json={'email': 'weakcheck@example.com', 'password': weak_password})
print('WEAK', weak.status_code, weak.get_json())

register = client.post('/api/auth/register', json={'email': email, 'password': password})
print('REGISTER', register.status_code, register.get_json())

login = client.post('/api/auth/login', json={'email': email, 'password': password})
print('LOGIN', login.status_code, login.get_json())
print('PERSISTED', email in auth_routes.load_local_auth_users())

store = auth_routes.load_local_auth_users()
store.pop(email, None)
auth_routes.save_local_auth_users(store)
