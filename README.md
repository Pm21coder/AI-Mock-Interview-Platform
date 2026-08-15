# AI Mock Interview Platform

An intelligent interview preparation tool featuring AI-powered feedback, computer vision analysis, video recording, and payment integration for premium features.

**Current Status**: Core features working (see [HONEST_STATUS_REPORT.md](mock-interview-platform/HONEST_STATUS_REPORT.md) for detailed audit).

---

## Project Structure

This repository contains both frontend and backend services in a nested structure:

```
AI Mock Interview Platform/
├── mock-interview-platform/
│   ├── frontend/                  # Next.js React app (port 3000)
│   │   ├── package.json
│   │   ├── src/
│   │   └── .env.example
│   ├── backend/                   # Python Flask API (port 5000)
│   │   ├── run.py                 # Entry point
│   │   ├── requirements.txt
│   │   ├── app/
│   │   └── .env.example
│   └── [docs and configuration files]
├── .gitignore
└── README.md (this file)
```

**⚠️ IMPORTANT**: The actual application code lives inside `mock-interview-platform/`. All commands must be run from the correct subdirectories.

---

## Prerequisites

- **Node.js** 18+ and **npm** (for frontend)
- **Python** 3.9+ (for backend)
- **MongoDB** 5.0+ (local or cloud connection string required)
- **Environment variables** (see below)

---

## Quick Start (Development)

### 1. Clone and Navigate
```bash
git clone https://github.com/Pm21coder/AI-Mock-Interview-Platform.git
cd "AI Mock Interview Platform"
```

### 2. Backend Setup
```bash
cd mock-interview-platform/backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys (Gemini, MongoDB, Razorpay).

Start backend: `python run.py` (runs on http://localhost:5000)

### 3. Frontend Setup
In a new terminal:
### Backend tests

```bash
cd mock-interview-platform/backend
pip install -r requirements-dev.txt
python -m pytest
```

### Frontend

```bash
cd mock-interview-platform/frontend
npm install
```

Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL=http://localhost:5000`

