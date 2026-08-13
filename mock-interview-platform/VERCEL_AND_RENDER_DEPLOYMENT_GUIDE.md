# Complete Deployment Guide: Vercel + Render

Deploy your AI Mock Interview Platform to production using **Vercel** (frontend) and **Render** (backend).

**Estimated Time:** 2-3 hours  
**Prerequisites:** GitHub account, Vercel account, Render account, MongoDB Atlas account

---

## Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Step 1: Prepare Your Repository](#step-1-prepare-your-repository)
3. [Step 2: Set Up MongoDB Atlas](#step-2-set-up-mongodb-atlas)
4. [Step 3: Verify Backend Locally](#step-3-verify-backend-locally)
5. [Step 4: Deploy Backend to Render](#step-4-deploy-backend-to-render)
6. [Step 5: Deploy Frontend to Vercel](#step-5-deploy-frontend-to-vercel)
7. [Step 6: Configure Environment Variables](#step-6-configure-environment-variables)
8. [Step 7: Test the Deployment](#step-7-test-the-deployment)
9. [Step 8: Custom Domain (Optional)](#step-8-custom-domain-optional)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites & Setup

### Required Accounts

- ✅ **GitHub Account** - [github.com](https://github.com)
- ✅ **Vercel Account** - [vercel.com](https://vercel.com)
- ✅ **Render Account** - [render.com](https://render.com)
- ✅ **MongoDB Atlas Account** - [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
- ✅ **Razorpay Account** - [razorpay.com](https://razorpay.com) (for production payments)

### Required API Keys

Gather these BEFORE deployment:

```
Backend (.env):
├── MONGODB_URI=mongodb+srv://...
├── GEMINI_API_KEY=your-key
├── RAZORPAY_KEY_ID=rzp_test_...
├── RAZORPAY_KEY_SECRET=your-secret
└── JWT_SECRET_KEY=your-secret

Frontend (.env.local):
├── NEXT_PUBLIC_API_URL=https://your-render-backend.onrender.com
└── NEXT_PUBLIC_SOCKET_URL=https://your-render-backend.onrender.com
```

---

## Step 1: Prepare Your Repository

### 1.1 Push to GitHub

If your code isn't on GitHub yet:

```bash
# In your project root
git init
git add .
git commit -m "Initial commit - ready for production"
git remote add origin https://github.com/YOUR_USERNAME/AI-Mock-Interview-Platform.git
git branch -M main
git push -u origin main
```

### 1.2 Clean Up Sensitive Files

**CRITICAL:** Make sure `.env` files are NOT in Git:

```bash
# Verify .gitignore includes
cat .gitignore
# Should contain:
# .env
# .env.local
# *.env

# If .env was already committed, remove it:
git rm --cached .env
git commit -m "Remove .env file from tracking"
git push
```

### 1.3 Create `.env.example` Files

**Backend: `mock-interview-platform/backend/.env.example`**

```env
# Database
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/mock_interview?retryWrites=true&w=majority

# AI API
GEMINI_API_KEY=your-gemini-api-key
ENABLE_GEMINI=true

# Payment Gateway
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
RAZORPAY_KEY_SECRET=your-secret-key

# JWT / Security
JWT_SECRET_KEY=your-secure-secret-key-min-32-chars
FLASK_SECRET_KEY=your-flask-secret-key

# Environment
FLASK_ENV=production
FLASK_DEBUG=False
ENV=production

# CORS
CORS_ORIGINS=https://your-frontend-domain.vercel.app

# Socket.IO
SOCKETIO_MESSAGE_QUEUE_MODE=simple
```

**Frontend: `mock-interview-platform/frontend/.env.example`**

```env
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
NEXT_PUBLIC_SOCKET_URL=https://your-backend-url.onrender.com
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
```

Commit these files:

```bash
git add .env.example
git commit -m "Add .env.example files for reference"
git push
```

### 1.4 Verify Dependencies Are Pinned

**Backend:**

```bash
cd backend
grep -E "^[a-zA-Z]+==" requirements.txt | head -5
# Should see exact versions like:
# Flask==3.1.2
# PyMongo==4.6.1
# google-genai==2.17.0
```

If not pinned, run:

```bash
pip install -q pip-tools
pip-compile requirements.in  # If you have requirements.in
# OR manually pin versions:
# Replace ">=" with "=="
```

**Frontend:**

```bash
cd frontend
cat package-lock.json | head -20
# Should already exist; commit it if not:
git add package-lock.json
git commit -m "Add package-lock.json"
git push
```

---

## Step 2: Set Up MongoDB Atlas

### 2.1 Create a Free Cluster

1. Go to [MongoDB Atlas](https://account.mongodb.com/account/login)
2. Click **"Create a new project"**
3. Name it: `ai-mock-interview-prod`
4. Click **"Create Project"**
5. Click **"Build a Cluster"**
6. Choose **M0 (free tier)** - sufficient for testing
7. Select your region (closest to your users)
8. Click **"Create"** - wait ~5 minutes for cluster to start

### 2.2 Create Database User

1. In your cluster, go to **"Database Access"**
2. Click **"Add New Database User"**
3. Enter:
   - **Username:** `mock_interview_admin`
   - **Password:** Generate a strong password (save it!)
   - **Built-in Role:** `Atlas Admin`
4. Click **"Add User"**

### 2.3 Configure Network Access

1. Go to **"Network Access"**
2. Click **"Add IP Address"**
3. Choose **"Allow Access from Anywhere"** (for Render)
   - This adds `0.0.0.0/0` - change to specific IPs in production
4. Click **"Confirm"**

### 2.4 Get Connection String

1. Go to **"Clusters"** → Click your cluster name
2. Click **"Connect"**
3. Choose **"Connect your application"**
4. Copy the connection string:

```
mongodb+srv://mock_interview_admin:PASSWORD@cluster0.xxxxx.mongodb.net/mock_interview?retryWrites=true&w=majority
```

Replace:
- `PASSWORD` with your database user password
- `mock_interview` with your database name

**Save this for later!**

---

## Step 3: Verify Backend Locally

Before deploying to Render, test locally:

```bash
cd mock-interview-platform/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
MONGODB_URI=mongodb+srv://mock_interview_admin:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/mock_interview?retryWrites=true&w=majority
GEMINI_API_KEY=your-gemini-key
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=your-secret
JWT_SECRET_KEY=your-secret-key-min-32-chars
FLASK_SECRET_KEY=your-flask-secret-key
FLASK_ENV=production
FLASK_DEBUG=False
EOF

# Test backend
python run.py
# Should start on http://localhost:5000
# GET http://localhost:5000/api/health should return 200
```

Hit `Ctrl+C` to stop.

---

## Step 4: Deploy Backend to Render

### 4.1 Connect GitHub to Render

1. Go to [Render.com](https://render.com)
2. Sign up / Log in
3. Click **"New +"** → **"Web Service"**
4. Click **"Connect account"** → Link your GitHub
5. Find your repo: `AI-Mock-Interview-Platform`
6. Click **"Connect"**

### 4.2 Configure Backend Service

**General Settings:**

- **Name:** `ai-mock-interview-api`
- **Environment:** `Python 3.11`
- **Build Command:** 
  ```
  cd mock-interview-platform/backend && pip install -r requirements.txt
  ```
- **Start Command:**
  ```
  cd mock-interview-platform/backend && gunicorn --workers 2 --threads 100 --worker-class gthread --timeout 120 --bind 0.0.0.0:$PORT run:app
  ```
- **Plan:** Free (or paid if you need better uptime)

### 4.3 Add Environment Variables

Click **"Environment"** and add:

| Key | Value |
|-----|-------|
| `MONGODB_URI` | `mongodb+srv://mock_interview_admin:PASSWORD@cluster0.xxxxx.mongodb.net/mock_interview?retryWrites=true&w=majority` |
| `GOOGLE_GEMINI_API_KEY` | Your Gemini API key |
| `RAZORPAY_KEY_ID` | `rzp_test_xxxxx` (or `rzp_live_xxxxx` for production) |
| `RAZORPAY_KEY_SECRET` | Your Razorpay secret |
| `JWT_SECRET_KEY` | Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SECRET_KEY` | Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FLASK_DEBUG` | `False` |
| `FRONTEND_URL` | `https://your-frontend-domain.vercel.app` (add after Vercel deployment) |
| `ENABLE_GEMINI` | `true` |

### 4.4 Deploy

Click **"Create Web Service"**

Render will:
1. Install dependencies
2. Build the backend
3. Deploy it
4. Show you the URL: `https://ai-mock-interview-api.onrender.com`

⏳ **First deployment takes 5-10 minutes**. Monitor the logs.

### 4.5 Verify Backend Deployment

```bash
# Test health endpoint
curl https://ai-mock-interview-api.onrender.com/api/health
# Should return: {"status": "healthy"}

# Test database connection
curl https://ai-mock-interview-api.onrender.com/api/subscription/plans
# Should return subscription tiers
```

**Save your backend URL** for Step 5!

---

## Step 5: Deploy Frontend to Vercel

### 5.1 Connect GitHub to Vercel

1. Go to [Vercel.com](https://vercel.com)
2. Sign up / Log in
3. Click **"Add New..."** → **"Project"**
4. Click **"Continue with GitHub"**
5. Search and select: `AI-Mock-Interview-Platform`
6. Click **"Import"**

### 5.2 Configure Frontend

**Project Settings:**

- **Framework Preset:** `Next.js`
- **Root Directory:** `mock-interview-platform/frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Install Command:** `npm ci`

### 5.3 Add Environment Variables

Click **"Environment Variables"** and add:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://ai-mock-interview-api.onrender.com` |
| `NEXT_PUBLIC_SOCKET_URL` | `https://ai-mock-interview-api.onrender.com` |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | Your Razorpay test key (public) |

**Note:** `NEXT_PUBLIC_*` variables are sent to browser, so they're safe to make public.

### 5.4 Deploy

Click **"Deploy"**

Vercel will:
1. Install dependencies
2. Build the Next.js app
3. Deploy to CDN
4. Show you the URL: `https://ai-mock-interview.vercel.app`

⏳ **Deployment takes 3-5 minutes**.

**Save your frontend URL!**

---

## Step 6: Configure Environment Variables

### 6.1 Update Backend Frontend URL

Now that you have your Vercel URL, update the backend:

1. Go to Render → Your service → **Settings**
2. Find `FRONTEND_URL` environment variable
3. Update to your Vercel URL:
   ```
   FRONTEND_URL=https://your-frontend.vercel.app
   ```
4. Click **"Save"** - backend will redeploy

### 6.2 Verify Frontend Points to Backend

Your frontend `.env.local` in Vercel should have:

```env
NEXT_PUBLIC_API_URL=https://ai-mock-interview-api.onrender.com
NEXT_PUBLIC_SOCKET_URL=https://ai-mock-interview-api.onrender.com
```

If you need to change these:

1. Go to Vercel → Project Settings → **Environment Variables**
2. Update values
3. Click **"Save"**
4. Deploy again (Vercel → Deployments → Trigger Deploy)

---

## Step 7: Test the Deployment

### 7.1 Health Checks

```bash
# Backend health
curl https://ai-mock-interview-api.onrender.com/api/health

# Frontend loads
open https://your-frontend.vercel.app
# Should load homepage
```

### 7.2 Full User Flow Test

1. **Register**
   - Go to your Vercel frontend
   - Click "Register"
   - Create account with email/password
   - Should succeed and redirect to login

2. **Login**
   - Login with your credentials
   - Should see dashboard with "Free" tier
   - Should show 3 interviews remaining

3. **Interview Creation**
   - Click "Create Interview"
   - Select category (e.g., "technical")
   - Click "Generate Questions"
   - Should receive 3 mock questions

4. **Answer Submission**
   - Answer a question
   - Click "Submit"
   - Should receive AI feedback

5. **Payment (Test Mode)**
   - Go to "Upgrade"
   - Select "Basic Plan"
   - Click "Pay with Razorpay"
   - Use test card: `4111 1111 1111 1111`, CVC: `123`
   - Should succeed and upgrade tier

6. **Verify Upgrade**
   - Dashboard should show "Basic" tier
   - Should show 15 interviews remaining

### 7.3 Check Logs

**Backend logs (Render):**
- Go to Render → Service → **Logs**
- Look for any errors
- Should see connection success: `MongoDB connected successfully`

**Frontend logs (Vercel):**
- Go to Vercel → Project → **Deployments**
- Click latest deployment
- Should show "Deployment successful"

---

## Step 8: Custom Domain (Optional)

### 8.1 Frontend Custom Domain (Vercel)

1. Buy a domain from Namecheap, GoDaddy, etc.
2. Go to Vercel → Settings → **Domains**
3. Click **"Add"**
4. Enter your domain: `yourdomain.com`
5. Follow instructions to update nameservers
6. Wait for DNS propagation (~24 hours)

### 8.2 Backend Custom Domain (Render)

1. Go to Render → Service → Settings → **Custom Domains**
2. Click **"Add Custom Domain"**
3. Enter: `api.yourdomain.com`
4. Update your DNS records as shown
5. Update backend's `CORS_ORIGINS` to use custom domain

---

## Troubleshooting

### Issue: Backend deployment fails

**Check logs:**
```
Render → Your service → Logs
```

**Common causes:**

| Error | Solution |
|-------|----------|
| `SyntaxError in Python` | Check `requirements.txt` doesn't have duplicate packages |
| `ModuleNotFoundError: pymongo` | Ensure `PyMongo==4.6.1` is in `requirements.txt` |
| `MONGODB_URI not found` | Add it to Render Environment Variables |
| `gunicorn command not found` | Ensure `gunicorn==23.0.0` is in `requirements.txt` |

### Issue: Frontend deployment fails

**Check logs:**
```
Vercel → Deployments → Click failed deployment
```

**Common causes:**

| Error | Solution |
|-------|----------|
| `Node module not found` | Run `npm ci` locally, commit `package-lock.json` |
| `Environment variable missing` | Add `NEXT_PUBLIC_API_URL` in Vercel settings |
| `Build timeout` | Increase timeout in Vercel settings (Project → Settings → Build) |

### Issue: Frontend can't connect to backend

**Check:**

1. Backend is running:
   ```bash
   curl https://your-backend.onrender.com/api/health
   ```

2. Frontend has correct API URL:
   - Go to Vercel → Project Settings → Environment Variables
   - Verify `NEXT_PUBLIC_API_URL` matches backend URL

3. Backend CORS allows frontend:
   - Render → Service → Environment Variables
   - Verify `CORS_ORIGINS=https://your-frontend.vercel.app`

4. Check browser console (F12 → Console)
   - Look for CORS errors or connection refused

**Fix CORS error:**

```javascript
// If you see: "Access to XMLHttpRequest blocked by CORS policy"
// Update backend CORS_ORIGINS:
Render → Environment Variables → CORS_ORIGINS
```

### Issue: WebSocket connection fails

**Symptoms:**
- Dashboard doesn't update in real-time
- "Cannot connect to WebSocket" in console

**Fix:**

1. Render deployment uses gunicorn, not `socketio.run()`
2. WebSocket should work with `simple-websocket` backend
3. Check:
   ```bash
   # Backend Render logs should show:
   # "Application startup complete [gunicorn]"
   ```

4. Verify Socket.IO endpoint in frontend:
   ```javascript
   // Should match backend URL
   NEXT_PUBLIC_SOCKET_URL=https://your-backend.onrender.com
   ```

### Issue: Database connection times out

**Symptoms:**
- "Connection timeout" or "Unable to connect to MongoDB"

**Fix:**

1. Check MongoDB Atlas Network Access:
   - MongoDB Atlas → Network Access
   - Verify Render IP is whitelisted (should be `0.0.0.0/0`)

2. Verify connection string:
   ```bash
   # Should include:
   # ?retryWrites=true&w=majority
   # &authSource=admin
   ```

3. Check database user:
   - MongoDB Atlas → Database Access
   - Verify user `mock_interview_admin` exists
   - Verify password is correct

### Issue: Razorpay payments fail

**Symptoms:**
- "Unable to process payment" during checkout
- "Invalid Razorpay key"

**Fix:**

1. Verify test keys are used (starts with `rzp_test_`)
2. Check Razorpay dashboard for API key limits
3. Verify `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in Render
4. Test with Razorpay test card:
   - **Card Number:** `4111 1111 1111 1111`
   - **Expiry:** Any future date
   - **CVC:** Any 3 digits
   - **OTP:** `123456`

### Issue: Render goes to sleep (free tier)

**Symptom:** Backend responds slowly after inactivity

**Solutions:**

1. **Upgrade to Paid Plan:**
   - Render → Service → Settings → Change Plan to Paid
   - Keeps instance always running

2. **Alternatively, keep backend awake:**
   - Add an uptime monitor (UptimeRobot, etc.)
   - Ping health endpoint every 5 minutes

---

## Production Checklist

Before going live, complete these:

- [ ] Backend and frontend URLs working
- [ ] User registration/login working
- [ ] Interview questions generating correctly
- [ ] AI feedback being received
- [ ] Razorpay test payments working
- [ ] MongoDB queries executing successfully
- [ ] WebSocket connections stable
- [ ] CORS errors resolved
- [ ] Logs monitored and clean
- [ ] Performance acceptable (no timeouts)
- [ ] All secrets stored in environment variables
- [ ] `.env` files NOT in Git
- [ ] Backup strategy configured for MongoDB
- [ ] Error monitoring set up (optional: Sentry, LogRocket)

---

## Next Steps

### Immediate (Day 1)

1. ✅ Deploy backend to Render
2. ✅ Deploy frontend to Vercel
3. ✅ Run through test flow
4. ✅ Fix any CORS/connection issues

### Soon (Week 1)

5. Set up custom domain (optional)
6. Switch Razorpay to live keys (if live payment ready)
7. Set up error monitoring (Sentry)
8. Configure database backups

### Later (Before Big Launch)

9. Load testing
10. Security audit
11. Performance optimization
12. Marketing/launch prep

---

## Support

If you encounter issues:

1. **Check Render logs:** Render → Service → Logs
2. **Check Vercel logs:** Vercel → Deployments → Click deployment
3. **Check MongoDB logs:** MongoDB Atlas → Cluster → Logs
4. **Check browser console:** F12 → Console tab
5. **Post error message + logs** to get help

---

**You're ready to deploy! 🚀**
