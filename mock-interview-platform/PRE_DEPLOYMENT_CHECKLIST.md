# Pre-Deployment Checklist

Complete ALL items in this checklist before deploying to production.

---

## 1. Code Quality & Security (MUST COMPLETE)

### 1.1 Secrets & Credentials
- [ ] `.env` file is NOT in Git (check `.gitignore`)
- [ ] `.env.local` is NOT in Git
- [ ] No hardcoded passwords in source code
- [ ] No API keys in comments or code
- [ ] `.env.example` files created with placeholder values only

**Verify:**
```bash
# Should show NO .env files
git status
git log --all --full-history --source -- .env
git log --all --full-history --source -- .env.local
```

### 1.2 Dependencies
- [ ] Backend: All versions pinned with `==` (no `>=` or `~`)
- [ ] Frontend: `package-lock.json` committed to Git
- [ ] No deprecated dependencies (check for security advisories)
- [ ] No duplicate packages (e.g., one Gemini SDK only)

**Verify:**
```bash
# Backend - should show exact versions
cd backend
grep -E "^[a-zA-Z]+==" requirements.txt | wc -l
# Frontend - should exist
cd frontend
ls -la package-lock.json
```

### 1.3 Code Syntax
- [ ] No `console.log()` left in production code
- [ ] No TODO or FIXME comments in critical paths
- [ ] No debug/development imports in production
- [ ] TypeScript/Python syntax errors resolved

**Verify:**
```bash
# Frontend linting
npm run lint
# Python syntax check (in backend directory)
python -m py_compile app/**/*.py
```

---

## 2. Frontend Configuration (VERCEL)

### 2.1 Build Configuration
- [ ] `next.config.js` properly configured
- [ ] `tsconfig.json` or `jsconfig.json` exists
- [ ] Build succeeds locally: `npm run build`
- [ ] No build warnings or errors

**Test locally:**
```bash
cd frontend
npm ci  # Clean install
npm run build
npm start
```

