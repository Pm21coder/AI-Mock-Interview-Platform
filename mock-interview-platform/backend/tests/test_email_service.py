import os

from app import create_app


def test_contact_email_route_fails_when_gmail_is_not_configured(monkeypatch):
    monkeypatch.delenv('GMAIL_USER', raising=False)
    monkeypatch.delenv('GMAIL_APP_PASSWORD', raising=False)

    app = create_app()
    with app.test_client() as client:
        response = client.post('/api/send-email', json={
            'name': 'Test User',
            'email': 'user@example.com',
            'subject': 'Hello',
            'message': 'This is a test message.'
        })

    assert response.status_code == 503
    payload = response.get_json()
    assert 'configured' in payload['error'].lower()
