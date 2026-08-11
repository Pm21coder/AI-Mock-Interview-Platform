# UPI Payment Integration Setup

This document explains how to set up and use the UPI payment system for Indian users.

## Overview

The platform now supports two payment methods:
1. **Stripe** - For international users (credit/debit cards)
2. **UPI** - For Indian users (UPI ID/QR code payment)

## UPI Configuration

### Current Settings

The UPI payment is configured with the following details (in `backend/app/config.py`):

```python
UPI_ID = '9156727375@pthdfc'
UPI_NAME = 'Pramod Ulhas Mane'
```

### Changing UPI Details

To update the UPI ID and name, you can either:

1. **Update in code** (hardcoded):
   - Edit `backend/app/config.py`
   - Change `UPI_ID` and `UPI_NAME` values

2. **Use environment variables** (recommended for production):
   - Add to `backend/.env`:
   ```env
   UPI_ID=your-upi-id@upi
   UPI_NAME=Your Name
   ```

## How UPI Payment Works

### User Flow

1. User visits `/subscription` page
2. Selects a plan (Basic $9/month or Pro $19/month)
3. Clicks "Pay with UPI" button
4. Modal opens showing:
   - Selected plan and amount in INR
   - UPI ID to pay
   - Payment instructions
5. User pays via any UPI app (Paytm, GPay, PhonePe, BHIM)
6. User enters the transaction ID
7. Clicks "Submit Payment"
8. Payment request is stored for verification
9. Admin verifies payment and activates subscription

### API Endpoints

#### 1. Get UPI Information
```
GET /api/subscription/upi-info
```

**Response:**
```json
{
  "upi_id": "9156727375@pthdfc",
  "upi_name": "Pramod Ulhas Mane",
  "plans": {
    "basic": {
      "name": "Basic Plan",
      "price": 9,
      "currency": "USD",
      "upi_amount": "₹750"
    },
    "pro": {
      "name": "Pro Plan",
      "price": 19,
      "currency": "USD",
      "upi_amount": "₹1580"
    }
  }
}
```

#### 2. Submit UPI Payment
```
POST /api/subscription/upi-payment
Headers: Authorization: Bearer <token>
Body: {
  "tier": "basic",
  "transaction_id": "123456789012"
}
```

**Response:**
```json
{
  "message": "Payment request submitted successfully",
  "status": "pending_verification",
  "transaction_id": "123456789012",
  "upi_id": "9156727375@pthdfc",
  "tier": "basic",
  "note": "Your subscription will be activated within 24 hours after payment verification"
}
```

## Payment Verification (Admin Task)

### Current Implementation

Currently, UPI payments are stored in a `pending_payments` collection in MongoDB with status `pending_verification`. 

### Verification Process

To verify and activate subscriptions:

1. **Check your payment gateway/bank account** for received payments
2. **Match transaction IDs** in the `pending_payments` collection
3. **Update user subscription** manually or create an admin endpoint:

```python
# Example admin endpoint (add to subscription.py)
@subscription_bp.route('/admin/verify-upi-payment', methods=['POST'])
@token_required
def verify_upi_payment(current_user):
    # Add admin check here
    data = request.get_json(silent=True) or {}
    transaction_id = data.get('transaction_id')
    action = data.get('action')  # 'approve' or 'reject'
    
    payment = mongo.db.pending_payments.find_one({'transaction_id': transaction_id})
    
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    
    if action == 'approve':
        # Activate subscription
        mongo.db.users.update_one(
            {'_id': payment['user_id']},
            {
                '$set': {
                    'subscription_tier': payment['tier'],
                    'subscription_status': 'active',
                    'subscription_start_date': datetime.utcnow(),
                    'subscription_end_date': datetime.utcnow() + timedelta(days=30),
                    'interviews_used_this_month': 0
                }
            }
        )
        
        # Update payment status
        mongo.db.pending_payments.update_one(
            {'transaction_id': transaction_id},
            {'$set': {'status': 'approved', 'verified_at': datetime.utcnow()}}
        )
        
        return jsonify({'message': 'Payment approved and subscription activated'}), 200
    
    elif action == 'reject':
        mongo.db.pending_payments.update_one(
            {'transaction_id': transaction_id},
            {'$set': {'status': 'rejected', 'verified_at': datetime.utcnow()}}
        )
        return jsonify({'message': 'Payment rejected'}), 200
```

## Frontend Features

### UPI Payment Modal

When a user clicks "Pay with UPI":
- Modal displays selected plan and INR amount
- Shows UPI ID: `9156727375@pthdfc`
- Provides step-by-step payment instructions
- Input field for transaction ID
- Submit button to record payment

### User Experience

1. **Clear Instructions**: Step-by-step guide on how to pay
2. **Amount Display**: Shows approximate INR amount
3. **Transaction ID**: Required field for verification
4. **Confirmation**: Alert message after submission
5. **Status**: User is notified that subscription will be activated within 24 hours

## Amount Conversion

Current approximate conversions (update as needed):
- Basic Plan: $9 USD ≈ ₹750 INR
- Pro Plan: $19 USD ≈ ₹1580 INR

**Note**: These are approximate amounts. You should:
- Update based on current exchange rates
- Consider adding a small buffer for currency fluctuations
- Or set fixed INR prices

## Production Considerations

### 1. Payment Gateway Integration

For automated verification, integrate with:
- **Razorpay** (recommended for India)
- **PayU**
- **Instamojo**
- **Cashfree**

These provide:
- Automatic payment verification
- Webhook notifications
- Refund management
- Payment analytics

### 2. Security

- Never trust client-side transaction IDs
- Always verify with payment gateway
- Use webhooks for real-time verification
- Implement rate limiting on payment endpoints
- Add CAPTCHA to prevent abuse

### 3. User Communication

- Send email confirmation after payment submission
- Notify user when subscription is activated
- Send reminders for failed/expired payments
- Provide payment receipt

### 4. Admin Dashboard

Create an admin panel to:
- View pending payments
- Verify/reject payments
- Manually activate subscriptions
- View payment history
- Generate reports

## Testing

### Test the UPI Flow

1. **Visit**: http://localhost:3000/subscription
2. **Select Plan**: Choose Basic or Pro
3. **Click**: "Pay with UPI" button
4. **Modal Opens**: Shows UPI details
5. **Make Payment**: Use any UPI app to pay
6. **Enter Transaction ID**: Copy from payment app
7. **Submit**: Click "Submit Payment"
8. **Confirmation**: See success message

### Test Data

You can use any UPI app with test mode or make a small real payment for testing.

## Troubleshooting

### Payment Not Showing in Database

- Check MongoDB connection
- Verify user is authenticated
- Check backend logs for errors

### Transaction ID Not Accepted

- Ensure transaction ID is not empty
- Check for duplicate transaction IDs
- Verify format matches your payment gateway

### Subscription Not Activated

- Payment must be manually verified (or integrate payment gateway)
- Check `pending_payments` collection
- Verify transaction ID matches payment record

## Migration from Stripe Only

If you already have users on Stripe:
1. Existing Stripe subscriptions continue to work
2. New users can choose either Stripe or UPI
3. Users can switch payment methods by canceling and re-subscribing
4. All subscription data is stored in the same `users` collection

## Support

For UPI payment issues:
- Check backend logs
- Verify MongoDB connection
- Review pending_payments collection
- Contact payment gateway support if integrated