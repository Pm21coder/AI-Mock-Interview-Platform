# Deployment Guide for Your Actual Repository

**Only proceed after completing:** `GITHUB_SECURITY_FIX.md` ✓

This guide is based on your actual GitHub repository structure:

```
AI-Mock-Interview-Platform/
├── mock-interview-platform/
│   ├── backend/          (Flask + Socket.IO)
│   ├── frontend/         (Next.js + React 19)
│   ├── DEPLOYMENT_GUIDE_START_HERE.md
│   ├── render.yaml       (Already configured)
│   └── [other docs]
```

---

## Part 1: Verify MongoDB Atlas

### Step 1: Create or Access MongoDB Cluster

Go to: [MongoDB Atlas](https://cloud.mongodb.com)

You need:
- **Cluster name:** ai-mock-interview-prod (or similar)
- **Region:** Your region
- **Tier:** M0 (free) is fine for testing
- **Database:** mock_interview
- **User:** mock_interview_admin
- **Password:** Strong password (saved securely)

### Step 2: Get Connection String

From MongoDB Atlas:

1. Click your cluster → **Connect**
2. Choose **Connect Your Application**
3. Copy the connection string

Format:
```
mongodb+srv://mock_interview_admin:PASSWORD@cluster0.xxxxx.mongodb.net/mock_interview?retryWrites=true&w=majority
```

**Save this - you'll need it for Render.**

### Step 3: Whitelist Render's IPs

MongoDB Atlas → **Network Access**

Add:
```
0.0.0.0/0
```

This allows Render to connect from anywhere.

---

## Part 2: Deploy Backend to Render

### Step 1: Open Render Dashboard

Go to: [Render Dashboard](https://render.com/dashboard)

Click: **New +** → **Web Service**

### Step 2: Connect GitHub

Click: **Connect Account** → Link your GitHub

Find and select: `Pm21coder/AI-Mock-Interview-Platform`

### Step 3: Configure Render Service

**Name:** `ai-mock-interview-api`

**Branch:** `main`

**Root Directory:** `mock-interview-platform/backend`  
*(This is critical - your repo has backend in a subdirectory)*

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
gunicorn --workers 1 --threads 100 --worker-class gthread --bind 0.0.0.0:$PORT run:app
```

**Plan:** Free (or Paid if you need better uptime)

### Step 4: Add Environment Variables

Click: **Environment**

Add these variables:

| Key | Value |
|-----|-------|
| `MONGODB_URI` | Your MongoDB connection string |
| `GOOGLE_GEMINI_API_KEY` | Your Gemini API key (from Step 1 of GitHub fix) |
| `GOOGLE_GEMINI_MODEL` | `gemini-2.0-flash` |
| `RAZORPAY_KEY_ID` | Your new Razorpay test key (from Step 1 of GitHub fix) |
| `RAZORPAY_KEY_SECRET` | Your new Razorpay secret (from Step 1 of GitHub fix) |
| `JWT_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FLASK_DEBUG` | `False` |
| `ENABLE_GEMINI` | `true` |
| `FRONTEND_URL` | Leave blank for now (update after Vercel deploys) |

**Important variable names:**
- ✅ Use: `GOOGLE_GEMINI_API_KEY` (not `GEMINI_API_KEY`)
- ✅ The code reads: `os.getenv('GOOGLE_GEMINI_API_KEY')`

### Step 5: Deploy

Click: **Create Web Service**

⏳ **Wait 5-10 minutes for deployment**

Monitor the logs:
- **Render → Your Service → Logs**

You want to see:
```
✓ Build successful
✓ Deploy live
```

Your backend URL will appear:
```
https://ai-mock-interview-api.onrender.com
```

(Your actual URL will be different)

**Save this URL - you need it for Vercel**

### Step 6: Test Backend Health

Open in browser:
```
https://YOUR-RENDER-URL.onrender.com/api/health
```

Replace `YOUR-RENDER-URL` with your actual Render URL from Step 5.

**Success response:**
```json
{
  "status": "ok",
  "active_client": "google.genai"
}
```

or (if Gemini not configured yet):
```json
{
  "status": "ok",
  "active_client": "none"
}
```

**If you get an error:** Check Render logs for details.

---

## Part 3: Deploy Frontend to Vercel

### Step 1: Open Vercel Dashboard

Go to: [Vercel Dashboard](https://vercel.com/dashboard)

Click: **Add New** → **Project**

### Step 2: Import GitHub Repository

Click: **Continue with GitHub**

Find: `AI-Mock-Interview-Platform`

Click: **Import**

### Step 3: Configure Project Settings

**Framework:** Next.js (auto-detected)

**Root Directory:** `mock-interview-platform/frontend`  
*(Critical - your frontend is in a subdirectory)*

**Build Command:** `npm run build`

**Output Directory:** `.next`

### Step 4: Add Environment Variables

Click: **Environment Variables**

Add:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | https://YOUR-RENDER-URL.onrender.com |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | Your Razorpay public key (starts with `rzp_test_`) |

**Important:**
- These `NEXT_PUBLIC_*` variables are sent to the browser (safe to expose)
- DO NOT add backend secrets as `NEXT_PUBLIC_*` variables
- Replace `YOUR-RENDER-URL` with your actual Render URL from Part 2 Step 5

### Step 5: Deploy

Click: **Deploy**

⏳ **Wait 3-5 minutes**

You'll get:
```
https://ai-mock-interview.vercel.app
```

(Your actual domain will be different)

**Save this URL**

### Step 6: Verify Frontend Loads

Open:
```
https://YOUR-VERCEL-URL.vercel.app
```

Should see:
- Homepage loads
- No console errors (F12 → Console)
- Navigation works

---

## Part 4: Connect Backend and Frontend

### Step 1: Update Render with Frontend URL

Go to: **Render Dashboard → Your Service → Environment**

Find: `FRONTEND_URL`

Set:
```
FRONTEND_URL=https://YOUR-VERCEL-URL.vercel.app
```

**Click Save** - Render will redeploy

### Step 2: Test Connection

Open Vercel frontend:
```
https://YOUR-VERCEL-URL.vercel.app
```

Open browser console (F12):
```
Console tab
```

Should NOT see CORS errors.

---

## Part 5: Test Your Application (22-Point Checklist)

### Test 1: Backend Health
```
GET https://YOUR-RENDER-URL.onrender.com/api/health
```
✅ Should return `{"status": "ok"}`

---

### Test 2: Frontend Loads
```
https://YOUR-VERCEL-URL.vercel.app
```
✅ Homepage displays

---

### Test 3: Register New User

1. Click **Register**
2. Enter: `test@example.com` / `password123`
3. Click **Register**

**Check:**
- ✅ Registers successfully
- ✅ Redirects to login
- ✅ No console errors
- ✅ MongoDB receives user (check Render logs)

---

### Test 4: Login

1. Login with `test@example.com` / `password123`
2. ✅ Redirects to dashboard
3. ✅ Shows subscription tier (should be "Free")
4. ✅ Shows monthly interview count

---

### Test 5: Interview Setup

1. Go to `/interview/setup` (click "Create Interview")
2. Select:
   - **Job Role:** Software Engineer
   - **Category:** Technical
   - **Difficulty:** Medium
3. Click **Generate Questions**

**Check:**
- ✅ Questions appear
- ✅ Questions are NOT just fallback text (verify they're from Gemini)
- ✅ No console errors

**To verify Gemini:**
- Check Render logs for Gemini API calls
- Or check `/api/health` for `"active_client": "google.genai"`

---

### Test 6: Answer Submission

1. Read a question
2. Type an answer
3. Click **Submit**

**Check:**
- ✅ Receives AI feedback
- ✅ Feedback includes a score (0-100)
- ✅ No console errors

---

### Test 7: Dashboard/History

1. Go to Dashboard
2. Look for **Recent Interviews**

**Check:**
- ✅ Previously completed interviews appear
- ✅ Shows date, category, score
- ✅ Loads from MongoDB (check logs)

---

### Test 8: Try Resume Upload

1. Go to **Resume** section (if exists)
2. Try to upload resume as Free user

**Check:**
- ✅ Get error: "Resume review is only available on the Pro plan"
- ✅ See upgrade button

---

### Test 9: Try to Exceed Interview Limit

As Free user (3 interviews/month):

1. Create interview #1 → Complete
2. Create interview #2 → Complete
3. Create interview #3 → Complete
4. Try to create interview #4

**Check:**
- ✅ Interview #4 fails with: "Monthly limit exceeded"
- ✅ See upgrade prompt

---

### Test 10: Socket.IO Connection

Open browser DevTools (F12):

1. **Network tab**
2. Filter for **WS** (WebSocket)
3. Create/update something on dashboard

**Check:**
- ✅ Socket.IO connection shows connected
- ✅ Messages being exchanged
- ✅ No connection errors

---

### Test 11: Subscription Plans Page

1. Go to **Pricing** or **Upgrade**
2. View plan options (Free, Basic, Pro)

**Check:**
- ✅ All plans display
- ✅ Pricing shows correctly
- ✅ Feature matrix clear

---

### Test 12: Create Razorpay Order (Test Mode)

1. Click **Upgrade to Basic**
2. Click **Pay with Razorpay**

**Check:**
- ✅ Order created (check Render logs)
- ✅ Redirects to Razorpay checkout
- ✅ Test payment form appears

---

### Test 13: Test Razorpay Payment

On Razorpay checkout:

1. **Card Number:** `4111 1111 1111 1111`
2. **Expiry:** Any future date (e.g., 12/25)
3. **CVC:** `123`
4. Click **Pay**
5. **OTP:** `123456`
6. Click **Verify**

**Check:**
- ✅ Payment succeeds
- ✅ Redirects back to app
- ✅ Subscription upgraded to "Basic"
- ✅ Monthly interview limit now 15

---

### Test 14: Generate Interview as Basic User

1. Create new interview
2. Generate questions

**Check:**
- ✅ Can generate (not limited to 3 anymore)
- ✅ Interview count increases

---

### Test 15: Try Video Analysis (if enabled)

1. Answer a question
2. Try to submit with video

**Note:** Video analysis dependencies are commented out, so:
- If it fails: Expected (dependencies not installed)
- If it works: Bonus! It's using fallback

---

### Test 16: Logout

1. Click **Logout**
2. Should redirect to login

**Check:**
- ✅ Token cleared
- ✅ Can't access dashboard anymore
- ✅ Must login again

---

### Test 17: Login with New User

1. Login with new test account

**Check:**
- ✅ Gets default Free tier
- ✅ Subscription dates set correctly
- ✅ Monthly limit = 3

---

### Test 18: Test with Different Job Roles

Try interview questions for different roles:
- **Data Scientist**
- **Product Manager**
- **Graphic Designer**

**Check:**
- ✅ Each returns relevant questions
- ✅ Categories vary by role

---

### Test 19: Feedback History

1. Complete several interviews
2. Go to feedback history

**Check:**
- ✅ All interviews visible
- ✅ Scores, feedback, dates shown
- ✅ Free tier shows last 7 days only (or all if not implemented)

---

### Test 20: Multiple Tab Test

1. Open app in 2 browser tabs
2. Create interview in Tab 1
3. Check Tab 2

**Check:**
- ✅ Tab 2 updates in real-time (Socket.IO)
- ✅ No duplicate sessions created

---

### Test 21: Mobile Responsiveness

1. Open on phone/tablet
2. Try creating interview
3. Try answering questions

**Check:**
- ✅ UI responsive
- ✅ Buttons clickable
- ✅ Text readable

---

### Test 22: Error Scenarios

**Test 1: Invalid Login**
- Try logging in with wrong password
- ✅ Should error: "Invalid credentials"

**Test 2: Network Error**
- Disconnect internet while on app
- ✅ Should show graceful error or reconnect message

**Test 3: MongoDB Down** (don't actually test this)
- Would show: "Database error, try again later"

---

## If Any Test Fails

### Check Render Logs

```
Render Dashboard → Your Service → Logs
```

Look for:
- ❌ Python errors
- ❌ MongoDB connection issues
- ❌ Gemini API errors
- ❌ Missing environment variables

### Check Vercel Logs

```
Vercel Dashboard → Deployments → Click latest
```

Look for:
- ❌ Build errors
- ❌ Missing environment variables
- ❌ Node module issues

### Check Browser Console

```
F12 → Console tab
```

Look for:
- ❌ CORS errors (likely if Backend/Frontend URLs don't match)
- ❌ Network errors (backend not responding)
- ❌ JavaScript errors

### Check Network Tab

```
F12 → Network tab
```

Check:
- ❌ API calls → 4xx/5xx errors?
- ❌ WebSocket (WS) → Failed to connect?

---

## Troubleshooting by Error

### Error: "CORS error"
**Fix:** Update `FRONTEND_URL` on Render to match your Vercel URL

### Error: "Cannot connect to backend"
**Fix:** Verify `NEXT_PUBLIC_API_URL` on Vercel matches your Render URL

### Error: "Gemini not working"
**Fix:** Verify `GOOGLE_GEMINI_API_KEY` on Render is correct

### Error: "Database connection failed"
**Fix:** Verify `MONGODB_URI` on Render is correct and MongoDB is running

### Error: "Razorpay error"
**Fix:** Verify `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are correct test keys

### Error: "Module not found: google.genai"
**Fix:** Ensure `google-genai==2.17.0` installed (check Render build logs)

---

## ✅ Success Criteria

You've successfully deployed when:

✅ Backend health check returns `{"status": "ok"}`
✅ Frontend homepage loads without errors
✅ User registration works
✅ User login works
✅ Interview generation works
✅ Gemini returns real questions (not fallback)
✅ Answer analysis returns AI feedback
✅ Dashboard shows interview history
✅ Socket.IO connections stable
✅ Razorpay payment flow works end-to-end
✅ Subscription tier upgrade works
✅ All 22 tests pass

---

## Next Steps After Deployment Success

### Option 1: Keep Testing
- Enable video analysis dependencies
- Test camera recording
- Test computer vision analysis
- Test edge cases

### Option 2: Prepare for Production
- Enable video analysis if needed
- Tighten CORS (restrict to Vercel domain only)
- Set up monitoring (Sentry, LogRocket)
- Configure database backups

### Option 3: Go Live
- Switch to Razorpay live keys (carefully!)
- Update Vercel domain settings
- Set up monitoring/alerts
- Announce to users

---

## Your Deployment URLs

Save these:

```
Frontend (Vercel):    https://YOUR-VERCEL-URL.vercel.app
Backend (Render):     https://YOUR-RENDER-URL.onrender.com
GitHub:               https://github.com/Pm21coder/AI-Mock-Interview-Platform
MongoDB Atlas:        https://cloud.mongodb.com
Render Dashboard:     https://render.com/dashboard
Vercel Dashboard:     https://vercel.com/dashboard
Razorpay Dashboard:   https://dashboard.razorpay.com
```

---

**Status: 🟢 READY TO DEPLOY**

Start with Step 1 of Part 1 above.

Good luck! 🚀
