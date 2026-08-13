# Production Deployment Checklist

Complete this checklist before deploying to production. Use this as a sign-off document.

## Phase 1: Security (CRITICAL)

- [ ] **Credentials Rotation**
  - [ ] All `.env` files removed from Git
  - [ ] All credentials rotated (MongoDB, Gemini, Razorpay, JWT, Secret Key)
  - [ ] See: `CREDENTIALS_ROTATION_GUIDE.md`

- [ ] **Environment Configuration**
  - [ ] `.env.example` created for backend
  - [ ] `.env.local.example` created for frontend (if needed)
  - [ ] `.gitignore` correctly excludes `.env` and `.env.local`

- [ ] **Deployment Secrets**
  - [ ] All secrets configured in Vercel environment variables (frontend)
  - [ ] All secrets configured in Render environment variables (backend)
  - [ ] `FLASK_DEBUG=False` in production
  - [ ] `ENABLE_GEMINI=true` only if Gemini API key is valid

## Phase 2: Dependencies

- [ ] **Backend Dependencies Pinned**
  - [ ] `requirements.txt` uses exact versions (`==`)
  - [ ] Duplicate Gemini SDK removed (only `google-genai`)
  - [ ] All dependencies tested locally
  - [ ] See: `DEPENDENCY_PINNING_GUIDE.md`

- [ ] **Frontend Dependencies Pinned**
  - [ ] `package-lock.json` committed to Git
  - [ ] `npm ci` used in production builds (not `npm install`)
  - [ ] Documentation updated (Next.js 16.3, React 19)

- [ ] **Clean Build Verification**
  ```bash
  # Backend
  cd backend
  rm -rf .venv
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python -m pytest tests/ -v
  
  # Frontend
  cd frontend
  rm -rf node_modules
  npm ci
  npm run lint
  npm run build
  npm start
  ```

## Phase 3: Production Functionality

### 3.1 Authentication & Authorization

- [ ] **User Registration**
  - [ ] New users receive free tier with 3 monthly interviews
  - [ ] Subscription cycle dates (`subscription_start_date`, `subscription_end_date`) are set
  - [ ] Test: Register → Login → Check dashboard

- [ ] **JWT Token**
  - [ ] Token expires after 24 hours
  - [ ] Token refreshing works (if implemented)
  - [ ] Logout clears token from frontend storage
  - [ ] Protected endpoints return 401 without token

- [ ] **Email Uniqueness**
  - [ ] Duplicate email registration rejected
  - [ ] SQL injection attempts on email field handled gracefully

### 3.2 Interview Features

- [ ] **Question Generation**
  - [ ] Free tier: Can generate 3 interviews/month
  - [ ] Basic tier: Can generate 15 interviews/month
  - [ ] Pro tier: Unlimited interviews
  - [ ] Monthly limit enforced at question generation (not answer submission)
  - [ ] All categories available to Basic and Pro tiers
  - [ ] Standard categories only for Free tier (if implemented)

- [ ] **Answer Analysis**
  - [ ] NLP analysis works
  - [ ] Gemini AI feedback includes scores
  - [ ] Video analysis feature-gated to Basic+ tiers
  - [ ] Failed analysis returns user-friendly error (not empty response)

- [ ] **Feedback & History**
  - [ ] Free tier: 7-day feedback history
  - [ ] Basic+ tiers: Unlimited feedback history
  - [ ] Recent interviews display on dashboard

### 3.3 Resume Features

- [ ] **Resume Upload (Pro tier only)**
  - [ ] Free/Basic users get feature-gated error with upgrade prompt
  - [ ] Pro users can upload PDF, DOCX, TXT
  - [ ] File size limit enforced
  - [ ] Analysis returned correctly

### 3.4 Payments

- [ ] **Razorpay Integration**
  - [ ] Test mode working (rzp_test_* keys)
  - [ ] Order creation successful
  - [ ] Checkout redirects to Razorpay correctly
  - [ ] Payment success callback processed
  - [ ] User subscription upgraded after payment
  - [ ] Dashboard reflects new tier immediately

- [ ] **Payment Edge Cases**
  - [ ] Payment failure handled gracefully
  - [ ] Duplicate payment attempts prevented
  - [ ] Payment cancellation handled
  - [ ] Razorpay signature verification validated
  - [ ] Webhook timeout handling implemented

- [ ] **Test Payment Checklist**
  - [ ] Free user → Basic upgrade → payment success
  - [ ] Basic user → Pro upgrade → payment success
  - [ ] Payment failure scenario → user stays on current tier
  - [ ] Duplicate order prevention working

### 3.5 Socket.IO / Real-time Features

- [ ] **WebSocket Connection**
  - [ ] Dashboard updates in real-time
  - [ ] Multiple tabs/devices work simultaneously
  - [ ] Connection persists across page refreshes
  - [ ] Graceful reconnection after network loss

- [ ] **Render Production Testing**
  - [ ] WebSocket works on Render-deployed backend
  - [ ] Polling fallback works if WebSocket unavailable
  - [ ] Real-time dashboard updates work from Vercel frontend → Render backend

## Phase 4: Infrastructure & Performance

