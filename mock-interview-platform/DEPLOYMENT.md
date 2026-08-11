# Deployment Guide

This guide covers deploying the AI Mock Interview Platform to production.

## Architecture

- **Frontend**: Next.js 16 (deploy on Vercel)
- **Backend**: Flask + Flask-SocketIO (deploy on Render/Railway/Fly.io)
- **Database**: MongoDB (MongoDB Atlas recommended)
- **AI**: Google Gemini API

---

## Part 1: Deploy Frontend to Vercel

### Prerequisites
- GitHub/GitLab/Bitbucket account
- Vercel account (sign up at https://vercel.com)
- Backend deployed (see Part 2)

### Step 1: Push to GitHub

```bash
cd mock-interview-platform
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/mock-interview-platform.git
git push -u origin main
```

### Step 2: Deploy on Vercel

1. Go to https://vercel.com/new
2. Import your repository
3. Configure the project:
   - **Framework Preset**: Next.js
   - **Root Directory**: `mock-interview-platform/frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

4. **Environment Variables** (click "Environment Variables"):
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
   ```
   Replace with your actual backend URL from Part 2.

5. Click **Deploy**

### Step 3: Verify Deployment

- Frontend will be available at: `https://your-project.vercel.app`
- Test the homepage and navigation

---

## Part 2: Deploy Backend

### Option A: Deploy on Render (Recommended)

#### Step 1: Prepare Backend

Create `mock-interview-platform/backend/render.yaml`:

```yaml
services:
  - type: web
    name: mock-interview-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn run:app
    envVars:
      - key: MONGODB_URI
        value: mongodb+srv://username:password@cluster.mongodb.net/mock_interview
      - key: GOOGLE_GEMINI_API_KEY
        value: your-gemini-api-key
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_DEBUG
        value: False
```

#### Step 2: Setup MongoDB Atlas

1. Go to https://www.mongodb.com/atlas/database
2. Create a free cluster
3. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/mock_interview`
4. Whitelist Render IPs (or use 0.0.0.0/0 for testing)

#### Step 3: Deploy on Render

1. Go to https://render.com
2. Click "New" → "Blueprint"
3. Connect your GitHub repository
4. Select the `render.yaml` file
5. Click "Apply"

Your backend will be available at: `https://mock-interview-api.onrender.com`

### Option B: Deploy on Railway

1. Go to https://railway.app
2. Create new project from GitHub repo
3. Select `mock-interview-platform/backend` as root
4. Add environment variables:
   ```
   MONGODB_URI=mongodb+srv://...
   GOOGLE_GEMINI_API_KEY=...
   JWT_SECRET_KEY=...
   SECRET_KEY=...
   FLASK_DEBUG=False
   ```
5. Deploy

### Option C: Deploy on Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Run: `fly launch` in `mock-interview-platform/backend`
3. Set secrets: `fly secrets set MONGODB_URI=... GOOGLE_GEMINI_API_KEY=...`
4. Deploy: `fly deploy`

---

## Part 3: Update Vercel with Backend URL

After deploying backend:

1. Go to Vercel dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Update `NEXT_PUBLIC_API_URL` with your backend URL
5. Redeploy the frontend

---

## Part 4: Configure Google Gemini API

1. Go to https://makersuite.google.com/app/apikey
2. Create API key
3. Add to backend environment variables as `GOOGLE_GEMINI_API_KEY`

---

## Part 5: Test Production Deployment

1. Visit your Vercel URL
2. Test homepage: https://your-project.vercel.app
3. Test resume upload: https://your-project.vercel.app/resume
4. Test interview flow: https://your-project.vercel.app/interview/setup
5. Test dashboard: https://your-project.vercel.app/dashboard

---

## Environment Variables Reference

### Frontend (Vercel)
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

### Backend (Render/Railway/Fly.io)
```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/mock_interview
GOOGLE_GEMINI_API_KEY=AIzaSy...
JWT_SECRET_KEY=your-secret-key-here
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
```

---

## Troubleshooting

### CORS Errors
- Ensure backend CORS is configured to allow your Vercel domain
- Check `CORS(app)` in `backend/app/__init__.py`

### API Not Working
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Check backend logs for errors
- Ensure MongoDB connection is working

### Socket.IO Not Connecting
- Verify Socket.IO path in `next.config.js`
- Check that backend Socket.IO is running
- Ensure CORS allows your domain

### Build Failures
- Check Vercel build logs
- Ensure all dependencies are in `package.json`
- Verify Node.js version (should be 18+)

---

## Cost Estimates

### Free Tier (Testing)
- **Vercel**: Free (Hobby plan)
- **Render**: Free (with limitations)
- **MongoDB Atlas**: Free (512 MB)
- **Total**: $0/month

### Production (Small Scale)
- **Vercel Pro**: $20/month
- **Render Starter**: $7/month
- **MongoDB Atlas**: $9/month (M2 cluster)
- **Total**: ~$36/month

---

## Custom Domain (Optional)

### Add Custom Domain to Vercel

1. Buy domain from Namecheap/GoDaddy/Google Domains
2. In Vercel: Settings → Domains → Add domain
3. Update nameservers at your registrar:
   ```
   ns1.vercel-dns.com
   ns2.vercel-dns.com
   ```
4. Wait for DNS propagation (24-48 hours)

### Add Custom Domain to Backend

- **Render**: Settings → Custom Domains
- **Railway**: Settings → Domains
- **Fly.io**: `fly certs add yourdomain.com`

---

## Monitoring

### Vercel Analytics
- Enable in Vercel dashboard
- Monitor page views, performance, errors

### Backend Logs
- **Render**: Logs tab in dashboard
- **Railway**: Deployments → Logs
- **Fly.io**: `fly logs`

### MongoDB Monitoring
- Atlas dashboard shows queries, connections, storage

---

## CI/CD

The deployment is automatic:
- Push to GitHub → Vercel auto-deploys frontend
- Push to GitHub → Render/Railway auto-deploys backend
- No manual intervention needed

---

## Security Checklist

- [ ] Enable HTTPS (automatic on Vercel/Render)
- [ ] Use strong JWT_SECRET_KEY (32+ random characters)
- [ ] Enable MongoDB authentication
- [ ] Whitelist IPs in MongoDB Atlas
- [ ] Set FLASK_DEBUG=False in production
- [ ] Use environment variables for all secrets
- [ ] Enable rate limiting on backend (optional)
- [ ] Add API key validation for Gemini (optional)

---

## Support

For issues:
1. Check Vercel/backend logs
2. Verify environment variables
3. Test API endpoints with Postman/curl
4. Check MongoDB connection
5. Review CORS configuration