import time
import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    # Ensure Redis is not required for tests
    app.config['REQUIRE_REDIS_IN_PRODUCTION'] = False
    return app


def test_analyze_job_requires_question_and_answer(app):
    with app.test_client() as client:
        resp = client.post('/api/interview/analyze-answer-job', json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert 'error' in data


def test_analyze_job_returns_job_id_and_completes(app):
    # Provide a minimal valid payload; in-process worker should handle this in tests
    payload = {
        'question': 'What is unit testing?',
        'answer': 'Unit testing verifies small units of code.',
        'expected_answer': 'Unit tests verify individual functions or classes.'
    }
    with app.test_client() as client:
        resp = client.post('/api/interview/analyze-answer-job', json=payload)
        assert resp.status_code == 202
        data = resp.get_json()
        assert data is not None
        assert 'job_id' in data
        job_id = data['job_id']

        # Poll the job endpoint until completed or timeout
        finished = False
        start = time.time()
        while time.time() - start < 5:  # wait up to 5s
            status_resp = client.get(f'/api/interview/job/{job_id}')
            assert status_resp.status_code in (200, 404)
            sdata = status_resp.get_json()
            if sdata is None:
                break
            if sdata.get('status') == 'completed':
                finished = True
                assert 'result' in sdata
                break
            if sdata.get('status') == 'failed':
                pytest.fail('Job failed: %s' % sdata.get('error'))
            time.sleep(0.2)

        assert finished, 'Analyze job did not complete within timeout'