- [ ] **MongoDB**
  - [ ] Connection pooling configured
  - [ ] Indexes created on frequently queried fields
  - [ ] Duplicate user email handling works
  - [ ] Connection timeouts properly configured
  - [ ] Backups enabled on MongoDB Atlas
  - [ ] Connection string uses TLS/SSL

- [ ] **Rate Limiting**
  - [ ] Login endpoints rate-limited (max 5 attempts/minute)
  - [ ] Payment endpoints rate-limited
  - [ ] API endpoints rate-limited (if high-traffic expected)

- [ ] **CORS Configuration**
  - [ ] Frontend domain (Vercel) whitelisted
  - [ ] Credentials allowed if needed
  - [ ] Preflight requests handled
  - [ ] No `*` wildcard in production

- [ ] **Monitoring & Logging**
  - [ ] Error logging configured
  - [ ] Application insights/monitoring active
  - [ ] Health check endpoint available
  - [ ] Database connection logs available
  - [ ] Gemini API failures logged

- [ ] **API Validation**
  - [ ] All inputs validated before processing
  - [ ] File uploads validate file type (not just extension)
  - [ ] SQL injection protection enabled
  - [ ] XSS protection enabled
  - [ ] Large requests rejected (max payload size set)

## Phase 5: Testing

### 5.1 End-to-End Testing (Manual)

```
User Flow Checklist:
├── 1. Registration
│   └── Create account with email/password
├── 2. Login
│   └── Login with created credentials
├── 3. Dashboard
│   └── Verify subscription tier displayed (Free)
├── 4. Interview Setup
│   └── Create mock interview session
├── 5. Question Generation
│   └── Generate questions successfully
├── 6. Answer Submission
│   └── Answer question with text/video
├── 7. Feedback
│   └── Receive AI analysis & feedback
├── 8. History
│   └── View previous interviews
├── 9. Resume Upload
│   └── Try to upload (should fail if Free tier)
├── 10. Subscription
│   └── View pricing page
├── 11. Payment (Test Mode)
│   └── Upgrade to Basic/Pro with test payment
├── 12. Post-Upgrade
│   └── Verify new tier features available
├── 13. Dashboard Update
│   └── See new monthly interview limit
└── 14. Logout
    └── Logout successfully
```

### 5.2 Browser Compatibility

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile browsers (iOS Safari, Chrome Android)

### 5.3 Error Scenarios

- [ ] MongoDB connection lost → Graceful fallback
- [ ] Gemini API timeout → User-friendly error
- [ ] Razorpay unavailable → Clear error message
- [ ] Network disconnection → Reconnect handling
- [ ] Invalid JWT token → Redirect to login

## Phase 6: Documentation

- [ ] **README updated**
  - [ ] Correct tech stack versions listed
  - [ ] Installation instructions clear
  - [ ] Environment setup documented

- [ ] **Deployment Guide**
  - [ ] Vercel deployment steps clear
  - [ ] Render deployment steps clear
  - [ ] Environment variables documented
  - [ ] First-time setup instructions provided

- [ ] **API Documentation**
  - [ ] All endpoints documented
  - [ ] Request/response formats shown
  - [ ] Error codes listed
  - [ ] Rate limits documented

## Phase 7: Final Sign-Off

- [ ] **Code Review**
  - [ ] Critical paths reviewed by second person
  - [ ] No hardcoded secrets in code
  - [ ] No console.log() left in production code
  - [ ] No debug flags enabled

- [ ] **Performance**
  - [ ] Lighthouse score for frontend ≥ 80
  - [ ] API response times < 2 seconds
  - [ ] No N+1 database queries
  - [ ] Frontend bundle size reasonable

- [ ] **Security Review**
  - [ ] OWASP top 10 considered
  - [ ] No known CVEs in dependencies
  - [ ] Secrets management verified
  - [ ] Input validation comprehensive

- [ ] **Stakeholder Sign-Off**
  - [ ] Product owner approval
  - [ ] Technical lead approval
  - [ ] Security team approval (if applicable)

## Rollback Plan

If issues arise after deployment:

1. **Immediate Actions**
   - [ ] Revert to previous version
   - [ ] Notify users of maintenance
   - [ ] Check error logs for root cause

2. **Investigation**
   - [ ] Run the same tests from this checklist
   - [ ] Identify the failed component
   - [ ] Fix locally before re-deploying

3. **Re-deployment**
   - [ ] Apply fix to staging environment first
   - [ ] Re-run checklist on staging
   - [ ] Deploy to production
   - [ ] Verify all systems operational

## Deployment Record

**Date:** _______________  
**Version:** _______________  
**Deployed By:** _______________  
**Approved By:** _______________  
**All Checklist Items Completed:** _____ (Yes/No)  
**Issues Found:** _________________________  
**Resolution:** _________________________  
**Final Status:** _____ (Ready / Not Ready / Rolled Back)  

---

## Resources

- [Vercel Deployment Documentation](https://vercel.com/docs)
- [Render Deployment Documentation](https://render.com/docs)
- [OWASP Web Application Security](https://owasp.org/www-project-web-security-testing-guide/)
- [MongoDB Production Checklist](https://docs.mongodb.com/manual/administration/production-checklist-development/)
