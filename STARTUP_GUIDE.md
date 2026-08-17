# Quick Startup Guide - AI Mock Interview Platform

This guide helps you start both the backend and frontend servers for local development.

## Prerequisites

- Node.js 18+ (for frontend)
- Python 3.8+ (for backend)
- Virtual environment activated in backend folder

## Starting the Backend

```bash
# Navigate to backend directory
cd mock-interview-platform/backend

# Activate virtual environment
.venv\Scripts\activate  # Windows
# OR
source .venv/bin/activate  # Mac/Linux

# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the Flask development server
python run.py

# Expected output:
# * Running on http://127.0.0.1:5000
# * Running on http://10.x.x.x:5000
```

**Keep this terminal window open!** The backend must keep running for the frontend to communicate with it.

---

## Starting the Frontend (New Terminal Window)

```bash
# Navigate to frontend directory  
cd mock-interview-platform/frontend

# Install dependencies (if not already done)
npm install

# Start the Next.js development server
npm run dev

# Expected output:
# ▲ Next.js 16.3.0
# - Local:        http://127.0.0.1:3000
# - Environments: .env.local
```

Open your browser to `http://localhost:3000`

---

## Troubleshooting Network Errors

If you see "Network Error" when fetching data:

### 1. **Backend Not Running?**
- Check if the terminal running `python run.py` is still open
- Look for: `Running on http://127.0.0.1:5000`
- If not, start the backend server (see above)

### 2. **Frontend Can't Find Backend?**
- Verify `.env.local` in the frontend directory contains:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:5000
  ```
- If missing or incorrect, update and restart frontend with `npm run dev`

### 3. **CORS Error (Different From Network Error)**
- CORS errors show in the browser console with message like "Access to XMLHttpRequest has been blocked by CORS policy"
- To fix: Ensure backend is allowing the frontend origin
- The backend allows `http://localhost:3000` by default
- To add more origins: set environment variable
  ```bash
  export CORS_ORIGINS="http://localhost:3000,http://localhost:3001,https://yourdomain.com"
  ```

### 4. **Port Already In Use?**
- **Backend (5000)**: Kill the process or change port
  ```bash
  # Windows: Find process using port 5000
  netstat -ano | findstr :5000
  taskkill /PID <PID> /F
  
  # Mac/Linux:
  lsof -i :5000
  kill -9 <PID>
  ```
- **Frontend (3000)**: Next.js will automatically use 3001 if 3000 is taken

---

## Common Issues

### "ModuleNotFoundError: No module named 'flask_limiter'"
- **Solution**: Backend dependencies need to be installed
  ```bash
  cd backend
  .venv\Scripts\pip install -r requirements.txt
  ```

### "MongoDB connection failed" (Warning)
- **This is normal for local development!** The app falls back to guest mode
- To use MongoDB: Start Docker container or set `USE_ATLAS_MONGO=true`

### "TypeError: Cannot read property '_id' of undefined"
- **Likely cause**: User not logged in (no auth token)
- **Solution**: Register and login first at `http://localhost:3000/register`

### Frontend Shows "502 Bad Gateway" or Timeout
- **Likely cause**: Backend crashed or not responding
- **Solution**: 
  1. Check the backend terminal for errors
  2. Restart the backend: `python run.py`

---

## Environment Variables

### Frontend (mock-interview-platform/frontend/.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:5000      # Backend URL
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_TPHWS... # Test mode key
NEXT_PUBLIC_DEBUG=false                         # Set to 'true' for debug logs
```

### Backend (mock-interview-platform/backend/.env)
```
SECRET_KEY=<random-secret>                      # Session encryption key
JWT_SECRET_KEY=<random-secret>                  # JWT signing key
CORS_ORIGINS=http://localhost:3000              # Allowed origins
FLASK_ENV=development                           # Set to 'production' for deployment
MONGODB_URI=<atlas-uri>                         # MongoDB connection (optional)
GOOGLE_GEMINI_API_KEY=<key>                     # Gemini AI API key (optional)
RAZORPAY_KEY_ID=<key>                           # Razorpay test key (optional)
RAZORPAY_KEY_SECRET=<secret>                    # Razorpay test secret (optional)
```

---

## Testing the Connection

### Test Backend Health
```bash
# In another terminal, test if backend is responding
curl http://localhost:5000/api/health

# Expected: {"status": "ok"} or similar response
```

### Test CORS Configuration
```bash
# Verify CORS is allowing localhost:3000
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS http://localhost:5000/api/auth/me
```

### Enable Debug Mode
Set in frontend `.env.local`:
```
NEXT_PUBLIC_DEBUG=true
```

Then check browser console (F12) for detailed API request logs.

---

## Full Development Setup (One-Time)

```bash
# 1. Install backend dependencies
cd mock-interview-platform/backend
.venv\Scripts\pip install -r requirements.txt

# 2. Install frontend dependencies
cd ../frontend
npm install

# 3. Done! Now you can:
# - Terminal 1: cd backend && python run.py
# - Terminal 2: cd frontend && npm run dev
```

---

## Stopping the Servers

- **Backend**: Press `Ctrl+C` in the backend terminal
- **Frontend**: Press `Ctrl+C` in the frontend terminal

---

## Need Help?

1. Check this guide for your specific error
2. Look at the terminal output for error messages
3. Enable debug logging: `NEXT_PUBLIC_DEBUG=true` in frontend
4. Check browser console (F12) for more details
5. Ensure both servers are actually running (don't close the terminals!)

---

**Key Point**: Both the backend AND frontend servers must be running simultaneously for the application to work!
