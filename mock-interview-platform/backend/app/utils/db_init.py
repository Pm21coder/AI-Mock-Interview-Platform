"""MongoDB initialization and seeding for the mock interview platform.

Run this module directly to create collections, indexes, and seed data:

    python -m app.utils.db_init

It is safe to run multiple times (idempotent).
"""
from datetime import datetime, timedelta

from app import create_app, mongo
from app.utils.time import utc_now

# ---------------------------------------------------------------------------
# Collection definitions
# ---------------------------------------------------------------------------

COLLECTIONS = {
    'users': {
        'indexes': [
            {'key': [('email', 1)], 'unique': True, 'name': 'email_unique'},
        ],
    },
    'interviews': {
        'indexes': [
            {'key': [('user_id', 1), ('created_at', -1)], 'name': 'user_created_idx'},
            {'key': [('user_id', 1), ('responses', 1)], 'name': 'user_responses_idx'},
        ],
    },
    'responses': {
        'indexes': [
            {'key': [('user_id', 1), ('timestamp', -1)], 'name': 'user_timestamp_idx'},
            {'key': [('session_id', 1)], 'name': 'session_idx'},
        ],
    },
    'dashboard_stats': {
        'indexes': [
            {'key': [('user_id', 1)], 'unique': True, 'name': 'user_id_unique'},
            {'key': [('updated_at', -1)], 'name': 'updated_at_idx'},
        ],
    },
    'dashboard_processed_sessions': {
        'indexes': [
            {'key': [('session_id', 1), ('user_id', 1)], 'unique': True, 'name': 'session_user_unique'},
        ],
    },
}


def ensure_collections():
    """Create collections and their indexes if they do not exist."""
    for collection_name, spec in COLLECTIONS.items():
        if collection_name not in mongo.db.list_collection_names():
            mongo.db.create_collection(collection_name)
            print(f'Created collection: {collection_name}')

        for index_spec in spec['indexes']:
            try:
                mongo.db[collection_name].create_index(
                    index_spec['key'],
                    unique=index_spec.get('unique', False),
                    name=index_spec['name'],
                )
                print(f'  Index ensured: {collection_name}.{index_spec["name"]}')
            except Exception as exc:
                print(f'  Index warning ({collection_name}.{index_spec["name"]}): {exc}')


def seed_demo_user():
    """Create a demo user if none exists."""
    existing = mongo.db.users.find_one({'email': 'demo@mockinterview.app'})
    if existing:
        print('Demo user already exists, skipping.')
        return existing

    import bcrypt

    demo_user = {
        'email': 'demo@mockinterview.app',
        'password_hash': bcrypt.hashpw(b'demo12345', bcrypt.gensalt()).decode('utf-8'),
        'created_at': utc_now(),
    }
    try:
        result = mongo.db.users.insert_one(demo_user)
        print(f'Created demo user: demo@mockinterview.app (id={result.inserted_id})')
        return demo_user
    except Exception as exc:
        print(f'Failed to create demo user: {exc}')
        return None


def seed_demo_interviews(user_id, count=5):
    """Seed sample completed interviews for the demo user."""
    existing = mongo.db.interviews.count_documents({'user_id': user_id, 'responses': {'$ne': []}})
    if existing > 0:
        print(f'Demo user already has {existing} completed interviews, skipping seed.')
        return

    roles = [
        ('Software Engineer', 88, 0.90),
        ('Product Manager', 79, 0.85),
        ('Data Analyst', 91, 0.92),
        ('UX Designer', 75, 0.80),
        ('DevOps Engineer', 85, 0.88),
    ]

    for i, (role, score, confidence) in enumerate(roles):
        created_at = utc_now() - timedelta(days=i * 5)
        interview = {
            '_id': f'demo_seed_{i}',
            'user_id': user_id,
            'job_role': role,
            'questions': [
                {
                    'question': f'Tell me about your experience as a {role}.',
                    'category': 'technical',
                    'difficulty': 'medium',
                    'expected_answer': 'Sample expected answer.',
                }
            ],
            'created_at': created_at,
            'responses': [
                {
                    'question_index': 0,
                    'answer': f'Sample answer for {role} interview.',
                    'feedback': {
                        'gemini_feedback': {
                            'overall_score': score,
                            'content_score': score - 2,
                            'structure_score': score - 1,
                            'clarity_score': score + 1,
                            'strengths': ['Clear communication', 'Technical depth'],
                            'improvements': ['Be more concise', 'Add more examples'],
                            'detailed_feedback': 'Good performance overall.',
                        },
                        'cv_analysis': {
                            'average_confidence': confidence,
                            'overall_assessment': 'Good visual presence',
                            'total_frames_analyzed': 120,
                        },
                        'timestamp': created_at.isoformat(),
                    },
                }
            ],
            'feedback': [],
        }
        mongo.db.interviews.insert_one(interview)
        print(f'  Seeded interview: {role} (score={score})')


def seed_dashboard_stats(user_id):
    """Rebuild dashboard stats for the demo user from seeded interviews."""
    from app.services.dashboard_service import DashboardService

    service = DashboardService()
    stats = service.rebuild_from_interviews(user_id)
    print(
        f'Dashboard stats seeded for demo user: '
        f'{stats.interviews_completed} interviews, '
        f'avg score={stats.average_score}, '
        f'avg confidence={stats.confidence_score}'
    )


def run():
    """Run the full initialization sequence."""
    app = create_app()
    with app.app_context():
        print('=== MongoDB Initialization ===')
        ensure_collections()

        demo_user = seed_demo_user()
        if demo_user:
            user_id = str(demo_user['_id'])
            seed_demo_interviews(user_id)
            seed_dashboard_stats(user_id)

        print('=== Initialization complete ===')


if __name__ == '__main__':
    run()
