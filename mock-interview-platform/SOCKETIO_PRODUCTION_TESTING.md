# Socket.IO Production Testing Guide

## Problem

Your local development setup uses:
```python
socketio.run(app)  # Local WebSocket server
```

But production Render uses:
```bash
gunicorn --workers 1 --threads 100 --bind 0.0.0.0:$PORT run:app
```

These are **different execution paths** and WebSocket behavior may differ.

## What to Test

### 1. Local Testing (Before Deployment)

#### 1.1 Test Local WebSocket Connection

```bash
# Terminal 1: Start backend
cd mock-interview-platform/backend
python run.py
# Should output: "Running on http://localhost:5000"
```

```bash
# Terminal 2: Start frontend
cd mock-interview-platform/frontend
npm run dev
# Should output: "Local: http://localhost:3000"
```

Open browser console: `http://localhost:3000`

```javascript
// Browser console test
const socket = io('http://localhost:5000');
socket.on('connect', () => {
  console.log('✅ Connected:', socket.id);
});
socket.on('disconnect', () => {
  console.log('❌ Disconnected');
});
socket.on('error', (error) => {
  console.error('❌ Socket error:', error);
});

// Send test event
socket.emit('test_event', { message: 'Hello' }, (response) => {
  console.log('Server responded:', response);
});
```

#### 1.2 Test Dashboard Real-Time Updates

1. Create an interview on one tab
2. Open dashboard on second tab
3. **Verify:** Dashboard updates in real-time when new interview is created
4. **Test:** Refresh the dashboard tab → updates should persist
5. **Test:** Close/reopen tab → should reconnect automatically

### 2. Staging Testing (Render Deployment)

#### 2.1 Deploy to Render

1. Push code to GitHub
2. Trigger Render deployment
3. Wait for build to complete

#### 2.2 Test WebSocket on Render

Replace `http://localhost:5000` with your Render backend URL (e.g., `https://your-api.onrender.com`).

```javascript
// Browser console on Vercel frontend
const socket = io('https://your-api.onrender.com', {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5
});

socket.on('connect', () => {
  console.log('✅ Connected to Render:', socket.id);
  console.log('Transport:', socket.io.engine.transport.name);
});

socket.on('error', (error) => {
  console.error('❌ Connection error:', error);
});

socket.on('connect_error', (error) => {
  console.error('❌ Connect error:', error);
});

socket.on('disconnect', (reason) => {
  console.log('❌ Disconnected:', reason);
});
```

#### 2.3 Monitor Connection Type

Socket.IO can use:
- **WebSocket** (preferred, faster)
- **HTTP Long Polling** (fallback if WebSocket blocked)

Check the console output:
```
Transport: websocket      // ✅ Good - native WebSocket
Transport: polling        // 🟡 Okay - fallback polling
```

### 3. Production WebSocket Checklist

- [ ] **Connection Establishment**
  - [ ] Socket connects within 2 seconds
  - [ ] Connection ID (`socket.id`) is unique
  - [ ] Console shows no errors

- [ ] **Message Delivery**
  - [ ] Client → Server events received
  - [ ] Server → Client events received
  - [ ] Real-time dashboard updates work

- [ ] **Reconnection**
  - [ ] Simulate network loss (DevTools → Network → Offline)
  - [ ] Wait 5+ seconds
  - [ ] Reconnect to network
  - [ ] Socket auto-reconnects (should see "reconnect attempt" in logs)

- [ ] **Multiple Connections**
  - [ ] Open dashboard in 2+ browser tabs
  - [ ] Create interview in one tab
  - [ ] Verify all tabs receive update simultaneously

- [ ] **Load Testing**
  - [ ] Multiple users creating interviews concurrently
  - [ ] All receive real-time dashboard updates
  - [ ] No message loss or delays

### 4. Debugging WebSocket Issues

#### 4.1 Enable Socket.IO Debugging

