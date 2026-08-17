import time
from unittest import TestCase
from unittest.mock import patch
from datetime import timedelta

from bson import ObjectId
from flask import Flask, request

from app.routes.interview import generate_questions
from app.services.gemini_service import GeminiService
from app.services.subscription_service import SubscriptionService, fallback_subscriptions
from app.utils.time import utc_now


class InterviewQuestionRouteTests(TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.user_id = ObjectId()

    def test_question_generation_uses_the_native_user_id_for_plan_checks(self):
        with patch(
            'app.routes.interview.subscription_service.check_interview_limit',
            return_value=(True, None),
        ) as check_limit, patch(
            'app.routes.interview.subscription_service.get_available_question_categories',
            return_value=['technical', 'behavioral'],
        ) as get_categories, patch(
            'app.routes.interview.subscription_service.increment_interview_count',
        ) as increment_count, patch(
            'app.routes.interview.subscription_service.get_user_subscription',
            return_value={
                'tier': 'free',
                'interviews_used_this_month': 1,
                'interviews_remaining': 2,
                'monthly_limit': 3,
            },
        ), patch(
            'app.routes.interview.emit_interview_usage_update',
        ) as emit_usage_update, patch(
            'app.routes.interview.gemini_service.generate_questions',
            return_value=[{
                'question': 'How do you design a reliable API?',
                'expected_answer': 'Use clear contracts, tests, and monitoring.',
            }],
        ):
            with self.app.test_request_context(
                '/api/interview/generate-questions',
                method='POST',
                json={
                    'job_role': 'Software Engineer',
                    'category': 'technical',
                    'difficulty': 'medium',
                    'num_questions': 1,
                },
            ):
                request.current_user = {'_id': self.user_id}
                response = generate_questions.__wrapped__()

        self.assertEqual(response.status_code, 200)
        check_limit.assert_called_once_with(self.user_id)
        get_categories.assert_called_once_with(self.user_id)
        increment_count.assert_called_once_with(self.user_id)
        emit_usage_update.assert_called_once_with(
            str(self.user_id),
            {
                'tier': 'free',
                'interviews_used_this_month': 1,
                'interviews_remaining': 2,
                'monthly_limit': 3,
            },
            response.get_json()['session_id'],
        )

    def test_restricted_category_returns_a_structured_upgrade_response(self):
        with patch(
            'app.routes.interview.subscription_service.check_interview_limit',
            return_value=(True, None),
        ), patch(
            'app.routes.interview.subscription_service.get_available_question_categories',
            return_value=['technical', 'behavioral'],
        ), patch(
            'app.routes.interview.subscription_service.get_user_subscription',
            return_value={'tier': 'free'},
        ):
            with self.app.test_request_context(
                '/api/interview/generate-questions',
                method='POST',
                json={
                    'job_role': 'Software Engineer',
                    'category': 'situational',
                },
            ):
                request.current_user = {'_id': self.user_id}
                response, status_code = generate_questions.__wrapped__()

        self.assertEqual(status_code, 403)
        self.assertEqual(response.get_json()['code'], 'category_not_in_plan')
        self.assertEqual(response.get_json()['required_tier'], 'basic')

    def test_quota_exhaustion_returns_an_upgrade_response_before_generation(self):
        limit_error = {
            'error': 'Monthly interview limit reached',
            'code': 'interview_limit_reached',
            'upgrade_url': '/subscription',
        }
        with patch(
            'app.routes.interview.subscription_service.check_interview_limit',
            return_value=(False, limit_error),
        ), patch(
            'app.routes.interview.gemini_service.generate_questions',
        ) as generate_questions_mock:
            with self.app.test_request_context(
                '/api/interview/generate-questions',
                method='POST',
                json={
                    'job_role': 'Software Engineer',
                    'category': 'technical',
                },
            ):
                request.current_user = {'_id': self.user_id}
                response, status_code = generate_questions.__wrapped__()

        self.assertEqual(status_code, 403)
        self.assertEqual(response.get_json()['code'], 'interview_limit_reached')
        generate_questions_mock.assert_not_called()


class SubscriptionFallbackTests(TestCase):
    def tearDown(self):
        fallback_subscriptions.clear()

    def test_local_paid_plan_is_available_to_feature_checks_and_usage_limits(self):
        fallback_subscriptions['demo_user'] = {
            'tier': 'basic',
            'status': 'active',
            'interviews_used_this_month': 14,
        }
        subscription_service = SubscriptionService()

        with patch('app.services.subscription_service.mongo') as mock_mongo:
            mock_mongo.db.users.find_one.return_value = None
            subscription = subscription_service.get_user_subscription('demo_user')
            can_proceed, error = subscription_service.check_interview_limit('demo_user')
            new_count = subscription_service.increment_interview_count('demo_user')
            can_proceed_after_limit, limit_error = subscription_service.check_interview_limit(
                'demo_user',
            )

        self.assertEqual(subscription['tier'], 'basic')
        self.assertEqual(subscription['interviews_remaining'], 1)
        self.assertTrue(can_proceed)
        self.assertIsNone(error)
        self.assertEqual(new_count, 15)
        self.assertFalse(can_proceed_after_limit)
        self.assertEqual(limit_error['code'], 'interview_limit_reached')
        self.assertEqual(limit_error['required_tier'], 'pro')

    def test_local_auth_account_persists_and_recovers_interview_usage(self):
        user_id = 'demo_local_usage'
        users = {
            'local@example.com': {
                '_id': user_id,
                'email': 'local@example.com',
                'subscription_tier': 'free',
                'subscription_status': 'active',
                'subscription_start_date': utc_now() - timedelta(days=1),
                'subscription_end_date': utc_now() + timedelta(days=29),
                'interviews_used_this_month': 0,
            }
        }
        subscription_service = SubscriptionService()

        with patch('app.services.subscription_service.mongo') as mock_mongo, \
             patch('app.routes.auth.load_local_auth_users', return_value=users), \
             patch('app.routes.auth.save_local_auth_users') as save_local_users:
            mock_mongo.db.users.find_one.return_value = None
            mock_mongo.db.interviews.count_documents.return_value = 2

            subscription = subscription_service.get_user_subscription(user_id)
            new_count = subscription_service.increment_interview_count(user_id)

        self.assertEqual(subscription['interviews_used_this_month'], 2)
        self.assertEqual(subscription['interviews_remaining'], 1)
        self.assertEqual(new_count, 3)
        self.assertEqual(users['local@example.com']['interviews_used_this_month'], 3)
        save_local_users.assert_called()


class GeminiFallbackTests(TestCase):
    def test_run_with_timeout_uses_the_configured_deadline(self):
        start = time.time()

        with self.assertRaises(TimeoutError):
            GeminiService.run_with_timeout(
                lambda: (time.sleep(0.2), 'done'),
                timeout_seconds=0.05,
            )

        self.assertLess(time.time() - start, 0.2)

    def test_question_fallback_returns_the_requested_number_of_questions(self):
        questions = GeminiService().get_fallback_questions(
            'Software Engineer',
            'behavioral',
            num_questions=5,
        )

        self.assertEqual(len(questions), 5)
        self.assertTrue(all(question['question'] for question in questions))
