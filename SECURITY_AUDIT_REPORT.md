# Security & Code Quality Audit Report

**Date**: August 14, 2026  
**Scope**: Full application review (backend Python/Flask + frontend Next.js/React)  
**Status**: Audit complete - issues identified and documented below

---

## 🔴 CRITICAL Issues

### 1. **CORS Allows All Origins** 
**File**: `backend/app/__init__.py` line 9, 55  
**Issue**: Both Flask-CORS and Flask-SocketIO are configured to accept requests from any origin:
```python
socketio = SocketIO(cors_allowed_origins='*')  # Line 9
CORS(app)  # Line 55 - default is all origins
```

**Risk**: Any website can make requests to your API and perform actions on behalf of authenticated users (CSRF attacks).

**Fix**:
```python
# Restrict to specific origins
allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
socketio = SocketIO(cors_allowed_origins=allowed_origins)
CORS(app, origins=allowed_origins)
```

**Action Required**: 
- Update config.py to add `CORS_ORIGINS` environment variable
- Update app initialization to use restricted origins
- In production, set to your actual frontend domain only

---

### 2. **No Rate Limiting on Critical Endpoints**
**Files**: All API routes in `backend/app/routes/`  
**Issue**: No rate limiting on sensitive endpoints like:
- `/api/auth/login` - vulnerable to brute force
- `/api/auth/register` - vulnerable to spam/DoS
- `/api/razorpay/*` - payment endpoints could be abused
- `/api/interview/generate-questions` - can be spam-attacked

**Risk**: Attackers can brute-force credentials, spam account creation, or trigger expensive Gemini API calls.

**Fix**: Install and configure Flask-Limiter:
```bash
pip install Flask-Limiter
```

Add to `backend/app/__init__.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# On specific routes:
@limiter.limit("5 per minute")  # Brute force protection
@auth_bp.route('/login', methods=['POST'])
def login():
    ...
```

**Action Required**: Implement rate limiting before production deployment.

---

### 3. **Secrets at Repo Root (Already Partially Fixed)**
**Status**: ✅ FIXED in this session
- Root `.env` and `.env.local` deleted
- `.gitignore` updated to unanchor paths
- But: Secrets were exposed in git history before deletion

