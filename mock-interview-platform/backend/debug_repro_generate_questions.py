import traceback
from app import create_app

try:
    app = create_app()
    with app.test_client() as client:
        resp = client.post('/api/interview/generate-questions', json={
            'job_role': 'Software Engineer',
            'category': 'technical',
            'difficulty': 'medium',
            'num_questions': 3,
        })
        print('status', resp.status_code)
        try:
            print('json:', resp.get_json())
        except Exception as e:
            print('could not decode json, raw:', resp.data)
except Exception:
    traceback.print_exc()
