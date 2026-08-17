# Quick Deployment Checklist (30-minute version)

Use this for a fast deployment reference. Full guide: `VERCEL_AND_RENDER_DEPLOYMENT_GUIDE.md`

---

## Pre-Deployment (5 minutes)

- [ ] Code pushed to GitHub
- [ ] `.env` files removed from Git (check `.gitignore`)
- [ ] Dependencies pinned to exact versions (`==`)
  - Backend: `Flask==3.1.2`, `PyMongo==4.6.1`, etc.
  - Frontend: `package-lock.json` committed
- [ ] Have these ready:
  - MongoDB connection string
  - Gemini API key
  - Razorpay test keys (rzp_test_*)
  - JWT secret (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

---

## Step 1: MongoDB Atlas Setup (5 minutes)

1. Create cluster (M0 free tier)
2. Create user: `mock_interview_admin` with strong password
3. Allow access from anywhere (0.0.0.0/0)
4. Copy connection string:
   ```
   mongodb+srv://mock_interview_admin:PASSWORD@cluster.mongodb.net/mock_interview?retryWrites=true&w=majority
   ```

✅ **Save connection string!**

---

## Step 2: Deploy Backend to Render (5 minutes)

1. Render.com → New Web Service → Connect GitHub
2. Select: `AI-Mock-Interview-Platform`
3. Settings:
   - **Root Directory:** `mock-interview-platform/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --workers 2 --threads 100 --worker-class gthread --bind 0.0.0.0:$PORT run:app`
4. Environment Variables (add all):
   ```
   MONGODB_URI = mongodb+srv://...
   GOOGLE_GEMINI_API_KEY = your-key
   RAZORPAY_KEY_ID = rzp_test_...
   RAZORPAY_KEY_SECRET = your-secret
   JWT_SECRET_KEY = (generate with Python)
   SECRET_KEY = (generate with Python)
   FLASK_DEBUG = False
   FRONTEND_URL = https://your-vercel-frontend.vercel.app (add after step 3)
   ENABLE_GEMINI = true

   # If you plan to run long-running AI tasks or enable job-based processing,
   # configure a Redis URL and run an RQ worker. Example:
   REDIS_URL = redis://:<password>@redis-host:6379/0
   # Start a worker on the backend host (or dedicated worker dyno/container):
   #   cd mock-interview-platform && REDIS_URL=$REDIS_URL python backend/worker.py
   # The backend will automatically enqueue jobs to Redis when REDIS_URL is set.
   ```
5. Click Deploy

⏳ **Wait 5-10 minutes for deployment**

✅ **Save backend URL:** `https://your-service.onrender.com`

---

## Step 3: Deploy Frontend to Vercel (5 minutes)

1. Vercel.com → Add New Project → Connect GitHub
2. Select: `AI-Mock-Interview-Platform`
3. Settings:
   - **Root Directory:** `mock-interview-platform/frontend`
   - **Build Command:** `npm run build`
   - **Framework:** Next.js
4. Environment Variables:
   ```
   NEXT_PUBLIC_API_URL = https://your-backend-url.onrender.com
   NEXT_PUBLIC_SOCKET_URL = https://your-backend-url.onrender.com
   NEXT_PUBLIC_RAZORPAY_KEY_ID = rzp_test_...
   ```
5. Click Deploy

⏳ **Wait 3-5 minutes for deployment**

✅ **Save frontend URL:** `https://your-project.vercel.app`

---

## Step 4: Update Backend Frontend URL (2 minutes)

Now that you have Vercel URL:

1. Render → Your Service → Environment
2. Find `FRONTEND_URL`
3. Update to: `https://your-frontend-url.vercel.app`
4. Save

✅ **Backend will redeploy automatically**

---

## Step 5: Test Deployment (5 minutes)

### Health Check
```bash
curl https://your-backend.onrender.com/api/health
# Should return: {"status": "healthy"}
```

### Frontend Load
- Open: `https://your-frontend.vercel.app`
- Should load homepage

### Full Test Flow
1. **Register** → Create account
2. **Login** → Login with credentials
3. **Interview** → Create and answer questions
4. **Payment** → Try upgrade with test card:
   - Number: `4111 1111 1111 1111`
   - CVC: `123`
   - OTP: `123456`

✅ **All working? You're deployed!**

---

## Troubleshooting (Quick Fixes)

| Problem | Solution |
|---------|----------|
| Backend won't deploy | Check Render logs → verify Python syntax |
| Frontend won't load | Check Vercel logs → verify npm install works |
| Can't connect to backend | Add `CORS_ORIGINS` to Render environment |
| WebSocket fails | Verify `NEXT_PUBLIC_SOCKET_URL` matches backend URL |
| Database errors | Verify MongoDB connection string + password |
| Payment fails | Use test keys (rzp_test_*), not live keys |

---

## Important URLs

**After deployment, save these:**

```
Frontend: https://your-frontend.vercel.app
Backend:  https://your-backend.onrender.com
GitHub:   https://github.com/YOUR_USERNAME/AI-Mock-Interview-Platform
MongoDB:  https://cloud.mongodb.com
Render:   https://render.com/dashboard
Vercel:   https://vercel.com/dashboard
Razorpay: https://dashboard.razorpay.com
```

---

## Next Deployment Tips

**To update code after deployment:**

1. **Backend changes:**
   - Commit and push to GitHub
   - Render auto-redeploys (watch Render → Deploy log)

2. **Frontend changes:**
   - Commit and push to GitHub
   - Vercel auto-redeploys (watch Vercel → Deployments)

3. **Environment variable changes:**
   - Update in Render or Vercel dashboard
   - Manual redeploy needed (both platforms)

---

**🎉 Deployment Complete! Your app is live!**

For detailed troubleshooting, see: `VERCEL_AND_RENDER_DEPLOYMENT_GUIDE.md`
