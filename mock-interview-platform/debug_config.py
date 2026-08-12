from app import create_app
app = create_app()
print('MONGO_AVAILABLE=', app.config.get('MONGO_AVAILABLE'))
print('MONGO_URI=', app.config.get('MONGO_URI'))
print('JWT_SECRET_KEY=', app.config.get('JWT_SECRET_KEY'))
print('RAZORPAY_KEY_ID=', app.config.get('RAZORPAY_KEY_ID'))
print('RAZORPAY_KEY_SECRET=', bool(app.config.get('RAZORPAY_KEY_SECRET')))
