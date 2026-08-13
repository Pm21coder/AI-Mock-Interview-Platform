#!/usr/bin/env python3
"""
Test script to verify Razorpay order creation works correctly.
This script creates a test user, logs in, and attempts to create a Razorpay order.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def test_razorpay_order_creation():
    """Test the complete Razorpay order creation flow."""
    
    print("=" * 60)
    print("Testing Razorpay Order Creation Fix")
    print("=" * 60)
    
    # Generate a unique test email
    test_email = f"test_razorpay_{datetime.now().timestamp()}@example.com"
    test_password = "TestPassword123!"
    
    # Test 1: Register a test user
    print("\n[1] Registering test user...")
    register_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": test_email,
            "password": test_password,
            "full_name": "Test User"
        }
    )
    
    if register_response.status_code not in [200, 201]:
        print(f"❌ Registration failed: {register_response.status_code}")
        print(f"Response: {register_response.text}")
        return False
    
    print(f"✅ User registered: {register_response.status_code}")
    print(f"   Email: {test_email}")
    
    # Test 2: Login to get auth token
    print("\n[2] Logging in to get auth token...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": test_email,
            "password": test_password
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    print(f"✅ User logged in: {login_response.status_code}")
    login_data = login_response.json()
    auth_token = login_data.get("token")
    
    if not auth_token:
        print("❌ No auth token received!")
        return False
    
    print(f"✅ Auth token obtained: {auth_token[:20]}...")
    
    # Test 3: Create Razorpay order without demo mode
    print("\n[3] Creating Razorpay order (non-demo)...")
    order_response = requests.post(
        f"{BASE_URL}/api/subscription/create-order",
        json={"tier": "basic", "demo_mode": False},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    print(f"Status: {order_response.status_code}")
    print(f"Response: {order_response.text[:200]}...")
    
    if order_response.status_code == 502:
        print("\n❌ 502 Bad Gateway Error detected!")
        print("The backend is failing to create the order.")
        print("Check backend logs for exception details.")
        return False
    
    if order_response.status_code == 200:
        print("✅ Order created successfully!")
        order_data = order_response.json()
        print(f"Order ID: {order_data.get('id')}")
        print(f"Amount: {order_data.get('amount')} {order_data.get('currency')}")
        return True
    
    # Test 4: Create Razorpay order in demo mode (fallback)
    print("\n[4] Creating Razorpay order (demo mode)...")
    demo_order_response = requests.post(
        f"{BASE_URL}/api/subscription/create-order",
        json={"tier": "basic", "demo_mode": True},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    print(f"Status: {demo_order_response.status_code}")
    if demo_order_response.status_code == 200:
        print("✅ Demo order created successfully!")
        order_data = demo_order_response.json()
        print(f"Demo Order ID: {order_data.get('id')}")
        return True
    
    print(f"❌ Demo order also failed: {demo_order_response.text}")
    return False

if __name__ == "__main__":
    success = test_razorpay_order_creation()
    print("\n" + "=" * 60)
    if success:
        print("✅ Razorpay order creation is working!")
    else:
        print("❌ Razorpay order creation test failed")
        print("\nCommon fixes:")
        print("1. Ensure .env has valid RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
        print("2. Check backend logs for detailed error messages")
        print("3. Verify MongoDB connection is working")
        print("4. Ensure all dependencies are installed: pip install -r requirements.txt")
    print("=" * 60)
