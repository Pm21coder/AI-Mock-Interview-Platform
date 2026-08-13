# Razorpay Payment System E2E Testing Guide

## Critical: Payment System Testing Strategy

**Never test with real money. Always use Razorpay Test Mode.**

### Test Mode vs Live Mode

| Mode | Key ID Format | Use Case | Money Flow |
|------|---------------|----------|-----------|
| **Test** | `rzp_test_*` | Development/Staging | No real transactions |
| **Live** | `rzp_live_*` | Production | Real money transfers |

**Current Status:** Backend `.env` has `rzp_live_*` keys (REAL MONEY) - these need to be replaced with test keys for development.

---

## Phase 1: Local Testing

### 1.1 Get Razorpay Test Keys

1. Go to [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. **Settings → API Keys**
3. Switch toggle to **"Test Mode"** (at the top)
4. Copy **Key ID** (starts with `rzp_test_`)
5. Copy **Key Secret**

### 1.2 Configure Local Environment

**File:** `backend/.env`

```env
# Set to TEST keys for development
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_test_secret_key
RAZORPAY_CURRENCY=INR

# Frontend test key (public, safe to expose)
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
```

### 1.3 Test Payment Methods

Razorpay provides test payment methods for development:

**Successful Payments:**
- Card: `4111 1111 1111 1111` (any future expiry, any CVV)
- UPI: `success@razorpay`
- Netbanking: Choose any bank

**Failed Payments:**
- Card: `4222 2222 2222 2222`
- UPI: `fail@razorpay`

---

## Phase 2: Local E2E Payment Flow Test

### 2.1 Setup

```bash
# Terminal 1: Backend
cd mock-interview-platform/backend
python run.py

# Terminal 2: Frontend
cd mock-interview-platform/frontend
npm run dev
```

### 2.2 Test Flow: Free User → Upgrade to Basic

**Step 1: Register New Account**
```
1. Go to http://localhost:3000
2. Click "Sign Up"
3. Enter email: test-basic@example.com
4. Enter password: Test123456
5. Click "Create Account"
6. ✅ Should show dashboard with Free tier
```

**Step 2: Check Subscription Info**
```
1. Go to Settings → Subscription
2. ✅ Should show:
   - Current Plan: Free
   - Monthly Interviews: 3
   - Status: Active
```

**Step 3: Attempt Resume Upload (Should Fail)**
```
1. Go to Resume → Upload Resume
2. Try to upload a PDF
3. ✅ Should show error: "Resume review is only available on Pro plan"
```

**Step 4: Initiate Payment**
```
1. Go to Pricing or Subscription → Upgrade to Basic
2. Click "Upgrade" button
3. ✅ Should redirect to Razorpay checkout
```

**Step 5: Complete Payment**
```
1. On Razorpay checkout:
   - Amount: ₹375 (test amount for Basic)
   - Click "Pay Now"
2. Select payment method: Credit Card
3. Enter test card: 4111 1111 1111 1111
4. Expiry: any future date (e.g., 12/25)
5. CVV: any 3 digits (e.g., 123)
6. OTP (if asked): any 6 digits
7. ✅ Should show "Payment Successful"
```

**Step 6: Verify Subscription Upgraded**
```
1. After payment success, should redirect to dashboard
2. ✅ Check:
   - Current Plan: Basic
   - Monthly Interviews: 15
   - Status: Active
3. Go to Settings → Subscription
4. ✅ Should show new tier with updated limits
```

**Step 7: Verify Features Unlocked**
```
1. Go to Resume → Upload Resume
2. ✅ Should now allow upload (feature-gated correctly)
3. Go to Interview Setup → Create Interview
4. ✅ Should allow more than 3 interviews this month
```

### 2.3 Test Flow: Failed Payment

**Step 1: Start New Upgrade**
```
1. Login as Free tier user
2. Go to Upgrade → Pro
3. Click "Upgrade" button
```

**Step 2: Use Failing Test Card**
```
1. On Razorpay checkout:
   - Select Credit Card
2. Enter test card: 4222 2222 2222 2222
3. Enter any expiry and CVV
4. ✅ Should fail with error message
```

**Step 3: Verify Subscription Unchanged**
```
1. After payment failure
2. ✅ Check:
   - Still on Free tier
   - No features unlocked
   - Can retry payment
```

### 2.4 Test Edge Cases

#### Duplicate Payment Attempt
```
1. User clicks "Pay Now" → payment processes
2. User immediately clicks "Pay Now" again
3. ✅ Should prevent duplicate order creation
4. ✅ User should get message: "Payment already in progress"
```

#### Payment Cancellation
```
1. On Razorpay checkout
2. Click "Cancel" or back button
3. ✅ Should return to app without subscription upgrade
4. ✅ Tier remains unchanged
```

#### Browser Refresh During Payment
```
1. On Razorpay checkout
2. Refresh page (F5 or Cmd+R)
3. ✅ Should complete payment correctly
4. ✅ Order should not be duplicated
```

#### Network Timeout During Payment
```
1. Start payment
2. Simulate network loss (DevTools → Offline)
3. Wait for request timeout
4. ✅ Should show error: "Payment processing failed"
5. ✅ Should allow retry
6. Restore network
7. User should see correct final state
```

---

## Phase 3: Webhook Testing

Razorpay uses webhooks to notify your backend of payment results.

### 3.1 Test Webhook Locally

**Problem:** Localhost is not accessible from internet, so Razorpay cannot send webhooks.

**Solution:** Use ngrok to expose your local server:

```bash
# Install ngrok (if not installed)
# From https://ngrok.com/download

# In terminal:
ngrok http 5000

# Output:
# Forwarding   https://xxxx-yy-zz.ngrok-free.app -> http://localhost:5000
# Copy this URL
```

### 3.2 Configure Razorpay Webhook

1. Go to [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. **Settings → Webhooks**
3. Click **"Add New Webhook"**
4. **URL:** `https://xxxx-yy-zz.ngrok-free.app/api/webhook/razorpay`
5. **Events:** Check `payment.authorized`, `payment.failed`, `payment.captured`
6. Save webhook

### 3.3 Test Webhook Delivery

**Backend should receive:**

```json
{
  "event": "payment.authorized",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_xxxxx",
        "amount": 37500,
        "currency": "INR",
        "order_id": "order_xxxxx",
        "invoice_id": "inv_xxxxx",
        "international": false,
        "method": "card",
        "status": "authorized"
      }
    }
  }
}
```

Check backend logs:
```bash
tail -f backend/backend-dev.log | grep -i "payment\|webhook"
```

✅ Should see: `Webhook received for payment`

---

## Phase 4: Staging Testing (Render Deployment)

### 4.1 Configure Razorpay Webhook for Production

1. Razorpay Dashboard → **Webhooks**
2. Update webhook URL:
   ```
   https://your-api.onrender.com/api/webhook/razorpay
   ```

### 4.2 Test on Staging

1. Deploy frontend to Vercel
2. Deploy backend to Render
3. Set `NEXT_PUBLIC_API_URL` to Render backend URL in Vercel env

4. Go to deployed frontend: `https://your-app.vercel.app`
5. Register new account
6. Follow same payment flow as local testing
7. Use test payment methods (not real cards)

---

## Phase 5: Production Migration

### ⚠️ CRITICAL CHECKLIST

Before going live with real payments:

- [ ] **Keys Verified**
  - [ ] Live keys configured only in production
  - [ ] Test keys used in development/staging
  - [ ] No live keys in code or `.env` files

- [ ] **Signature Verification**
  - [ ] Backend validates Razorpay signature on every webhook
  - [ ] Signature key is kept secret (not in frontend)

- [ ] **Order Validation**
  - [ ] Backend validates order amount matches expected price
  - [ ] Backend validates order currency is correct
  - [ ] Prevents payment for modified amounts

- [ ] **Idempotency**
  - [ ] Duplicate webhooks don't create duplicate subscriptions
  - [ ] Webhook processing is idempotent

- [ ] **Error Handling**
  - [ ] Payment failures don't leave orphaned orders
  - [ ] User sees clear error message on failure
  - [ ] Admin can view failed payment attempts

- [ ] **Monitoring**
  - [ ] Payment logs captured
  - [ ] Failed payments alerted to admin
  - [ ] Webhook failures logged

### 5.1 Switch to Live Keys

**ONLY do this after completing all testing:**

1. Get Live Keys from [Razorpay Dashboard](https://dashboard.razorpay.com/)
   - Switch toggle to **"Live Mode"**
   - Copy live keys (start with `rzp_live_`)

2. Update production environment:
   - **Vercel:** Update `NEXT_PUBLIC_RAZORPAY_KEY_ID` (live key)
   - **Render:** Update `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` (live keys)

3. Redeploy

4. **First Live Payment:**
   - Use small test amount (₹1)
   - Use real card with small limit
   - Monitor logs closely
   - Verify subscription activated correctly

### 5.2 Live Payment Monitoring

After going live:

```bash
# Check Render logs for payment events
1. Render dashboard → Logs
2. Search for "payment" or "razorpay"
3. Look for errors or unexpected behavior

# Razorpay Dashboard
1. Dashboard → Transactions
2. Verify payment appears here
3. Check payment status
```

---

## Testing Checklist

Complete this before marking payment system as production-ready:

### Test Case 1: Successful Payment
- [ ] Register Free user
- [ ] Upgrade to Basic with test card `4111 1111 1111 1111`
- [ ] Payment succeeds
- [ ] Subscription activates immediately
- [ ] User can access Basic features
- [ ] Interview limit increases
- [ ] Dashboard shows new tier

### Test Case 2: Failed Payment
- [ ] Register Free user
- [ ] Attempt upgrade with failing card `4222 2222 2222 2222`
- [ ] Payment fails with error
- [ ] User stays on Free tier
- [ ] No subscription created
- [ ] User can retry payment

### Test Case 3: Payment Cancellation
- [ ] Start payment process
- [ ] Cancel before completion
- [ ] No subscription created
- [ ] User can retry

### Test Case 4: Duplicate Payment
- [ ] Start payment
- [ ] Quickly click Pay twice
- [ ] Only one payment processed
- [ ] Only one subscription created

### Test Case 5: Webhook Delivery
- [ ] Payment successful
- [ ] Backend receives webhook within 10 seconds
- [ ] Subscription status updates
- [ ] User immediately sees new tier

### Test Case 6: Database Transaction
- [ ] Payment succeeds
- [ ] Razorpay order saved to database
- [ ] Payment ID saved to database
- [ ] User subscription tier saved

### Test Case 7: Upgrade Existing User
- [ ] Basic user upgrades to Pro
- [ ] Payment succeeds
- [ ] Subscription updated from Basic to Pro
- [ ] Interview limit increases
- [ ] Additional Pro features available

### Test Case 8: Email Verification (if implemented)
- [ ] Verify confirmation email sent after payment
- [ ] Email contains order details
- [ ] Email contains transaction ID

---

## Common Razorpay Issues

| Issue | Error Message | Solution |
|-------|---------------|----------|
| Wrong key | `Invalid key id` | Verify `RAZORPAY_KEY_ID` is correct |
| Test vs Live mix | Payment fails with `Unauthorized` | Ensure all keys match (test or live) |
| Signature invalid | Webhook rejected | Verify `RAZORPAY_KEY_SECRET` matches |
| Amount mismatch | Payment declined | Verify amount in paise matches order |
| CORS error | Request blocked | Add your domain to Razorpay CORS settings |
| Webhook timeout | Payment succeeds but subscription doesn't | Check backend logs, verify webhook URL |

---

## References

- [Razorpay Documentation](https://razorpay.com/docs/)
- [Razorpay Test Cards](https://razorpay.com/docs/payment-gateway/test-cards/)
- [Razorpay Webhooks](https://razorpay.com/docs/webhooks/)
- [Razorpay Orders API](https://razorpay.com/docs/payment-gateway/orders/create/)
- [Razorpay Payments API](https://razorpay.com/docs/payment-gateway/payments/api/)
