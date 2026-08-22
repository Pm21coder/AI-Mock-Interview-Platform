import sys
sys.path.insert(0, 'c:\\Users\\dell\\OneDrive\\Desktop\\AI Mock Interview Platform\\mock-interview-platform\\backend')
from app import create_app, mongo
app = create_app()
print('App created')
with app.app_context():
    print('mongo object:', type(mongo))
    print('has cx:', hasattr(mongo, 'cx'))
    try:
        print('Attempting ping...')
        print(mongo.cx.admin.command('ping'))
        dbs = mongo.cx.list_database_names()
        print('Found databases:', dbs[:10])
    except Exception as e:
        print('Ping/list error:', type(e).__name__, str(e))
