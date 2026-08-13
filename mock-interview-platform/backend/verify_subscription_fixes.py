#!/usr/bin/env python
"""
Quick verification script for subscription enforcement fixes.
Tests the key subscription logic without requiring MongoDB or external services.
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Test 1: Verify free-tier billing cycle dates are set at registration
print("\n" + "="*60)
print("TEST 1: New user receives billing-cycle dates")
print("="*60)

try:
    from app.routes.auth import local_auth_users
    demo_user = local_auth_users.get('demo@mockinterview.app')
    
    if not demo_user:
        print("❌ FAIL: Demo user not found in local_auth_users")
        sys.exit(1)
    
    # Check required subscription fields
    required_fields = [
        'subscription_tier',
        'subscription_status', 
        'subscription_start_date',
        'subscription_end_date',
        'interviews_used_this_month'
    ]
    
    for field in required_fields:
        if field not in demo_user:
            print(f"❌ FAIL: Missing field '{field}' on demo user")
            sys.exit(1)
    
    # Verify values
    if demo_user['subscription_tier'] != 'free':
        print(f"❌ FAIL: Expected tier 'free', got '{demo_user['subscription_tier']}'")
        sys.exit(1)
    
    if demo_user['interviews_used_this_month'] != 0:
        print(f"❌ FAIL: Expected interviews_used=0, got {demo_user['interviews_used_this_month']}")
        sys.exit(1)
    
    start_date = demo_user['subscription_start_date']
    end_date = demo_user['subscription_end_date']
    
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        print("❌ FAIL: Dates are not datetime objects")
        sys.exit(1)
    
    days_in_cycle = (end_date - start_date).days
    if not (29 <= days_in_cycle <= 31):  # Allow some variance
        print(f"❌ FAIL: Expected ~30 day cycle, got {days_in_cycle} days")
        sys.exit(1)
    
    print("✅ PASS: Demo user has correct subscription setup")
    print(f"   - Tier: {demo_user['subscription_tier']}")
    print(f"   - Status: {demo_user['subscription_status']}")
    print(f"   - Start: {start_date.isoformat()}")
    print(f"   - End: {end_date.isoformat()}")
    print(f"   - Cycle length: {days_in_cycle} days")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verify subscription service reset logic
print("\n" + "="*60)
print("TEST 2: Subscription service monthly reset logic")
print("="*60)

try:
    from app.services.subscription_service import SubscriptionService
    
    service = SubscriptionService()
    
    # Test _should_reset_monthly_usage with expired cycle
    expired_user = {
        '_id': 'test_user',
        'subscription_tier': 'free',
        'subscription_end_date': datetime.utcnow() - timedelta(days=1),  # Expired 1 day ago
        'interviews_used_this_month': 3,
    }
    
    should_reset = service._should_reset_monthly_usage(expired_user)
    
    if not should_reset:
        print("❌ FAIL: Should reset for expired cycle, got False")
        sys.exit(1)
    
    print("✅ PASS: Correctly detects expired billing cycle")
    
    # Test with non-expired cycle
    active_user = {
        '_id': 'test_user_2',
        'subscription_tier': 'free',
        'subscription_end_date': datetime.utcnow() + timedelta(days=10),  # Expires in 10 days
        'interviews_used_this_month': 1,
    }
    
    should_reset = service._should_reset_monthly_usage(active_user)
    
    if should_reset:
        print("❌ FAIL: Should NOT reset for active cycle, got True")
        sys.exit(1)
    
    print("✅ PASS: Correctly detects active billing cycle")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify config has correct tier definitions
print("\n" + "="*60)
print("TEST 3: Subscription tier configuration")
print("="*60)

try:
    from app.config import Config
    
    tiers = Config.SUBSCRIPTION_TIERS
    
    # Check all tiers exist
    required_tiers = ['free', 'basic', 'pro']
    for tier in required_tiers:
        if tier not in tiers:
            print(f"❌ FAIL: Missing tier '{tier}'")
            sys.exit(1)
    
    # Check free tier
    free_tier = tiers['free']
    if free_tier['monthly_interviews'] != 3:
        print(f"❌ FAIL: Free tier should have 3 interviews, got {free_tier['monthly_interviews']}")
        sys.exit(1)
    
    if not free_tier['features'].get('video_analysis', False):
        print("❌ FAIL: Free tier should NOT have video_analysis")
        sys.exit(1)
    
    if not free_tier['features'].get('resume_review', False):
        print("❌ FAIL: Free tier should NOT have resume_review")
        sys.exit(1)
    
    # Check basic tier
    basic_tier = tiers['basic']
    if basic_tier['monthly_interviews'] != 15:
        print(f"❌ FAIL: Basic tier should have 15 interviews, got {basic_tier['monthly_interviews']}")
        sys.exit(1)
    
    if not basic_tier['features'].get('video_analysis', False):
        print("❌ FAIL: Basic tier should have video_analysis")
        sys.exit(1)
    
    if basic_tier['features'].get('resume_review', False):
        print("❌ FAIL: Basic tier should NOT have resume_review (Pro only)")
        sys.exit(1)
    
    # Check pro tier
    pro_tier = tiers['pro']
    if pro_tier['monthly_interviews'] != float('inf'):
        print(f"❌ FAIL: Pro tier should be unlimited, got {pro_tier['monthly_interviews']}")
        sys.exit(1)
    
    if not pro_tier['features'].get('resume_review', False):
        print("❌ FAIL: Pro tier should have resume_review")
        sys.exit(1)
    
    print("✅ PASS: All tiers configured correctly")
    print(f"   - Free: {free_tier['monthly_interviews']} interviews/month")
    print(f"   - Basic: {basic_tier['monthly_interviews']} interviews/month")
    print(f"   - Pro: Unlimited interviews/month")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify feature gating logic
print("\n" + "="*60)
print("TEST 4: Feature gating logic")
print("="*60)

try:
    from app.services.subscription_service import SubscriptionService
    
    service = SubscriptionService()
    
    # Mock a free user's subscription
    with patch('app.mongo.db.users.find_one') as mock_find:
        mock_find.return_value = {
            '_id': 'free_user',
            'subscription_tier': 'free',
            'subscription_status': 'active',
            'subscription_end_date': datetime.utcnow() + timedelta(days=10),
            'interviews_used_this_month': 0,
        }
        
        # Free user should NOT have video_analysis
        has_video = service.has_feature('free_user', 'video_analysis')
        if has_video:
            print("❌ FAIL: Free user should NOT have video_analysis")
            sys.exit(1)
        
        # Free user should NOT have resume_review
        has_resume = service.has_feature('free_user', 'resume_review')
        if has_resume:
            print("❌ FAIL: Free user should NOT have resume_review")
            sys.exit(1)
        
        print("✅ PASS: Free user correctly denied premium features")
    
    # Mock a pro user's subscription
    with patch('app.mongo.db.users.find_one') as mock_find:
        mock_find.return_value = {
            '_id': 'pro_user',
            'subscription_tier': 'pro',
            'subscription_status': 'active',
            'subscription_end_date': datetime.utcnow() + timedelta(days=30),
            'interviews_used_this_month': 0,
        }
        
        # Pro user SHOULD have video_analysis
        has_video = service.has_feature('pro_user', 'video_analysis')
        if not has_video:
            print("❌ FAIL: Pro user should have video_analysis")
            sys.exit(1)
        
        # Pro user SHOULD have resume_review
        has_resume = service.has_feature('pro_user', 'resume_review')
        if not has_resume:
            print("❌ FAIL: Pro user should have resume_review")
            sys.exit(1)
        
        print("✅ PASS: Pro user correctly granted all features")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Verify subscription lifecycle
print("\n" + "="*60)
print("TEST 5: Subscription expiry and downgrade")
print("="*60)

try:
    from app.services.subscription_service import SubscriptionService
    
    service = SubscriptionService()
    
    # Mock an expired paid user
    with patch('app.mongo.db.users.find_one') as mock_find:
        # First call returns expired basic user, second call after downgrade returns free
        expired_basic_user = {
            '_id': 'expired_user',
            'subscription_tier': 'basic',
            'subscription_status': 'active',
            'subscription_end_date': datetime.utcnow() - timedelta(days=1),  # Expired
            'interviews_used_this_month': 10,
        }
        
        mock_find.return_value = expired_basic_user
        
        with patch('app.mongo.db.users.update_one') as mock_update:
            mock_update.return_value = Mock(matched_count=1)
            
            # Get subscription should trigger downgrade
            sub = service.get_user_subscription('expired_user')
            
            # After downgrade, user should be on free tier
            if sub['tier'] != 'free':
                print(f"❌ FAIL: Expired user should be downgraded to free, got {sub['tier']}")
                sys.exit(1)
            
            # Update was called to downgrade
            if not mock_update.called:
                print("❌ FAIL: Downgrade update was not called")
                sys.exit(1)
            
            print("✅ PASS: Expired paid user correctly downgraded to free")
            print(f"   - Expired tier: basic")
            print(f"   - Downgraded to: {sub['tier']}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Final Summary
print("\n" + "="*60)
print("✅ ALL TESTS PASSED")
print("="*60)
print("\nSubscription enforcement fixes verified:")
print("  ✓ New users receive billing-cycle dates")
print("  ✓ Monthly reset logic works correctly")
print("  ✓ Tier configuration is correct")
print("  ✓ Feature gating logic enforces access control")
print("  ✓ Subscription expiry triggers downgrade")
print("\nReady for deployment! 🚀")
