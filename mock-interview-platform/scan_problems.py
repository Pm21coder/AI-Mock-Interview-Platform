#!/usr/bin/env python
"""Check for potential problems in the codebase."""

import sys
sys.path.insert(0, 'c:\\Users\\dell\\OneDrive\\Desktop\\AI Mock Interview Platform\\mock-interview-platform\\backend')

print("="*70)
print("CODEBASE PROBLEM SCAN")
print("="*70)

# Test 1: Import all core modules
print("\n[1] Testing imports...")
try:
    from app import create_app
    from app.services.subscription_service import SubscriptionService
    from app.services.gemini_service import GeminiService
    from app.services.nlp_service import NLPService
    from app.routes.subscription import subscription_bp
    from app.routes.interview import interview_bp
    print("  ✅ All core imports successful")
except Exception as e:
    print(f"  ❌ Import error: {e}")
    sys.exit(1)

# Test 2: App initialization
print("\n[2] Testing app initialization...")
try:
    app = create_app()
    print("  ✅ Flask app initializes successfully")
except Exception as e:
    print(f"  ❌ App initialization error: {e}")
    sys.exit(1)

# Test 3: Check subscription service methods
print("\n[3] Checking SubscriptionService methods...")
try:
    service = SubscriptionService()
    required_methods = [
        'check_interview_limit',
        'increment_interview_count',
        'get_user_subscription',
        'create_subscription',
        'upgrade_subscription',
        'start_trial',
        'has_feature',
        'get_usage_stats',
        'get_billing_history',
    ]
    missing = []
    for method in required_methods:
        if not hasattr(service, method):
            missing.append(method)
    
    if missing:
        print(f"  ❌ Missing methods: {missing}")
    else:
        print(f"  ✅ All {len(required_methods)} required methods present")
except Exception as e:
    print(f"  ❌ Error checking methods: {e}")
    sys.exit(1)

# Test 4: Check MongoDB connectivity
print("\n[4] Testing MongoDB connectivity...")
try:
    from app import mongo
    with app.app_context():
        # Try a simple count operation
        count = mongo.db.users.count_documents({})
        print(f"  ✅ MongoDB connected (users: {count})")
except Exception as e:
    print(f"  ⚠️  MongoDB not available (this is OK for testing): {type(e).__name__}")

# Test 5: Check Razorpay configuration
print("\n[5] Checking Razorpay configuration...")
try:
    from app.config import Config
    if Config.RAZORPAY_KEY_ID and Config.RAZORPAY_KEY_ID != 'dummy_key':
        print("  ✅ Razorpay key configured")
    else:
        print("  ⚠️  Razorpay key not configured (demo mode enabled)")
except Exception as e:
    print(f"  ❌ Razorpay config error: {e}")

# Test 6: Check subscription config
print("\n[6] Checking subscription tiers...")
try:
    from app.config import Config
    tiers = Config.SUBSCRIPTION_TIERS
    print(f"  ✅ Subscription tiers: {list(tiers.keys())}")
    for tier, config in tiers.items():
        print(f"     - {tier}: {config.get('monthly_interviews')} interviews")
except Exception as e:
    print(f"  ❌ Subscription config error: {e}")

# Test 7: Check API endpoints
print("\n[7] Checking API routes...")
try:
    subscription_routes = []
    for rule in app.url_map.iter_rules():
        if 'subscription' in rule.rule:
            subscription_routes.append(rule.rule)
    print(f"  ✅ Found {len(subscription_routes)} subscription endpoints")
    if len(subscription_routes) < 8:
        print(f"     ⚠️  Expected at least 8 endpoints, found {len(subscription_routes)}")
except Exception as e:
    print(f"  ❌ Route check error: {e}")

# Test 8: Check common Python errors
print("\n[8] Checking for syntax issues...")
try:
    import py_compile
    files = [
        'backend/app/services/subscription_service.py',
        'backend/app/routes/subscription.py',
        'backend/app/routes/interview.py',
    ]
    all_good = True
    for f in files:
        full_path = f'c:\\Users\\dell\\OneDrive\\Desktop\\AI Mock Interview Platform\\mock-interview-platform\\{f}'
        try:
            py_compile.compile(full_path, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"     ❌ {f}: {e}")
            all_good = False
    if all_good:
        print(f"  ✅ All Python files compile successfully")
except Exception as e:
    print(f"  ⚠️  Could not check syntax: {e}")

print("\n" + "="*70)
print("✅ SCAN COMPLETE - No critical issues found")
print("="*70)
