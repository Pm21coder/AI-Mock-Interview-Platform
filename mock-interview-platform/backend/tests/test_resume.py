from unittest import TestCase
from unittest.mock import patch

from bson import ObjectId
from flask import Flask, request

from app.routes.resume import get_resume_analysis, upload_resume


class ResumeUploadTests(TestCase):
    def test_upload_checks_feature_access_with_the_native_mongo_user_id(self):
        """A Pro user must not be treated as Free due to an ObjectId/string mismatch."""
        user_id = ObjectId()
        app = Flask(__name__)

        with patch(
            'app.routes.resume.subscription_service.has_feature',
            return_value=False,
        ) as has_feature:
            with app.test_request_context('/api/resume/upload', method='POST'):
                request.current_user = {'_id': user_id}
                response, status_code = upload_resume.__wrapped__()

        self.assertEqual(status_code, 403)
        self.assertEqual(response.get_json()['required_tier'], 'pro')
        has_feature.assert_called_once_with(user_id, 'resume_review')

    def test_analysis_rejects_a_missing_or_invalid_resume_id(self):
        app = Flask(__name__)

        with app.test_request_context('/api/resume/analysis/undefined'):
            request.current_user = {'_id': 'guest'}
            response, status_code = get_resume_analysis.__wrapped__('undefined')

        self.assertEqual(status_code, 400)
        self.assertEqual(response.get_json()['error'], 'A valid resume ID is required')
