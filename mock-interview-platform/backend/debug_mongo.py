import time
from app import create_app, mongo
from app.config import Config

app = create_app()
print('MONGO_AVAILABLE', app.config.get('MONGO_AVAILABLE'))
print('MONGO_URI', app.config.get('MONGO_URI'))

with app.app_context():
    start = time.time()
    try:
        print('count users start')
        count = mongo.db.users.count_documents({})
        print('count users result', count)
    except Exception as exc:
        print('count users error', type(exc).__name__, exc)
    print('elapsed', time.time() - start)
