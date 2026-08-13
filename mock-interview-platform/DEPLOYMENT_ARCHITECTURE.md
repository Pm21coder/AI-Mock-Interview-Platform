# Deployment Architecture & Overview

Your AI Mock Interview Platform deployment structure:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR USERS' BROWSERS                        │
└─────────────────────────────────────────────────────────────────────┘
                                   ↑
                      HTTPS / WebSocket
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│   Vercel                                                            │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  Frontend (Next.js 16.3.0, React 19, Tailwind)              │  │
│   │  ├─ Login / Register                                         │  │
│   │  ├─ Interview Setup                                          │  │
│   │  ├─ Dashboard                                                │  │
│   │  ├─ Subscription Plans                                       │  │
│   │  └─ Real-time updates via WebSocket                          │  │
│   │                                                              │  │
│   │  URL: https://your-project.vercel.app                       │  │
│   │  Variables: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SOCKET_URL    │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   ↑
                 API Calls (REST) + WebSocket
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│   Render                                                            │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  Backend (Flask, Flask-SocketIO)                             │  │
│   │  ├─ API Routes (auth, interview, subscription)              │  │
│   │  ├─ WebSocket for real-time events                          │  │
│   │  ├─ Gemini AI integration                                   │  │
│   │  └─ Razorpay payment processing                             │  │
│   │                                                              │  │
│   │  URL: https://your-service.onrender.com                     │  │
│   │  Start: gunicorn with gthread workers                       │  │
│   │  Variables: MONGODB_URI, GOOGLE_GEMINI_API_KEY, etc.       │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   ↑
                    MongoDB Connection String
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│   MongoDB Atlas (Cloud)                                             │
│   ├─ Cluster: ai-mock-interview-prod (M0 free tier)               │
│   ├─ Database: mock_interview                                       │
│   ├─ Collections:                                                   │
│   │  ├─ users (email, password_hash, subscription data)           │  │
│   │  ├─ interview_sessions (questions, answers)                   │  │
│   │  ├─ payments (razorpay orders, verifications)                 │  │
│   │  └─ feedback (AI analysis results)                            │  │
│   │                                                              │  │
│   │  Connection: TLS/SSL enabled                                 │  │
│   │  User: mock_interview_admin                                  │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Summary Table

| Component | Platform | Tech Stack | Status | URL |
|-----------|----------|-----------|--------|-----|
| **Frontend** | Vercel | Next.js 16.3, React 19, Tailwind CSS | Ready | https://your-project.vercel.app |
| **Backend** | Render | Flask, Flask-SocketIO, Python 3.11 | Ready | https://your-service.onrender.com |
| **Database** | MongoDB Atlas | MongoDB (M0 free tier) | Ready | Cluster on Atlas |
| **AI/ML** | Google Cloud | Gemini 2.0 Flash API | Ready | API-based |
| **Payments** | Razorpay | Test mode (rzp_test_*) | Ready | Dashboard.razorpay.com |

---

## What Gets Deployed Where

### Vercel (Frontend)
```
Repository: AI-Mock-Interview-Platform
├── frontend/
│   ├── src/app/          (pages + layouts)
│   ├── src/components/   (React components)
│   ├── src/hooks/        (custom hooks)
│   ├── src/utils/        (API client, auth, etc.)
│   ├── package.json
│   ├── next.config.js
│   └── tailwind.config.js
```

**What's deployed:**
- Next.js static builds
- Client-side React components
- API client configuration
- Environment variables: `NEXT_PUBLIC_API_URL`, etc.

---

### Render (Backend)
```
Repository: AI-Mock-Interview-Platform
├── mock-interview-platform/backend/
│   ├── app/
│   │   ├── routes/       (API endpoints)
│   │   ├── services/     (business logic)
│   │   ├── models/       (MongoDB schemas)
│   │   └── config.py     (configuration)
│   ├── requirements.txt  (Python dependencies)
│   ├── run.py           (entry point)
│   └── render.yaml      (Render config)
```

**What's deployed:**
- Flask application
- All Python dependencies
- Environment variables: `MONGODB_URI`, `GOOGLE_GEMINI_API_KEY`, etc.
- WebSocket support via gunicorn + gthread

---

### MongoDB Atlas (Database)
```
Cluster: ai-mock-interview-prod
├── Database: mock_interview
│   ├── Collection: users
│   ├── Collection: interview_sessions
│   ├── Collection: payments
│   ├── Collection: feedback
│   └── Collection: support_tickets
```

**What's stored:**
- User accounts & authentication data
- Interview sessions & answers
- Payment records
- AI feedback & analysis
- Support tickets

---

## Key Information to Keep Handy

After deployment, save these for future reference:

```
Frontend URL:        https://your-project.vercel.app
Backend API URL:     https://your-service.onrender.com
Backend WebSocket:   wss://your-service.onrender.com (Socket.IO)

GitHub Repo:         https://github.com/YOUR_USERNAME/AI-Mock-Interview-Platform
GitHub Branches:     main (production)

Render Dashboard:    https://render.com/dashboard
Render Service ID:   (shown in Render)

Vercel Dashboard:    https://vercel.com/dashboard
Vercel Project ID:   (shown in Vercel)

MongoDB Atlas:       https://cloud.mongodb.com
Cluster Name:        ai-mock-interview-prod
Database User:       mock_interview_admin

Razorpay Dashboard:  https://dashboard.razorpay.com
Account Type:        Test mode (until ready for live)
```

---

## Environment Variables Reference

### Frontend (.env.local on Vercel)
```
NEXT_PUBLIC_API_URL=https://your-service.onrender.com
NEXT_PUBLIC_SOCKET_URL=https://your-service.onrender.com
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxxx
```

### Backend (.env on Render)
```
MONGODB_URI=mongodb+srv://mock_interview_admin:PASSWORD@cluster.mongodb.net/mock_interview?retryWrites=true&w=majority
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=your-razorpay-secret
JWT_SECRET_KEY=your-secret-key-32-chars-min
SECRET_KEY=your-flask-secret-key
FLASK_DEBUG=False
FRONTEND_URL=https://your-project.vercel.app
ENABLE_GEMINI=true
```

---

## Common Data Flows

### 1. User Registration
```
Frontend Form
    ↓
POST /api/auth/register
    ↓
Backend validates & hashes password
    ↓
MongoDB stores user with:
  - tier: 'free'
  - subscription_start_date: now
  - subscription_end_date: now + 30 days
  - interviews_used_this_month: 0
    ↓
Returns JWT token
    ↓
Frontend stores token + redirects to dashboard
```

### 2. Interview Question Generation
```
Frontend: User creates interview
    ↓
POST /api/interview/generate-questions
    ↓
Backend checks:
  - Has JWT token? ✓
  - Monthly limit exceeded? ✗
  - Subscription active? ✓
    ↓
Calls Gemini API with prompt
    ↓
Returns 3 questions
    ↓
Frontend displays questions
```

### 3. Payment Processing
```
Frontend: User clicks "Upgrade"
    ↓
POST /api/subscription/create-order
    ↓
Backend creates Razorpay order
    ↓
Returns Razorpay order ID
    ↓
Frontend redirects to Razorpay checkout
    ↓
User pays with test card
    ↓
Razorpay redirects back to app
    ↓
Frontend verifies payment
    ↓
POST /api/subscription/verify-payment
    ↓
Backend updates user:
  - tier: 'basic' (or 'pro')
  - subscription_end_date: now + 1 month
    ↓
MongoDB stores payment record
    ↓
Frontend shows upgrade success
```

---

## Health Monitoring

### Key Endpoints to Monitor

```bash
# Backend Health
curl https://your-service.onrender.com/api/health
# Response: {"status": "healthy"}

# Database Connection
curl https://your-service.onrender.com/api/subscription/plans
# Should list all subscription plans

# Frontend
https://your-project.vercel.app
# Should load homepage without errors
```

---

## Scaling Considerations

### Current Setup (Free Tier)
- ✓ Free tier good for testing & small user bases
- ✓ Render free tier goes to sleep after 15 min inactivity
- ✓ MongoDB Atlas M0 has 512MB storage limit
- ✓ Vercel free tier excellent for frontend

### When You Need to Scale
```
Low Traffic (100-500 users/day)
├─ Keep current setup
├─ Monitor performance
└─ Consider upgrading Render to Paid

Medium Traffic (500-5000 users/day)
├─ Upgrade Render to Standard ($12/month)
├─ Enable MongoDB connection pooling
├─ Add caching layer (Redis)
└─ Consider CDN for static assets

High Traffic (5000+ users/day)
├─ Multiple Render instances (load balance)
├─ Upgrade MongoDB to M2+ tier
├─ Add message queue (Redis/RabbitMQ)
├─ Implement caching strategy
└─ Consider separate services for different functions
```

---

## Next Steps After Deployment

1. ✅ **Verify all endpoints working** (see Testing section in main guide)
2. ✅ **Monitor logs daily** for first week
3. ✅ **Set up uptime monitoring** (optional: UptimeRobot.com)
4. ✅ **Configure backups** for MongoDB
5. ✅ **Plan credential rotation** every 3-6 months
6. 🔄 **When ready for live payments:**
   - Get Razorpay live keys
   - Update environment variables
   - Change from test mode to live mode
   - Thoroughly test with small amounts

---

**Ready to deploy? Start with: `VERCEL_AND_RENDER_DEPLOYMENT_GUIDE.md`**

**Quick version? Use: `DEPLOYMENT_QUICK_REFERENCE.md`**
