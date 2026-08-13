# Phase 2: Dependency Management

## Current Issues

1. **Loose version pinning:** Using `>=` allows any version, risking breaking changes
2. **Duplicate Gemini SDKs:** Both `google-generativeai` and `google-genai` installed
3. **No lock file in production:** Deployments may use different dependency versions

## Solution

### Step 1: Remove Duplicate Gemini SDK

The project has migrated to `google-genai`, so `google-generativeai` is redundant.

**File:** `backend/requirements.txt`

```diff
- google-generativeai>=0.8
google-genai>=2.17.0
```

### Step 2: Pin All Dependency Versions

Use exact versions (with `==`) for production stability.

**Example:** `backend/requirements.txt`

```txt
# Web Framework
Flask==3.1.2
Flask-CORS==5.0.1
Flask-SocketIO==5.5.0
simple-websocket==1.1.0

# Database
Flask-PyMongo==3.0.2
PyMongo==4.6.1

# Server
gunicorn==23.0.0

# Environment
python-dotenv==1.1.0

# Authentication
PyJWT==2.10.1
bcrypt==4.3.0

# AI
google-genai==2.17.0

# Payment
razorpay==2.0.1

# DNS
dnspython==2.5.0

# Resume Processing
PyPDF2==3.0.1
python-docx==1.1.2

# Optional: Computer Vision (for video analysis)
# opencv-python>=4.8.0
# mediapipe>=0.10.0

# Optional: NLP
# nltk>=3.8.1
# textblob>=0.17.1

# Optional: ML
# scikit-learn>=1.3.0
```

### Step 3: Lock Dependency Versions for Deployment

Create a `requirements-lock.txt` for production deployments:

```bash
pip freeze > backend/requirements-lock.txt
```

**Workflow:**
- **Development:** Use `requirements.txt` with flexible versions for testing new features
- **Staging:** Test with `requirements-lock.txt` to catch version incompatibilities
- **Production:** Deploy using `requirements-lock.txt` for reproducibility

### Step 4: Update Deployment Configuration

**File:** `backend/render.yaml`

```yaml
services:
  - type: web
    # ... existing config ...
    buildCommand: pip install -r requirements-lock.txt
    # or for flexibility:
    buildCommand: pip install -r requirements.txt
```

### Step 5: Test Dependency Installation

```bash
# Clean test
rm -rf backend/venv
python -m venv backend/venv

# Activate venv
source backend/venv/bin/activate  # Linux/Mac
# or
backend\venv\Scripts\activate  # Windows

# Install with pinned versions
pip install -r backend/requirements.txt

# Run tests
python -m pytest backend/tests/test_subscription.py -v
```

## Documentation Update

Update `README.md`:

```markdown
### Installation

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

## Verification

After updating dependencies:

1. **Run all tests:**
   ```bash
   pytest backend/tests/ -v
   ```

2. **Test Gemini integration:**
   ```bash
   python backend/test_gemini_response.py
   ```

3. **Test MongoDB:**
   ```bash
   python backend/test_mongo_simple.py
   ```

4. **Test Razorpay:**
   ```bash
   python backend/test_razorpay_fix.py
   ```

5. **Start the application:**
   ```bash
   python run.py
   ```
   - Verify no import errors
   - Verify services connect successfully

## Frontend Dependencies

Update `frontend/package.json` similarly:

1. **Pin major versions:**
   ```json
   "dependencies": {
     "next": "16.3.0",
     "react": "19.0.0",
     "react-dom": "19.0.0"
   }
   ```

2. **Generate lock file:**
   ```bash
   npm ci  # Uses package-lock.json for exact versions
   ```

3. **Test build:**
   ```bash
   npm run build
   npm run lint
   npm start
   ```

## Benefits

✅ **Reproducibility:** Same dependencies across dev/staging/production
✅ **Security:** Easier to track and patch vulnerable versions
✅ **Stability:** No surprise breaking changes on new deployments
✅ **Debugging:** Easier to isolate issues when versions are known
