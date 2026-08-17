from unittest.mock import patch
from app.routes import auth as auth_routes

with patch('app.routes.auth._mongo_available', return_value=False), patch('app.routes.auth.find_user', return_value=None):
    from app import create_app
    app = create_app()
    with app.test_client() as client:
        resp = client.post('/api/auth/register', json={'email':'new_cycle@example.com','password':'password123'})
        print('status', resp.status_code)
        print('json:', resp.get_json())
