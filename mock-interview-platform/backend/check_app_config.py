from app import create_app
app = create_app()
print('TESTING=', app.config.get('TESTING'))
print('MONGO_AVAILABLE=', app.config.get('MONGO_AVAILABLE'))
