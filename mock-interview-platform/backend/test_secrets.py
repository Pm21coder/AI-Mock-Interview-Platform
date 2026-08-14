#!/usr/bin/env python3
"""Test backend initialization with secret key validation."""

import os

# Test 1: Debug mode should allow default secrets
print('Test 1: Debug mode (should allow default secrets)')
os.environ['FLASK_DEBUG'] = 'true'
try:
    from app import create_app
    app = create_app()
    print('✓ Backend initialized successfully in debug mode')
except RuntimeError as e:
    print(f'✗ Failed: {e}')

# Test 2: Production mode should reject default secrets
print()
print('Test 2: Production mode (should reject default secrets)')
os.environ['FLASK_DEBUG'] = 'false'
os.environ['SECRET_KEY'] = 'your-secret-key-change-in-production'
os.environ['JWT_SECRET_KEY'] = 'your-secret-key-change-in-production'

# Need to reload the config module to pick up new env vars
import importlib
import sys
if 'app' in sys.modules:
    del sys.modules['app']
    del sys.modules['app.config']

try:
    from app import create_app as create_app2
    app2 = create_app2()
    print('✗ Backend should have rejected default secrets in production mode')
except RuntimeError as e:
    print('✓ Backend correctly rejected default secrets in production mode')
    print(f'  Error message: {str(e)[:100]}...')
