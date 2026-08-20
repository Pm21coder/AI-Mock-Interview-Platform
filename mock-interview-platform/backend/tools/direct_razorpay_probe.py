import os
import razorpay

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

key = os.getenv('RAZORPAY_KEY_ID')
secret = os.getenv('RAZORPAY_KEY_SECRET')
print('Using key:', key)
client = razorpay.Client(auth=(key, secret))
try:
    order = client.order.create(data={
        'amount': 100,
        'currency': 'INR',
        'receipt': 'test_receipt',
        'payment_capture': 1,
    }, timeout=10)
    print('Order created:', order)
except Exception as e:
    print('Razorpay probe failed:', type(e), e)
    import traceback
    traceback.print_exc()
