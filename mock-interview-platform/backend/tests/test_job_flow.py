import time
from unittest import TestCase
from unittest.mock import patch
from flask import Flask, request

from app.routes.interview import generate_questions_job, get_job_status


class JobFlowTests(TestCase):
    def setUp(self):
        self.app = Flask(__name__)

    def test_generate_questions_job_enqueues_and_completes(self):
        # Patch the job runner to return a completed result immediately
        completed_result = {'status': 'completed', 'result': {'session_id': 'test_session', 'questions': [{'question': 'Q1', 'expected_answer': 'A1'}]}}
        with patch('app.routes.interview.run_generate_questions_job', return_value=completed_result):
            with self.app.test_request_context('/api/interview/generate-questions-job', method='POST', json={'job_role': 'SE', 'category': 'technical', 'difficulty': 'medium', 'num_questions': 1}):
                # The endpoint should return a 202 and a job id
                resp = generate_questions_job.__wrapped__()
                self.assertEqual(resp.status_code, 202)
                job_id = resp.get_json().get('job_id')
                self.assertTrue(job_id)

                # Poll the job status until completed (thread updates jobs store)
                start = time.time()
                status = None
                while time.time() - start < 5:
                    with self.app.test_request_context(f'/api/interview/job/{job_id}', method='GET'):
                        request.current_user = {'_id': 'guest'}
                        status_resp = get_job_status.__wrapped__(job_id)
                        # The view may return a (response, status) tuple in some branches
                        if isinstance(status_resp, tuple):
                            body, code = status_resp
                            data = body.get_json()
                        else:
                            data = status_resp.get_json()
                        status = data.get('status')
                        if status == 'completed':
                            break
                    time.sleep(0.1)
                self.assertEqual(status, 'completed')

    def test_generate_questions_job_fails(self):
        # Patch the job runner to return a failed result
        failed_result = {'status': 'failed', 'error': 'LLM crashed'}
        with patch('app.routes.interview.run_generate_questions_job', return_value=failed_result):
            with self.app.test_request_context('/api/interview/generate-questions-job', method='POST', json={'job_role': 'SE', 'category': 'technical', 'difficulty': 'medium', 'num_questions': 1}):
                resp = generate_questions_job.__wrapped__()
                self.assertEqual(resp.status_code, 202)
                job_id = resp.get_json().get('job_id')
                self.assertTrue(job_id)

                # Poll until failed status is observed
                start = time.time()
                status = None
                while time.time() - start < 5:
                    with self.app.test_request_context(f'/api/interview/job/{job_id}', method='GET'):
                        request.current_user = {'_id': 'guest'}
                        status_resp = get_job_status.__wrapped__(job_id)
                        if isinstance(status_resp, tuple):
                            body, code = status_resp
                            data = body.get_json()
                        else:
                            data = status_resp.get_json()
                        status = data.get('status')
                        if status == 'failed':
                            self.assertEqual(data.get('error'), 'LLM crashed')
                            break
                    time.sleep(0.1)
                self.assertEqual(status, 'failed')

    def test_generate_questions_job_missing_job_returns_404(self):
        with self.app.test_request_context('/api/interview/job/notfound', method='GET'):
            request.current_user = {'_id': 'guest'}
            resp = get_job_status.__wrapped__('nonexistent_job')
            # Expect a tuple (response, status)
            self.assertIsInstance(resp, tuple)
            body, code = resp
            self.assertEqual(code, 404)
            self.assertEqual(body.get_json().get('error'), 'Job not found')