Start frontend: `npm run dev` (runs on http://localhost:3000)

---

## Full Installation Guide

### Backend Setup

Navigate to backend directory:
```bash
cd mock-interview-platform/backend
```

Create Python virtual environment:
```bash
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create `.env` file (copy from `.env.example`):
```bash
# Database
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/mock_interview

# AI Provider
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_GEMINI_MODEL=gemini-2.0-flash

# Payment Gateway
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret_key
RAZORPAY_CURRENCY=INR

# Security (MUST change in production)
SECRET_KEY=your_random_secret_key_here
JWT_SECRET_KEY=your_random_jwt_secret_here

# Flask
FLASK_DEBUG=false
FLASK_ENV=production

# Frontend
FRONTEND_URL=http://localhost:3000
```

Start backend:
```bash
python run.py
```

**Backend runs on**: http://localhost:5000

### Frontend Setup

In a new terminal, navigate to frontend directory:
```bash
cd mock-interview-platform/frontend
npm install
```

Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_RAZORPAY_KEY_ID=your_razorpay_public_key_id
```

Start frontend:
```bash
npm run dev
```

**Frontend runs on**: http://localhost:3000

---

## Running the Application

### Development

Open three terminals:

**Terminal 1 - Backend:**
```bash
cd mock-interview-platform/backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python run.py
```

**Terminal 2 - Frontend:**
```bash
cd mock-interview-platform/frontend
npm run dev
```

**Terminal 3 - MongoDB** (if running locally):
```bash
mongod
```

Visit http://localhost:3000

### Production

**Frontend Build:**
```bash
cd mock-interview-platform/frontend
npm run build
npm start
```

**Backend:** Deploy to Render, Heroku, AWS, or your hosting provider with environment variables set.

---

## Environment Variables

### Backend (`mock-interview-platform/backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_DEBUG` | No | `true` for dev (relaxed security), `false` for prod |
| `MONGODB_URI` | Yes | MongoDB connection string |
| `GOOGLE_GEMINI_API_KEY` | Yes | Google AI API key |
| `GOOGLE_GEMINI_MODEL` | No | Model name (default: `gemini-2.0-flash`) |
| `RAZORPAY_KEY_ID` | Yes | Razorpay key ID |
| `RAZORPAY_KEY_SECRET` | Yes | Razorpay secret (keep private) |
| `RAZORPAY_CURRENCY` | No | Currency (default: `INR`) |
| `SECRET_KEY` | Yes | Flask secret (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `JWT_SECRET_KEY` | Yes | JWT signing key (generate same way) |
| `FRONTEND_URL` | No | Frontend URL for CORS (default: `http://localhost:3000`) |

### Frontend (`mock-interview-platform/frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend URL (e.g., `http://localhost:5000`) |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | Yes | Razorpay public key (safe to expose) |

---

## Features

- ✅ **AI-Powered Feedback** - Google Gemini integration with fallback heuristics
- ✅ **Video Recording** - Capture interviews with HUD visualization
- ✅ **Expression Analysis** - Eye contact, confidence, and emotion metrics
- ✅ **Subscription System** - Free/Basic/Pro tiers with usage limits
- ✅ **Payment Integration** - Razorpay for Indian payment processing
- ✅ **Real-time Dashboard** - Socket.IO for live updates
- ✅ **Responsive UI** - Mobile-friendly Next.js frontend
- ✅ **Guest Mode** - Practice without registration
- ⚠️ **Computer Vision** - Currently simulated (real implementation planned)

---

## Troubleshooting

### "Could not read package.json" Error

**Issue**: Running `npm install` from repo root  
**Solution**: Navigate to frontend first
```bash
cd mock-interview-platform/frontend
npm install
```

### "can't open file 'run.py'" Error

**Issue**: Running Python from repo root  
**Solution**: Navigate to backend first
```bash
cd mock-interview-platform/backend
python run.py
```

### MongoDB Connection Fails

**Solution**:
1. Check `MONGODB_URI` in `.env`
2. Ensure MongoDB is running
3. For MongoDB Atlas: verify IP whitelist includes your current IP
4. Test connection: `python -c "from pymongo import MongoClient; MongoClient('YOUR_URI').admin.command('ping')"`

### Payments Not Working

**Solution**:
1. Verify test keys in dev, production keys in prod
2. Check Razorpay dashboard for errors
3. Ensure `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are correct

### Real-time Updates Not Working

**Solution**:
1. Verify backend is running on `http://localhost:5000`
2. Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`
3. Ensure firewall allows WebSocket connections

---

## API Endpoints

**Authentication:**
- `POST /api/auth/register` - Register new account
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/logout` - Logout user

**Interviews:**
- `POST /api/interview/start-session` - Begin interview
- `POST /api/interview/generate-questions` - Get interview questions
- `POST /api/interview/analyze-answer` - Submit answer, get AI feedback

**Subscriptions:**
- `GET /api/subscription/plans` - Fetch all subscription tiers
- `GET /api/subscription/status` - Check user's current plan
- `POST /api/subscription/upgrade` - Upgrade to paid tier

**Payments:**
- `POST /api/razorpay/create-order` - Initiate payment
- `POST /api/razorpay/verify-payment` - Confirm payment

See detailed docs in `mock-interview-platform/` guides.

---

## Security

⚠️ **Never commit `.env` files**. They are in `.gitignore`:
- Backend: `mock-interview-platform/backend/.env`
- Frontend: `mock-interview-platform/frontend/.env.local`

⚠️ **Production Security Checklist:**
- [ ] Set `FLASK_DEBUG=false`
- [ ] Generate unique `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Use production Razorpay keys
- [ ] Use production MongoDB connection
- [ ] Enable HTTPS on frontend
- [ ] Restrict CORS origins
- [ ] Enable rate limiting on API routes

---

## Known Limitations

- Computer vision analysis is currently simulated (not real face detection)
- Guest mode data is lost when backend restarts
- Rate limiting not yet implemented on API endpoints

For full status, see [HONEST_STATUS_REPORT.md](mock-interview-platform/HONEST_STATUS_REPORT.md)

---

## Deployment

### Vercel (Frontend)
```bash
cd mock-interview-platform/frontend
vercel deploy
```

### Render / Heroku (Backend)
Set up environment variables, push code, and deploy.

See detailed guides in `mock-interview-platform/DEPLOYMENT_*.md`

---

## Issues & Support

- Report bugs: [GitHub Issues](https://github.com/Pm21coder/AI-Mock-Interview-Platform/issues)
- Full audit: [HONEST_STATUS_REPORT.md](mock-interview-platform/HONEST_STATUS_REPORT.md)
- Deployment guides: See `mock-interview-platform/` directory