**Remaining Action**: 
- Rotate the exposed Razorpay test keys (even though they're test keys)
- Add pre-commit hook to prevent .env from being committed again

---

## 🟠 HIGH Priority Issues

### 4. **No Request Input Validation/Sanitization**
**Files**: All Flask routes  
**Issue**: While endpoints check for required fields, there's minimal validation of input content. Example:
```python
# backend/app/routes/interview.py line 141
answer = (data.get('answer') or '').strip()  # Only strips whitespace
question = data.get('question')  # No validation of content
```

**Risk**: 
- Very long strings could cause DoS
- Special characters could cause injection attacks
- No size limits on uploaded files

**Recommendations**:
1. Add max length validation to text fields
2. Add file size limits for resume uploads
3. Sanitize HTML/script content if displayed

Example fix:
```python
MAX_ANSWER_LENGTH = 10000
MAX_QUESTION_LENGTH = 2000

if len(answer) > MAX_ANSWER_LENGTH:
    return jsonify({'error': 'Answer too long'}), 400
if len(question) > MAX_QUESTION_LENGTH:
    return jsonify({'error': 'Question too long'}), 400
```

### 5. **Sensitive Error Details in API Responses**
**Files**: `backend/app/routes/interview.py` line 206, and similar patterns throughout

**Issue**: Some error responses might leak implementation details:
```python
except Exception as exc:
    return jsonify({'error': str(exc)}), 500  # Exposes full error message
```

**Risk**: Stack traces or database errors could reveal system architecture to attackers.

**Fix**: Always return generic error messages in production:
```python
except Exception as exc:
    logger.error(f'Internal error: {exc}')  # Log full error
    return jsonify({'error': 'An error occurred. Please try again.'}), 500  # Generic response
```

### 6. **Missing HTTPS Enforcement in Production**
**Issue**: No enforcement of HTTPS in production. While hosting providers handle this, the Flask app doesn't redirect HTTP → HTTPS.

**Fix**: Add to `backend/app/__init__.py`:
```python
from flask_talisman import Talisman

if not app.config['FLASK_DEBUG']:
    Talisman(app, force_https=True)
```

---

## 🟡 MEDIUM Priority Issues

### 7. **JWT Expiration Too Long (30 days)**
**File**: `backend/app/routes/auth.py` line 75  
**Issue**: Tokens expire after 30 days, which is quite long:
```python
'exp': datetime.utcnow() + timedelta(days=30)
```

**Risk**: Compromised tokens are valid for a full month.

**Recommendation**: Reduce to 24 hours with refresh token rotation:
```python
'exp': datetime.utcnow() + timedelta(hours=24)
```

### 8. **No Logging/Auditing of Payment Events**
**Files**: `backend/app/routes/subscription.py`  
**Issue**: Payment verification and upgrades are logged minimally. No audit trail for financial transactions.

**Risk**: Difficult to detect fraud or unauthorized access.

**Fix**: Add detailed logging:
```python
logger.info(f'User {user_id} upgraded from {old_tier} to {new_tier}')
logger.info(f'Payment verified: order_id={order_id}, amount={amount}, user_id={user_id}')
```

### 9. **No HTTPS Redirect from HTTP**
**Issue**: No automatic redirect from HTTP to HTTPS in the Flask app.

**Fix**: Add redirect middleware:
```python
@app.before_request
def before_request():
    if not app.config['FLASK_DEBUG'] and not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

### 10. **MongoDB Connection String Not Validated**
**Issue**: No validation that MONGODB_URI is properly formatted before use.

**Risk**: Misconfigured connection strings fail silently with fallback to guest mode.

**Fix**: Test connection at startup:
```python
def _check_mongodb_connection(uri):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command('ping')
        client.close()
        return True
    except Exception as e:
        logger.error(f'MongoDB connection failed: {e}')
        return False
```

---

## 🟢 LOW Priority Issues (Hardening)

### 11. **Missing Security Headers**
Add to `backend/app/__init__.py`:
```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### 12. **Password Requirements Not Enforced**
**File**: `backend/app/routes/auth.py` line 82  
**Issue**: Passwords are not validated for complexity:
```python
password = data.get('password') or ''

if not email or '@' not in email or not password:
    return jsonify({'error': 'Email and password are required'}), 400
```

**Risk**: Weak passwords can be brute-forced.

**Fix**: Add password validation:
```python
def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain a digit"
    if not any(char.isupper() for char in password):
        return False, "Password must contain an uppercase letter"
    return True, None
```

### 13. **Frontend: No CSP (Content Security Policy)**
**Issue**: Next.js app has no CSP headers to prevent XSS attacks.

**Fix**: Add to `frontend/next.config.js`:
```javascript
async headers() {
  return [
    {
      source: '/:path*',
      headers: [
        {
          key: 'Content-Security-Policy',
          value: "default-src 'self'; script-src 'self' 'unsafe-inline' checkout.razorpay.com; img-src 'self' data:; font-src 'self'"
        }
      ]
    }
  ]
}
```

### 14. **Frontend: Missing Dependency Security Scan**
**Issue**: No regular npm audit for vulnerable dependencies.

**Recommendation**: Add to CI/CD:
```bash
npm audit --audit-level=moderate
```

Or run locally:
```bash
cd mock-interview-platform/frontend
npm audit
```

---

## ✅ What's Good

### Security Strengths
- ✅ Passwords are hashed with bcrypt (strong algorithm)
- ✅ JWT authentication is properly implemented
- ✅ API endpoints require valid tokens (token_required decorator)
- ✅ Database queries use PyMongo which prevents MongoDB injection
- ✅ RAZORPAY keys are properly marked as NEXT_PUBLIC vs SECRET
- ✅ Frontend .env variables are properly split (public vs local)
- ✅ Error handling is comprehensive in most routes
- ✅ Sensitive routes check subscription tier before allowing access

### Code Quality Strengths
- ✅ Comprehensive error handling in API routes
- ✅ Proper try/catch patterns in async/await code
- ✅ Input validation for required fields
- ✅ Graceful fallbacks (guest mode, Gemini fallback)
- ✅ Clear separation of concerns (services, routes, utils)
- ✅ Requirements.txt matches actual imports
- ✅ Environment variables used for configuration

---

## Recommended Priority Order for Fixes

1. **CRITICAL** (Before production):
   - [ ] Implement CORS origin restriction
   - [ ] Implement rate limiting on auth and payment endpoints
   - [ ] Rotate exposed API keys (even test keys)

2. **HIGH** (Before first public deployment):
   - [ ] Add input validation/sanitization
   - [ ] Generic error messages in production
   - [ ] HTTPS enforcement

3. **MEDIUM** (Before large-scale deployment):
   - [ ] Reduce JWT expiration to 24 hours
   - [ ] Add payment audit logging
   - [ ] Validate MongoDB connection at startup

4. **LOW** (Good practice):
   - [ ] Add security headers
   - [ ] Enforce password requirements
   - [ ] Add CSP headers
   - [ ] Run npm audit regularly

---

## Testing Recommendations

### Security Testing
```bash
# Check for vulnerable dependencies
cd mock-interview-platform/frontend && npm audit
cd mock-interview-platform/backend && pip-audit

# Test CORS restrictions
curl -H "Origin: https://evil.com" http://localhost:5000/api/interview/generate-questions

# Test rate limiting
for i in {1..20}; do curl -X POST http://localhost:5000/api/auth/login; done

# Test JWT expiration (create token, wait 24h+, try to use)
```

### Manual Testing Checklist
- [ ] Can't access protected endpoints without valid JWT
- [ ] CORS blocks requests from other origins
- [ ] Rate limiting triggers after N requests
- [ ] Payment endpoints reject invalid input
- [ ] Database connection errors don't crash server
- [ ] Frontend gracefully handles API errors

---

## Files That Need Updates

| File | Issue | Priority |
|------|-------|----------|
| `backend/app/__init__.py` | CORS, rate limiting, security headers | CRITICAL |
| `backend/app/config.py` | Add CORS_ORIGINS env var | CRITICAL |
| `backend/app/routes/auth.py` | Rate limiting, password validation | HIGH |
| `backend/app/routes/subscription.py` | Payment audit logging | MEDIUM |
| `backend/requirements.txt` | Add flask-limiter, flask-talisman | CRITICAL |
| `frontend/next.config.js` | Add CSP headers, HTTPS redirect | HIGH |

---

## Deployment Checklist

Before deploying to production:

- [ ] CORS restricted to your domain only
- [ ] Rate limiting implemented
- [ ] JWT expiration set to 24 hours
- [ ] FLASK_DEBUG=false in environment
- [ ] SECRET_KEY and JWT_SECRET_KEY are unique and strong
- [ ] Razorpay keys are production keys (not test)
- [ ] HTTPS enforced
- [ ] Security headers added
- [ ] Error messages are generic (no stack traces to users)
- [ ] Payment logging enabled
- [ ] All API keys removed from code and only in .env
- [ ] .gitignore prevents .env commits
- [ ] MongoDB backups configured

---

## Summary

The application has a **solid foundation** with good error handling and proper authentication. The main security gaps are:

1. **CORS misconfiguration** - Fix immediately
2. **No rate limiting** - Implement before production
3. **Input validation gaps** - Add bounds checking
4. **Long JWT expiration** - Reduce to 24 hours

Estimated effort to address all issues: **8-12 hours**

With these fixes implemented, the application will be production-ready from a security perspective.
