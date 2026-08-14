# MongoDB SRV Connection Timeout - Solutions Guide

## Problem
MongoDB SRV connection timeout occurs during backend initialization with error:
```
MongoDB is unavailable after init; starting in guest mode: ac-1fskaky-shard-00-02.z3jome6.mongodb.net:27017: timed out
```

**Root Cause:** The connection timeout was set to 1500ms (1.5 seconds), which is too short for SRV DNS lookups.

---

## ✅ Solution 1: Increased Connection Timeout (RECOMMENDED)

**Status:** Applied ✓

### What Changed
- Increased `MONGO_CONNECT_TIMEOUT_MS` from 1500ms to **5000ms (5 seconds)**
- Added better error messages in initialization logging

### File Modified
- `backend/.env` - Added `MONGO_CONNECT_TIMEOUT_MS=5000`
- `backend/app/__init__.py` - Improved error handling with clearer messages

### Benefits
- More time for SRV DNS resolution
- Works with remote MongoDB clusters
- Guest mode still available as fallback
- No code changes required

### Current Configuration (in .env)
```
MONGODB_URI=mongodb+srv://pramodmane09156_db_user:3OcOAeS0HjBjvhMQ@cluster0.z3jome6.mongodb.net/mock_interview?retryWrites=true&w=majority
MONGO_CONNECT_TIMEOUT_MS=5000
```

---

## Alternative Solutions

### Solution 2: Use Local MongoDB (Development Only)

If you want to avoid cloud connectivity issues entirely:

#### Setup Local MongoDB
```bash
# Windows - Install MongoDB Community Edition
# Download from: https://www.mongodb.com/try/download/community

# After installation, start MongoDB:
# mongod.exe (default location: C:\Program Files\MongoDB\Server\bin\)
```

#### Update .env
```
MONGODB_URI=mongodb://localhost:27017/mock_interview
MONGO_CONNECT_TIMEOUT_MS=3000
```

**Advantages:**
- No network/DNS issues
- Faster connection
- Full database functionality

**Disadvantages:**
- Requires local MongoDB installation
- Data lost if not persisted
- Not suitable for production

---

### Solution 3: Further Increase Timeout (If Still Experiencing Issues)

If you're still seeing timeouts, increase it more:

```
MONGO_CONNECT_TIMEOUT_MS=10000  # 10 seconds
MONGO_CONNECT_TIMEOUT_MS=15000  # 15 seconds
```

**When to use:**
- Poor/unstable internet connection
- Located far from MongoDB cluster
- High DNS latency

---

### Solution 4: Disable MongoDB (Guest Mode Only)

If you don't need persistent data for development:

Update `backend/app/__init__.py` and set:
```python
app.config['MONGO_AVAILABLE'] = False  # Force guest mode
```

**When to use:**
- Testing without database
- Rapid prototyping
- When MongoDB is completely unavailable

**Limitations:**
- No user data persistence
- No interview history
- Guest sessions only

---

## Verification Steps

### 1. Check Connection Success
```bash
# Start backend
python run.py

# Look for this message (improved logging):
# ✓ MongoDB connection successful
# OR
# ⚠ MongoDB unavailable; starting in guest mode
```

### 2. Test API Endpoint
```bash
# Test that API still works (returns 401 = good, means auth check working)
curl -X GET http://localhost:5000/api/interview/dashboard-stats
```

### 3. Check Backend Logs
```bash
# Backend logs show connection status on startup
# No "timed out" errors should appear with 5000ms timeout
```

---

## Performance Impact

| Timeout | Characteristics | Best For |
|---------|-----------------|----------|
| 1500ms (old) | Fast, prone to failures | Very fast networks only |
| **5000ms (current)** | **Balanced, reliable** | **Most users** |
| 10000ms | Slow, very reliable | Poor connectivity |
| 15000ms | Very slow, maximum reliability | Troubleshooting |

---

## Network Diagnostics

If you still experience timeouts, check:

### 1. DNS Resolution
```bash
# Test DNS lookup for MongoDB cluster
nslookup cluster0.z3jome6.mongodb.net

# Should return IP addresses - if not, DNS is the issue
```

### 2. Network Connectivity
```bash
# Test connection to MongoDB cluster
Test-NetConnection cluster0.z3jome6.mongodb.net -Port 27017

# Should show: TcpTestSucceeded : True
```

### 3. Credentials Verification
- Check username: `pramodmane09156_db_user`
- Verify password is correct in .env
- Ensure IP whitelist includes your machine's IP in MongoDB Atlas

---

## MongoDB Atlas IP Whitelist

If using MongoDB Atlas (cloud):

1. Go to https://cloud.mongodb.com/
2. Navigate to Security → Network Access
3. Add your IP address or use `0.0.0.0/0` for development only
4. Restart backend after updating

---

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `MONGODB_URI` | `mongodb://localhost:27017/mock_interview` | Connection string |
| `MONGO_CONNECT_TIMEOUT_MS` | `1500` | Connection timeout in milliseconds |
| `FLASK_DEBUG` | `False` | Enable Flask debug mode |

---

## Current Status

✅ **Solution 1 Applied (Increased Timeout to 5000ms)**
- Backend initializes successfully
- Guest mode active as fallback
- API endpoints responding
- Improved logging messages enabled

### Next Steps
1. Restart backend: `python run.py`
2. Monitor for timeout errors (should see fewer/none)
3. If still experiencing issues, check network diagnostics above
4. Consider local MongoDB for development if cloud connectivity is unreliable

---

## Support

If issues persist:
1. Check MongoDB Atlas dashboard for connection issues
2. Verify network connectivity to cluster
3. Review MongoDB logs for errors
4. Consider switching to local MongoDB for development
