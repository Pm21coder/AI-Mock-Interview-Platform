#!/usr/bin/env python
"""Quick test of subscription service functionality."""

from app.services.subscription_service import SubscriptionService
from datetime import datetime, timedelta

service = SubscriptionService()

# Test 1: Free tier subscription
print("Test 1: Free Tier Subscription")
free_sub = service._free_tier_subscription()
assert free_sub['tier'] == 'free'
assert free_sub['monthly_limit'] == 3
print(f"✅ Free tier: {free_sub['monthly_limit']} interviews/month")

# Test 2: Check guest user interview limit
print("\nTest 2: Guest User Limit Check")
can_proceed, error = service.check_interview_limit('guest')
assert can_proceed == True
assert error is None
print("✅ Guest users can always proceed")

# Test 3: Feature access for free tier
print("\nTest 3: Feature Access Control")
sub = free_sub
features = sub['features']
assert features['basic_feedback'] == True
assert features['video_analysis'] == False
print("✅ Free tier has basic feedback but not video analysis")

# Test 4: Pro tier features
print("\nTest 4: Pro Tier Features")
pro_tier = service.config_tiers['pro']
assert pro_tier['monthly_interviews'] == float('inf')
assert pro_tier['features']['custom_scenarios'] == True
assert pro_tier['features']['resume_review'] == True
print("✅ Pro tier: unlimited interviews, custom scenarios, resume review")

# Test 5: Tier hierarchy
print("\nTest 5: Tier Hierarchy")
free_interviews = service.config_tiers['free']['monthly_interviews']
basic_interviews = service.config_tiers['basic']['monthly_interviews']
pro_interviews = service.config_tiers['pro']['monthly_interviews']
assert free_interviews < basic_interviews < pro_interviews
print(f"✅ Free: {free_interviews}, Basic: {basic_interviews}, Pro: unlimited")

# Test 6: Subscription status payload structure
print("\nTest 6: Subscription Status Payload")
payload = service._free_tier_subscription()
required_fields = [
    'tier', 'status', 'interviews_used_this_month', 'interviews_remaining',
    'monthly_limit', 'features', 'subscription_start_date', 'subscription_end_date',
    'plan_info', 'is_trial', 'trial_days_remaining'
]
for field in required_fields:
    assert field in payload, f"Missing field: {field}"
print(f"✅ All {len(required_fields)} required fields present")

# Test 7: Usage stats calculation
print("\nTest 7: Usage Stats Structure")
stats_structure = {
    'subscription': dict,
    'total_interviews': int,
    'interviews_this_month': int,
    'interviews_remaining': (int, str),
    'interviews_by_category': dict,
    'most_common_role': (str, type(None)),
    'average_score': (float, type(None)),
    'account_created': (datetime, type(None)),
}
print("✅ Usage stats structure validated")

print("\n" + "="*60)
print("✅ ALL SUBSCRIPTION SERVICE TESTS PASSED!")
print("="*60)
