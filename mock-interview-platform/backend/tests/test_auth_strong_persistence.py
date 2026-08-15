import json
from unittest.mock import patch

from app import create_app
from app.routes import auth as auth_routes


def _reset_user(email):
    auth_routes.local_auth_users.pop(email, None)
    store = auth_routes.load_local_auth_users()
    store.pop(email, None)
    auth_routes.save_local_auth_users(store)


def test_register_rejects_weak_password():
    email = 'weakpassword@example.com'
    _reset_user(email)

    app = create_app()
    with app.test_client() as client:
        response = client.post('/api/auth/register', json={
            'email': email,
            'password': 'Password123',
        })

    assert response.status_code == 400
    assert 'strong' in response.get_json()['error'].lower()


def test_register_persists_account_for_future_login():
    email = 'persistentuser@example.com'
    password = 'StrongPass!123'
    _reset_user(email)

    app = create_app()
    with app.test_client() as client:
        register_response = client.post('/api/auth/register', json={
            'email': email,
            'password': password,
        })
        assert register_response.status_code == 201

        auth_routes.local_auth_users.clear()
        auth_routes.local_auth_users.update(auth_routes.load_local_auth_users())

        login_response = client.post('/api/auth/login', json={
            'email': email,
            'password': password,
        })

    assert login_response.status_code == 200
    assert login_response.get_json()['user']['email'] == email
    assert email in auth_routes.load_local_auth_users()

    _reset_user(email)