### 2.2 Environment Setup
- [ ] Environment variables documented in `.env.example`
- [ ] All `NEXT_PUBLIC_*` variables identified
- [ ] Ready to add to Vercel:
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_SOCKET_URL`
  - `NEXT_PUBLIC_RAZORPAY_KEY_ID`

### 2.3 Frontend Features
- [ ] Login/registration page loads
- [ ] Dashboard renders correctly
- [ ] Interview setup form functional
- [ ] Responsive design works on mobile
- [ ] No broken links or images

---

## 3. Backend Configuration (RENDER)

### 3.1 Build Configuration
- [ ] `requirements.txt` has all dependencies
- [ ] Python 3.11 compatible (no Python 2 code)
- [ ] Clean install succeeds locally:
  ```bash
  python -m venv test_env
  source test_env/bin/activate
  pip install -r requirements.txt
  ```
- [ ] No import errors: `python -c "from app import create_app; app = create_app()"`

### 3.2 Server Configuration
- [ ] `run.py` (or equivalent) starts Flask app correctly
- [ ] Gunicorn command ready: `gunicorn --workers 2 --threads 100 --worker-class gthread --timeout 120 --bind 0.0.0.0:$PORT run:app`
- [ ] Socket.IO configured for gunicorn (using gthread workers)
- [ ] Health check endpoint available: `GET /api/health`

**Test locally:**
```bash
cd backend
export FLASK_ENV=production
export FLASK_DEBUG=False
gunicorn --workers 1 --threads 100 --worker-class gthread --bind 127.0.0.1:5000 run:app
# Visit: http://127.0.0.1:5000/api/health
```

### 3.3 Environment Secrets Ready
- [ ] `MONGODB_URI` obtained from MongoDB Atlas
- [ ] `GOOGLE_GEMINI_API_KEY` obtained (test or production)
- [ ] `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` obtained (test keys: `rzp_test_*`)
- [ ] `JWT_SECRET_KEY` generated (min 32 characters)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] `SECRET_KEY` generated (min 32 characters)

### 3.4 Backend Features
- [ ] User registration endpoint works
- [ ] User login endpoint works
- [ ] JWT token creation/validation works
- [ ] Database queries execute without errors
- [ ] Gemini API calls succeed (if enabled)
- [ ] Razorpay order creation works

---

## 4. Database Configuration (MONGODB ATLAS)

### 4.1 Cluster Setup
- [ ] Cluster created and running
- [ ] Cluster region optimal for your users
- [ ] M0 (free tier) or higher selected

### 4.2 Database User
- [ ] User `mock_interview_admin` created
- [ ] Strong password set (25+ random characters)
- [ ] Role set to `Atlas Admin` (for now, can restrict later)
- [ ] Password saved in secure location

### 4.3 Network Access
- [ ] IP whitelist configured: `0.0.0.0/0` (allows Render)
- [ ] TLS/SSL enabled for connections
- [ ] Connection string saved:
  ```
  mongodb+srv://mock_interview_admin:PASSWORD@cluster.mongodb.net/mock_interview?retryWrites=true&w=majority
  ```

### 4.4 Backup & Maintenance
- [ ] Backups enabled (if available on tier)
- [ ] Maintenance window set to off-peak time
- [ ] Database name set to `mock_interview`

**Test connection locally:**
```bash
python -c "
from pymongo import MongoClient
uri = 'mongodb+srv://mock_interview_admin:PASSWORD@cluster.mongodb.net/mock_interview?retryWrites=true&w=majority'
client = MongoClient(uri)
print('✓ Connected to MongoDB')
print('Databases:', client.list_database_names())
client.close()
"
```

---

## 5. Payment Gateway (RAZORPAY)

### 5.1 Account Setup
- [ ] Razorpay account created
- [ ] Account type: Test mode (initially)
- [ ] Test keys generated (start with `rzp_test_`)
- [ ] Keys saved securely

### 5.2 Integration Ready
- [ ] Test key ID: `rzp_test_xxxxx`
- [ ] Test secret: Available and saved
- [ ] Webhook URL (optional, but recommended):
  ```
  https://your-backend.onrender.com/api/subscription/razorpay-webhook
  ```
- [ ] Test payment cards available:
  - Visa: `4111 1111 1111 1111`
  - CVC: Any 3 digits
  - OTP: `123456`

---

## 6. API Integration (GEMINI)

### 6.1 API Key Acquisition
- [ ] Google Cloud Project created
- [ ] Gemini API enabled
- [ ] API key generated (unrestricted or IP-restricted)
- [ ] Key saved: `GOOGLE_GEMINI_API_KEY`

### 6.2 API Testing
- [ ] API key works locally
- [ ] Test call succeeds (can be in backend tests)
- [ ] Response format understood
- [ ] Rate limits documented

**Test locally:**
```bash
python -c "
import google.generativeai as genai
genai.configure(api_key='YOUR_KEY')
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content('Hello!')
print('✓ Gemini API working')
print(response.text[:100])
"
```

---

## 7. GitHub Repository

### 7.1 Repository Status
- [ ] Latest code committed
- [ ] All branches merged to `main`
- [ ] No uncommitted changes
- [ ] Clean git log (no sensitive commits)

**Verify:**
```bash
git status  # Should be clean
git log --oneline -5  # View recent commits
```

### 7.2 Remote Configuration
- [ ] Remote URL correct:
  ```bash
  git remote -v
  # Should show: origin https://github.com/YOUR_USERNAME/REPO.git
  ```
- [ ] All commits pushed to main branch
- [ ] No pending unpushed commits

**Verify:**
```bash
git push origin main  # Should say "Everything up-to-date"
```

---

## 8. Documentation

### 8.1 README Files
- [ ] `README.md` updated with:
  - [ ] Correct tech stack versions (Next.js 16.3, React 19, Flask, etc.)
  - [ ] Installation instructions
  - [ ] How to run locally
  - [ ] Environment setup
  - [ ] Deployment instructions link

### 8.2 Environment Documentation
- [ ] `.env.example` (backend) complete with all keys
- [ ] `.env.example` (frontend) complete
- [ ] Environment variables documented in deployment guide

### 8.3 Deployment Guides
- [ ] `VERCEL_AND_RENDER_DEPLOYMENT_GUIDE.md` reviewed
- [ ] `DEPLOYMENT_QUICK_REFERENCE.md` available
- [ ] `DEPLOYMENT_ARCHITECTURE.md` reviewed
- [ ] All guides have correct URLs and commands

---

## 9. Local Testing

### 9.1 Full Integration Test
- [ ] Start backend locally
- [ ] Start frontend locally
- [ ] Test complete user flow:
  1. Register new user
  2. Login
  3. Create interview
  4. Generate questions
  5. Submit answer
  6. Receive feedback
  7. View history
  8. Attempt upgrade (test payment)

### 9.2 Error Handling
- [ ] Test with MongoDB disconnected (graceful error)
- [ ] Test with invalid Gemini key (proper error message)
- [ ] Test with invalid JWT token (401 unauthorized)
- [ ] Test invalid input (400 bad request)

### 9.3 Performance Check
- [ ] No console errors (F12 → Console)
- [ ] No network errors (F12 → Network)
- [ ] Reasonable response times (<2 seconds)
- [ ] WebSocket connection succeeds

---

## 10. Final Security Review

### 10.1 Secrets Management
- [ ] No secrets in `.git/` history
- [ ] All secrets moved to environment variables
- [ ] `.env` and `.env.local` in `.gitignore`
- [ ] Secret rotation plan documented

### 10.2 API Security
- [ ] All inputs validated on backend
- [ ] SQL injection prevention in place
- [ ] XSS protection enabled (Next.js default)
- [ ] CORS properly configured (no `*` wildcard)
- [ ] Rate limiting configured (if needed)

### 10.3 Data Protection
- [ ] Passwords hashed with bcrypt
- [ ] JWT tokens have expiration
- [ ] Sensitive data not logged
- [ ] HTTPS enforced (automatic on Vercel/Render)

---

## Deployment Readiness Sign-Off

**Before proceeding to deployment, confirm:**

- [ ] All sections 1-10 above are complete
- [ ] Local testing passed
- [ ] Git repository clean and pushed
- [ ] Accounts created: Vercel, Render, MongoDB Atlas, Razorpay
- [ ] API keys obtained and secured

---

## Deployment Order

1. **MongoDB Atlas** - Database foundation
2. **Render Backend** - Server and APIs
3. **Vercel Frontend** - User interface
4. **Configure CORS** - Connect frontend to backend
5. **Test Production** - Full end-to-end test

---

## Post-Deployment

After deployment is complete:

- [ ] Monitor logs for first 24 hours
- [ ] Run through production testing
- [ ] Set up uptime monitoring (optional: UptimeRobot)
- [ ] Configure alerting for errors
- [ ] Plan credential rotation (every 3-6 months)
- [ ] Document any issues encountered

---

**You're ready for deployment! 🚀**

Start with: `VERCEL_AND_RENDER_DEPLOYMENT_GUIDE.md`
