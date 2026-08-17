#!/usr/bin/env python3
"""
API Connection Diagnostics Tool
Helps diagnose why the frontend can't connect to the backend
"""

import requests
import sys
import json
import subprocess
from urllib.parse import urljoin

# Configuration
BACKEND_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:3000"
TEST_ENDPOINTS = [
    "/api/health",
    "/api/auth/me",
    "/api/subscription/plans",
    "/api/subscription/question-categories",
]

def test_backend_running():
    """Check if backend server is running"""
    print("1️⃣  Testing if backend is running...")
    try:
        response = requests.get(urljoin(BACKEND_URL, "/api/health"), timeout=2)
        print(f"   ✅ Backend is running! Status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to {BACKEND_URL}")
        print(f"      Make sure backend is running: python run.py")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_cors_headers():
    """Check if CORS headers are properly configured"""
    print("\n2️⃣  Testing CORS configuration...")
    try:
        headers = {
            "Origin": FRONTEND_URL,
            "Access-Control-Request-Method": "GET"
        }
        response = requests.options(urljoin(BACKEND_URL, "/api/health"), headers=headers)
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
        }
        
        print(f"   Response headers:")
        for key, value in cors_headers.items():
            if value:
                print(f"   - {key}: {value}")
        
        if cors_headers["Access-Control-Allow-Origin"] == FRONTEND_URL:
            print(f"   ✅ CORS configured to allow {FRONTEND_URL}")
            return True
        else:
            print(f"   ⚠️  CORS may not be allowing {FRONTEND_URL}")
            print(f"      Allowed origin: {cors_headers['Access-Control-Allow-Origin']}")
            return False
    except Exception as e:
        print(f"   ❌ CORS test failed: {e}")
        return False

def test_api_endpoints():
    """Test various API endpoints"""
    print("\n3️⃣  Testing API endpoints...")
    
    for endpoint in TEST_ENDPOINTS:
        url = urljoin(BACKEND_URL, endpoint)
        try:
            response = requests.get(url, timeout=3)
            status = response.status_code
            
            # 200 = success, 401 = unauthorized (expected without token), others = error
            if status == 200:
                print(f"   ✅ {endpoint} -> {status}")
            elif status == 401:
                print(f"   ⚠️  {endpoint} -> {status} (Unauthorized - need login token)")
            else:
                print(f"   ❌ {endpoint} -> {status}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ {endpoint} -> Connection failed")
        except Exception as e:
            print(f"   ❌ {endpoint} -> Error: {str(e)[:50]}")

def test_frontend_running():
    """Check if frontend is running"""
    print("\n4️⃣  Testing if frontend is running...")
    try:
        response = requests.get(FRONTEND_URL, timeout=2)
        print(f"   ✅ Frontend is running at {FRONTEND_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  Cannot reach {FRONTEND_URL}")
        print(f"      Frontend may not be running. Start with: npm run dev")
        return False
    except Exception as e:
        print(f"   ⚠️  Error connecting to frontend: {e}")
        return False

def check_environment():
    """Check environment configuration"""
    print("\n5️⃣  Checking environment configuration...")
    
    # Check if .env.local exists in frontend
    try:
        with open("./frontend/.env.local", "r") as f:
            content = f.read()
            if "NEXT_PUBLIC_API_URL" in content:
                print("   ✅ Frontend .env.local has NEXT_PUBLIC_API_URL")
                for line in content.split("\n"):
                    if "NEXT_PUBLIC_API_URL" in line:
                        print(f"      {line}")
            else:
                print("   ⚠️  NEXT_PUBLIC_API_URL not found in frontend/.env.local")
    except FileNotFoundError:
        print("   ⚠️  frontend/.env.local not found")
    except Exception as e:
        print(f"   ⚠️  Error reading .env.local: {e}")

def print_summary():
    """Print diagnostic summary"""
    print("\n" + "="*60)
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*60)
    
    backend_ok = test_backend_running()
    cors_ok = test_cors_headers() if backend_ok else False
    test_api_endpoints()
    frontend_ok = test_frontend_running()
    check_environment()
    
    print("\n" + "="*60)
    if backend_ok and frontend_ok:
        print("✅ Both frontend and backend are running!")
        print("   Try refreshing the browser at http://localhost:3000")
    else:
        print("❌ Some services are not running:")
        if not backend_ok:
            print("   - Backend is not running at http://localhost:5000")
            print("     Start it: cd backend && python run.py")
        if not frontend_ok:
            print("   - Frontend is not running at http://localhost:3000")
            print("     Start it: cd frontend && npm run dev")
    print("="*60)

if __name__ == "__main__":
    try:
        print("🔍 API Connection Diagnostics")
        print("=" * 60)
        print_summary()
    except KeyboardInterrupt:
        print("\n\nCanceled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
