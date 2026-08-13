# 🚨 CRITICAL: Fix GitHub Before Deployment

**DO NOT DEPLOY UNTIL YOU COMPLETE THESE STEPS**

Your repository has exposed secrets in Git. This is a security emergency.

---

## ⚠️ Issues Found

1. ✋ **Root `.env` contains Razorpay SECRET** (publicly visible)
2. ✋ **Root `.env.local` contains Razorpay live key** (publicly visible)
3. ✋ **`.gitignore` doesn't exclude root `.env` files**
4. ⚠️ Video analysis dependencies commented out in requirements.txt
5. ⚠️ CORS open to everyone (`'*'`)

---

## 🔴 STEP 1: Rotate Razorpay Secret (DO THIS NOW)

**Your Razorpay secret was publicly committed to GitHub.**

Go to: [Razorpay Dashboard](https://dashboard.razorpay.com)

1. Settings → API Keys
2. Regenerate your API secret
3. Note the new secret
4. Note your new API key ID (also regenerate if possible)

**This is critical - do this FIRST before any other steps**

Save your new keys:
```
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXXXXX
RAZORPAY_KEY_SECRET=[new-secret-from-dashboard]
```

---

## 🔴 STEP 2: Fix `.gitignore` Locally

Open your local repository:

```bash
cd c:\Users\dell\OneDrive\Desktop\AI Mock Interview Platform
cd AI-Mock-Interview-Platform
```

Edit: `.gitignore` (root level)

Replace the entire file with:

```
# Environment files (CRITICAL)
.env
.env.local
.env.*.local
!.env.example
!.env.*.example

# Frontend
mock-interview-platform/frontend/.env.local
mock-interview-platform/frontend/node_modules/
mock-interview-platform/frontend/.next/
mock-interview-platform/frontend/dist/

# Backend
mock-interview-platform/backend/.env
mock-interview-platform/backend/.venv/
mock-interview-platform/backend/venv/
mock-interview-platform/backend/__pycache__/
mock-interview-platform/backend/*.pyc
mock-interview-platform/backend/dist/
mock-interview-platform/backend/build/

# Logs
*.log
logs/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.pytest_cache/
.coverage

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build
dist/
build/
*.egg-info/

# Database
*.db
*.sqlite
```

**Save the file.**

---

## 🔴 STEP 3: Remove `.env` Files from Git History

Run these commands in your terminal:

```bash
cd c:\Users\dell\OneDrive\Desktop\AI Mock Interview Platform\AI-Mock-Interview-Platform

# Remove from Git tracking (but keep local files)
git rm --cached .env 2>nul
git rm --cached .env.local 2>nul
git rm --cached mock-interview-platform/frontend/.env.local 2>nul
git rm --cached root/.env 2>nul

# Check status
git status
```

**Expected output:** Should show the `.env` files as deleted (ready to commit)

If any file doesn't exist, that's fine - the command just fails silently.

---

## 🔴 STEP 4: Create `.env.example` Files (Safe Templates)

### Create: `mock-interview-platform/backend/.env.example`

```env
# Database
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/mock_interview?retryWrites=true&w=majority

# Google Gemini AI (IMPORTANT: Use GOOGLE_GEMINI_API_KEY, not GEMINI_API_KEY)
GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here
GOOGLE_GEMINI_MODEL=gemini-2.0-flash
ENABLE_GEMINI=true

# Payment Gateway
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_secret_here

# Security (Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your-jwt-secret-min-32-chars
SECRET_KEY=your-flask-secret-min-32-chars

# Environment
FLASK_DEBUG=False
FRONTEND_URL=https://your-frontend-domain.vercel.app
```

### Create: `mock-interview-platform/frontend/.env.example`

```env
# Backend API
NEXT_PUBLIC_API_URL=https://your-backend-domain.onrender.com

# Razorpay (Public key only - safe to commit)
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
```

### Create: `.env.example` (root level, if it doesn't exist)

```env
# Root level environment - most config is in subdirectories
# See ./mock-interview-platform/backend/.env.example for backend
# See ./mock-interview-platform/frontend/.env.example for frontend
```

---

## 🔴 STEP 5: Verify Local `.env` Files Are NOT in Git

Run:

```bash
git status
```

You should see the `.env` files listed as deleted/removed.

**Verify these files still exist locally (we only removed from Git):**

```bash
ls .env 2>nul || echo "Root .env not found (OK if locally removed)"
ls mock-interview-platform/backend/.env 2>nul || echo "Backend .env not found"
ls mock-interview-platform/frontend/.env.local 2>nul || echo "Frontend .env.local not found"
```

If these files don't exist locally, create them now with your actual secrets before proceeding:

```bash
# Backend .env
cd mock-interview-platform/backend
copy .env.example .env
# Edit .env with your actual secrets
```

---

## 🔴 STEP 6: Commit the Cleanup

Run:

```bash
cd c:\Users\dell\OneDrive\Desktop\AI Mock Interview Platform\AI-Mock-Interview-Platform

git add .gitignore
git add mock-interview-platform/backend/.env.example
git add mock-interview-platform/frontend/.env.example
git add .env.example

git status
# Should show these files ready to commit, with .env files as deleted
```

Commit:

```bash
git commit -m "Security: Remove environment files from version control and update .gitignore

- Remove .env from root (contained Razorpay secret)
- Remove .env.local from root
- Remove .env.local from frontend
- Update .gitignore to properly exclude all environment files
- Add .env.example templates for reference
- IMPORTANT: Razorpay secret has been rotated in dashboard"
```

Push to GitHub:

```bash
git push origin main
```

**After push, verify on GitHub:**
- Go to: https://github.com/Pm21coder/AI-Mock-Interview-Platform
- Check that `.env` and `.env.local` are no longer in the repo
- Check that `.env.example` files are visible

---

## ⚠️ Important: Git History Still Contains Secrets

Removing the files from the latest commit **does NOT erase them from Git history**.

The secrets are still in the Git history (publicly visible to anyone who clones the repo).

**You must:**

1. ✅ Rotate the Razorpay secret (do this now)
2. Consider removing secrets from Git history using:
   - `git filter-branch` (complex, rewrites history)
   - Or just accept that you've rotated the secret so the exposed one is worthless

For now, the important part is:
- ✅ Secrets are rotated
- ✅ No new deploys will expose secrets
- ✅ Future developers won't accidentally commit secrets

---

## 🟡 Secondary Issues to Address Later

### Issue 1: Video Analysis Dependencies Commented Out

Your `requirements.txt` has video analysis dependencies commented:

```
# opencv-python==4.8.1.78
# mediapipe==0.10.2
# nltk==3.8.1
# textblob==0.17.1
# scikit-learn==1.4.1
```

**For your first deployment:** Keep them commented (less to install).

**After deployment works:** Uncomment if you want real video analysis.

### Issue 2: CORS is Open

Your backend has:

```python
CORS(app)  # Allows all origins
socketio = SocketIO(cors_allowed_origins='*')
```

**For your first deployment:** Leave this (one less failure point).

**After deployment works:** Restrict to your Vercel domain:

```python
CORS(app, origins=[os.getenv('FRONTEND_URL')])
socketio = SocketIO(cors_allowed_origins=os.getenv('FRONTEND_URL', '*'))
```

---

## ✅ Verification Checklist

- [ ] Razorpay secret rotated in dashboard
- [ ] New Razorpay keys saved locally
- [ ] `.gitignore` updated with environment file rules
- [ ] `.env` files removed from Git
- [ ] `.env.example` files created and committed
- [ ] Local `.env` files still exist (not deleted)
- [ ] Changes pushed to GitHub
- [ ] GitHub repo no longer shows `.env` files (only `.env.example`)

---

## 🚀 After Completing These Steps

Then proceed with: **DEPLOYMENT_FOR_YOUR_REPO.md** (coming next)

Which will guide you through:
1. MongoDB Atlas setup
2. Render backend deployment
3. Vercel frontend deployment
4. 22-point test checklist

---

**Status: 🔴 BLOCKING**

Do not proceed to Render/Vercel deployment until you complete all 6 steps above.
