# 🚨 Credentials Rotation Guide

## Critical Action Required

If your project has ever been pushed to a public repository with real credentials in `.env` files, **you must assume those credentials are compromised** and rotate them immediately.

## Credentials to Rotate

### 1. MongoDB Atlas Credentials
**Priority: 🔴 CRITICAL**

- [ ] Go to [MongoDB Atlas Console](https://cloud.mongodb.com/)
- [ ] Navigate to **Database Access**
- [ ] Delete the old user account that was exposed
- [ ] Create a new database user with a **new strong password**
- [ ] Copy the new connection string
- [ ] Update `MONGODB_URI` in your deployment platform (Render, Vercel)

### 2. Google Gemini API Key
**Priority: 🔴 CRITICAL**

- [ ] Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
- [ ] Delete the compromised API key
- [ ] Create a new API key
- [ ] Update `GOOGLE_GEMINI_API_KEY` in your deployment platform

### 3. Razorpay Keys
**Priority: 🔴 CRITICAL**

- [ ] Go to [Razorpay Dashboard Settings](https://dashboard.razorpay.com/settings/api-keys)
- [ ] Regenerate both **API Key ID** and **API Secret**
- [ ] **Verify you're using TEST keys** (rzp_test_*) for development
- [ ] Update `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in your deployment platform
- [ ] Test payments with the new test keys before deploying

### 4. JWT Secret Key
**Priority: 🔴 CRITICAL**

- [ ] Generate a new random string (at least 32 characters)
  ```bash
  # On Linux/Mac:
  openssl rand -hex 32
  
  # On Windows:
  # Use https://www.random.org/cgi-bin/randbytes?nbytes=32&format=h
  ```
- [ ] Update `JWT_SECRET_KEY` in your deployment platform
- [ ] All existing tokens will become invalid (users will need to login again)

### 5. Flask Secret Key
**Priority: 🟠 HIGH**

- [ ] Generate a new random string (at least 32 characters)
- [ ] Update `SECRET_KEY` in your deployment platform

## Steps to Prevent Future Exposure

1. **Verify `.gitignore` is correct:**
   ```
   backend/.env
   frontend/.env.local
   ```

2. **Never commit real secrets:**
   - Always use placeholder values in `.env.example` files
   - Add `.env` and `.env.local` to `.gitignore` BEFORE any commits

3. **Use environment management:**
   - ✅ Store secrets in **Render Environment Variables**
   - ✅ Store secrets in **Vercel Environment Variables**
   - ✅ Store secrets in **local `.env` files (git-ignored)**
   - ❌ Never store secrets in code files
   - ❌ Never store secrets in configuration files checked into Git

4. **Deployment platform setup:**
   - **Vercel:** Settings → Environment Variables
   - **Render:** Environment → Environment Variables
   - Make sure `FLASK_DEBUG=False` in production

5. **Audit your Git history:**
   ```bash
   # Check if secrets were ever committed:
   git log --all -p -- backend/.env | head -100
   ```
   
   If you find real secrets in history, use `git filter-branch` or `BFG Repo-Cleaner` to remove them:
   - [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

## Verification Checklist

- [ ] All new credentials generated and tested locally
- [ ] `.env` and `.env.local` files git-ignored
- [ ] `.env.example` files created with safe placeholders
- [ ] Deployment platforms updated with new credentials
- [ ] Application tested end-to-end with new credentials
- [ ] Old API keys/passwords confirmed deleted from service providers
- [ ] Team members notified of credential rotation

## Testing the Rotation

1. **Locally:**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with NEW TEST credentials
   python run.py
   # Verify all services connect successfully
   ```

2. **On Render/Vercel:**
   - Deploy after updating environment variables
   - Verify logs show successful connections to MongoDB, Gemini, Razorpay
   - Test a complete user flow: Register → Interview → Payment

## References

- [Razorpay Test/Live Mode Documentation](https://razorpay.com/docs/dashboard/testing-live-modes/)
- [MongoDB Security Checklist](https://docs.mongodb.com/manual/administration/security-checklist/)
- [Google Cloud Security Best Practices](https://cloud.google.com/docs/authentication/best-practices)
- [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
