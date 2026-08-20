import sys, os
# Ensure backend package root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

app = create_app()
print('FLASK_DEBUG (config):', app.config.get('FLASK_DEBUG'))
print('DEBUG (app.debug):', app.debug)
print('CORS_ORIGINS (type):', type(app.config.get('CORS_ORIGINS')))
print('CORS_ORIGINS (value):', app.config.get('CORS_ORIGINS'))
