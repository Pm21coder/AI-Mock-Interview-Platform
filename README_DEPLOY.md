# Deployment guide - Frontend (Vercel) & Backend (Render)

This file documents the exact environment variables and quick commands to deploy the frontend on Vercel and the backend on Render for the AI Mock Interview Platform.

IMPORTANT
- Do NOT commit any secrets to source control.
- Add secrets in the respective hosting dashboards (Vercel / Render) for Development / Preview / Production.

---

## Frontend (Vercel)

Required environment variables (set in Vercel Project → Settings → Environment Variables):

- NEXT_PUBLIC_API_BASE_URL (client)
  - Example: https://ai-mock-backend.onrender.com
  - Purpose: base URL for API calls from the browser.

- NEXT_PUBLIC_RAZORPAY_KEY_ID (client)
  - Example: rzp_test_xxx
  - Purpose: Razorpay public key used by client-side checkout.

- NEXT_PUBLIC_APP_NAME (client)
  - Example: "AI Mock Interview"

Optional (client)
- NEXT_PUBLIC_SENTRY_DSN
  - Public DSN for client error monitoring (optional)

Local development
- Copy `.env.example` to `frontend/.env.local` or to project root `.env.local` and update NEXT_PUBLIC_* values for local testing.

Vercel CLI quick commands
- Add a variable interactively: `vercel env add NEXT_PUBLIC_API_BASE_URL production`
- Pull production envs to local: `vercel env pull .env.local`

---

## Backend (Render)

Create a Web Service in Render and set the following environment variables in the Render dashboard for your service. Use the same variable names and values in Preview/Production as appropriate.

Server-only environment variables (set as secrets in Render):

- SECRET_KEY
  - Purpose: Flask session signing
  - Example: replace-with-very-long-secret

- JWT_SECRET_KEY
  - Purpose: JWT signing
  - Example: replace-with-very-long-secret

- MONGODB_URI
  - Purpose: MongoDB connection (the app's config.py reads MONGODB_URI)
  - Example: mongodb+srv://user:pass@cluster0.mongodb.net/ai_mock?retryWrites=true&w=majority

- USE_ATLAS_MONGO (optional)
  - Example: true

- RATE_LIMIT_STORAGE_URI
  - Purpose: rate limiter storage (used in app/__init__.py)
  - Example: redis://:password@redis-host:6379/1

- RATELIMIT_STORAGE_URL
  - Purpose: referenced by config.py — set to the same value as RATE_LIMIT_STORAGE_URI to be safe
  - Example: redis://:password@redis-host:6379/1

- REDIS_URL (optional)
  - Purpose: cache/session storage
  - Example: redis://:password@redis-host:6379/0

- RAZORPAY_KEY_ID
  - Example: rzp_test_xxx

- RAZORPAY_KEY_SECRET
  - Example: rzp_test_secret_xxx

- RAZORPAY_WEBHOOK_SECRET (optional)
  - Example: rzp_webhook_secret_xxx

- FRONTEND_URL
  - Purpose: for CORS and links
  - Example: https://your-frontend.vercel.app

- SENTRY_DSN (optional)

- MASTER_TOKEN_SECRET
  - Purpose: signing master activation tokens

- FLASK_DEBUG
  - Example: false (for production)

Notes about naming
- The repo uses both `RATE_LIMIT_STORAGE_URI` (app/__init__.py) and `RATELIMIT_STORAGE_URL` (config.py). Set BOTH to the same Redis URL in Render to ensure consistent behavior.

Start command & runtime notes
- The repository includes `run.py` as the local entrypoint; it uses `socketio.run(...)` for development.
- In production Render service, use Gunicorn with eventlet worker for Socket.IO compatibility.

Recommended Render startCommand (in `render.yaml` or in Render dashboard):

- `gunicorn -k eventlet -w 1 run:app --bind 0.0.0.0:$PORT`

Why eventlet? Flask-SocketIO requires an async worker for handling websocket long-polling reliably under a WSGI server; eventlet is a lightweight and compatible worker.

If you prefer, Render can run the Python entrypoint directly:
- `python run.py`
However Gunicorn+eventlet is recommended for production.

---

## Quick deploy checklist

1. Add `render.yaml` (already present) or create a Web Service in Render using the repo.
2. In Render, set all server env vars listed above as secrets.
3. Ensure `requirements.txt` includes `eventlet` (this repo has been updated to include it).
4. Deploy the service and inspect logs for any missing env errors.
5. On Vercel, set NEXT_PUBLIC_* env variables and redeploy frontend.

## Testing after deploy

- Master-code activation: Verify the two master codes are recognized:
  - MASTER-BASIC-E8E588F630E6E93F
  - MASTER-PRO-16BAEA3245C7D44A

- Razorpay Sandbox test: Use test keys and perform a checkout. Verify server verifies HMAC signature (order_id|payment_id hashed with RAZORPAY_KEY_SECRET).

---

If desired I can also:
- Update `render.yaml` startCommand to `python run.py` instead of gunicorn (already updated to gunicorn with eventlet in render.yaml).
- Add a small Render "one-off" job recipe for running migrations.
- Create a `backend/Procfile` or Dockerfile for container-based deploys.

