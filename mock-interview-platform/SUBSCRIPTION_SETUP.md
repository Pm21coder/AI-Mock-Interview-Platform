# Subscription System Setup Guide

This guide will help you set up the monthly subscription system with Stripe integration.

## Overview

The subscription system includes:
- **Free Tier**: 3 interviews/month with basic features
- **Basic Plan**: $9/month with 15 interviews and advanced features
- **Pro Plan**: $19/month with unlimited interviews and premium features

## Prerequisites

1. Stripe account (https://stripe.com)
2. MongoDB database running
3. Backend and frontend environments configured

## Step 1: Stripe Setup

### 1.1 Create Stripe Products and Prices

1. Log in to your Stripe Dashboard
2. Go to **Products** → **Add Product**
3. Create **Basic Plan**:
   - Name: `Basic Plan`
   - Price: `$9.00/month`
   - Copy the **Price ID** (starts with `price_`)
4. Create **Pro Plan**:
   - Name: `Pro Plan`
   - Price: `$19.00/month`
   - Copy the **Price ID** (starts with `price_`)

### 1.2 Get Stripe API Keys

1. Go to **Developers** → **API Keys**
2. Copy your **Secret Key** (starts with `sk_test_` or `sk_live_`)
3. Copy your **Publishable Key** (starts with `pk_test_` or `pk_live_`)

### 1.3 Set Up Webhook

1. Go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Endpoint URL: `https://your-domain.com/api/subscription/webhook`
4. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the **Webhook Secret** (starts with `whsec_`)

## Step 2: Environment Configuration

### 2.1 Backend Environment Variables

Add these to your `mock-interview-platform/backend/.env` file:

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Stripe Price IDs
STRIPE_BASIC_PRICE_ID=price_your_basic_price_id_here
STRIPE_PRO_PRICE_ID=price_your_pro_price_id_here

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

### 2.2 Frontend Environment Variables

Add this to your `mock-interview-platform/frontend/.env.local` file:

```env
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Step 3: Install Dependencies

### Backend

```bash
cd mock-interview-platform/backend
pip install -r requirements.txt
```

The `stripe>=7.0` package has been added to handle payment processing.

### Frontend

```bash
cd mock-interview-platform/frontend
npm install
```

## Step 4: Database Migration

The subscription fields have been added to the User model. For existing users, you need to add default values:

```javascript
// Run this in MongoDB shell or create a migration script
db.users.updateMany(
  {},
  {
    $set: {
      subscription_tier: 'free',
      subscription_status: 'active',
      interviews_used_this_month: 0
    }
  }
)
```

## Step 5: Run the Application

### Start Backend

```bash
cd mock-interview-platform/backend
python run.py
```

The backend will run on `http://localhost:5000`

### Start Frontend

```bash
cd mock-interview-platform/frontend
npm run dev
```

The frontend will run on `http://localhost:3000`

## Step 6: Test the Subscription Flow

1. **Register/Login**: Create an account or log in
2. **Visit Pricing Page**: Navigate to `/subscription`
3. **Select Plan**: Click "Upgrade to Basic" or "Upgrade to Pro"
4. **Complete Payment**: Use Stripe test card:
   - Card Number: `4242 4242 4242 4242`
   - Expiry: Any future date
   - CVC: Any 3 digits
5. **Verify Subscription**: Check that subscription status updates
6. **Test Interview Limit**: Try creating interviews to verify limits work

## Step 7: Production Deployment

### 7.1 Update Environment Variables

For production, update:
- `STRIPE_SECRET_KEY` → Use live key (`sk_live_...`)
- `STRIPE_PUBLISHABLE_KEY` → Use live key (`pk_live_...`)
- `FRONTEND_URL` → Your production domain
- Webhook URL → Your production domain

### 7.2 Configure Webhook in Stripe

Update the webhook endpoint URL to your production domain:
```
https://your-domain.com/api/subscription/webhook
```

### 7.3 Deploy Backend

The backend can be deployed to:
- Render (see `render.yaml`)
- AWS EC2
- Google Cloud Run
- Any Python-compatible hosting

### 7.4 Deploy Frontend

The frontend can be deployed to:
- Vercel (recommended for Next.js)
- Netlify
- AWS Amplify

## Features Implemented

### Backend
- ✅ User model with subscription fields
- ✅ Subscription API endpoints:
  - `GET /api/subscription/plans` - Get all plans
  - `GET /api/subscription/status` - Get user subscription status
  - `POST /api/subscription/create-checkout-session` - Create Stripe checkout
  - `POST /api/subscription/webhook` - Handle Stripe webhooks
  - `POST /api/subscription/cancel` - Cancel subscription
  - `POST /api/subscription/reactivate` - Reactivate subscription
  - `POST /api/subscription/portal` - Stripe customer portal
- ✅ Interview limit enforcement
- ✅ Automatic monthly usage reset
- ✅ Webhook handling for subscription events

### Frontend
- ✅ Pricing page (`/subscription`)
- ✅ Success page (`/subscription/success`)
- ✅ Subscription status display
- ✅ Navigation link to pricing
- ✅ API functions for subscription operations
- ✅ Responsive design with Tailwind CSS

### Subscription Tiers

**Free Tier ($0/month)**
- 3 mock interviews per month
- Basic AI feedback
- Standard question categories
- 7-day feedback history

**Basic Plan ($9/month)**
- 15 mock interviews per month
- Advanced AI feedback
- All question categories
- Unlimited feedback history
- Video recording analysis
- Email support

**Pro Plan ($19/month)**
- Unlimited mock interviews
- Premium AI coaching
- Custom interview scenarios
- Advanced analytics dashboard
- Priority support
- Resume review integration

## Testing with Stripe

Use these test card numbers:
- **Success**: `4242 4242 4242 4242`
- **Declined**: `4000 0000 0000 0002`
- **Requires Authentication**: `4000 0025 0000 3155`

## Troubleshooting

### Webhook Not Working
- Ensure webhook URL is publicly accessible
- Check webhook secret matches in `.env`
- Verify webhook events are selected in Stripe dashboard
- Check backend logs for webhook errors

### Payment Fails
- Verify Stripe keys are correct
- Check if using test mode vs live mode
- Ensure price IDs match in Stripe dashboard

### Subscription Not Updating
- Check MongoDB connection
- Verify user ID is being passed correctly
- Check webhook logs in Stripe dashboard

## Security Considerations

1. **Never expose Stripe Secret Key** in frontend code
2. **Always verify webhook signatures** using `STRIPE_WEBHOOK_SECRET`
3. **Use HTTPS** in production
4. **Validate user authentication** on all subscription endpoints
5. **Store sensitive data** (customer IDs) securely in database

## Support

For issues or questions:
- Check Stripe documentation: https://stripe.com/docs
- Review backend logs for errors
- Check browser console for frontend errors