**Backend (Flask):**
```python
# backend/run.py
import logging
logging.getLogger('socketio').setLevel(logging.DEBUG)
logging.getLogger('engineio').setLevel(logging.DEBUG)
```

**Frontend (Next.js):**
```javascript
// frontend/src/utils/api.js
const socket = io(API_URL, {
  debug: true,  // Enables debug logging
  transports: ['websocket', 'polling'],
  reconnection: true,
});
```

#### 4.2 Check Browser DevTools

**Network Tab:**
- WebSocket connection should show in Network tab
- Look for `ws://` (local) or `wss://` (production) connections
- Check "WS" filter to see WebSocket messages

**Console:**
- Check for Socket.IO version and transport
- Look for any error messages
- Monitor reconnection attempts

#### 4.3 Check Render Logs

```bash
# In Render dashboard:
1. Go to your service
2. Logs tab
3. Filter for "Socket" or "WebSocket"
4. Look for connection/disconnection events
```

### 5. Common Socket.IO Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| WebSocket blocked by proxy | Transport shows `polling` | Use polling (slower but works) or configure proxy |
| CORS error | `connect_error` in console | Update `CORS_ORIGINS` in backend config |
| Connection timeout | Connects then immediately disconnects | Check backend logs, verify Render is running |
| Message loss | Some dashboard updates not received | Verify websocket connected, check backend logs |
| Multiple connections | Socket re-connects every few seconds | Check for duplicate socket initialization |

### 6. Production Configuration

**Backend (.env or Render environment):**
```env
FLASK_DEBUG=False
FLASK_ENV=production
```

**Frontend (Vercel):**
```env
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
NEXT_PUBLIC_SOCKET_URL=https://your-api.onrender.com
```

**Socket.IO Configuration (backend/app/socket_events.py):**
```python
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://your-frontend.vercel.app",  # Production frontend
        "http://localhost:3000",  # Local development
    ],
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6,
)
```

### 7. Monitoring Script

Create `backend/test_socket_production.py` to monitor production Socket.IO:

```python
import socketio
import time
from datetime import datetime

# Connect to production backend
sio = socketio.Client(reconnection=True)

@sio.event
def connect():
    print(f"[{datetime.now()}] ✅ Connected to production backend")
    sio.emit('test_event', {'message': 'health check'})

@sio.event
def disconnect():
    print(f"[{datetime.now()}] ❌ Disconnected from production backend")

@sio.on('error')
def on_error(data):
    print(f"[{datetime.now()}] ❌ Error: {data}")

def main():
    backend_url = "https://your-api.onrender.com"
    print(f"Connecting to {backend_url}...")
    
    try:
        sio.connect(backend_url, transports=['websocket', 'polling'])
        print("Connected! Monitoring...")
        
        while True:
            time.sleep(30)
            if sio.connected:
                print(f"[{datetime.now()}] ✅ Still connected")
            else:
                print(f"[{datetime.now()}] ❌ Disconnected, attempting reconnection...")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    main()
```

Run during production monitoring:
```bash
python backend/test_socket_production.py
```

### 8. Final Verification

Before marking Socket.IO as production-ready:

✅ **Local to Local:** ✓ WebSocket works  
✅ **Local Frontend → Render Backend:** ✓ WebSocket works  
✅ **Vercel Frontend → Render Backend:** ✓ WebSocket works  
✅ **Fallback to Polling:** ✓ Polling works if WebSocket blocked  
✅ **Reconnection:** ✓ Auto-reconnects after network loss  
✅ **Load Test:** ✓ Multiple users connected simultaneously  
✅ **Real-time Updates:** ✓ Dashboard updates propagate instantly  
✅ **No Memory Leaks:** ✓ Long-running connections stable  

---

## References

- [Socket.IO Documentation](https://socket.io/docs/)
- [Socket.IO Troubleshooting](https://socket.io/docs/v4/troubleshooting-connection-issues/)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
- [Render WebSocket Support](https://render.com/docs/websocket-support)
