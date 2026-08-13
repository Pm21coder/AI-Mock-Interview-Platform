#!/usr/bin/env python
"""Test subscription API endpoints."""

import json
from app import create_app
from app.config import Config

app = create_app()
app.config['TESTING'] = True

# Test the API endpoints
with app.test_client() as client:
    print("="*60)
    print("Testing Subscription API Endpoints")
    print("="*60)
    
    # Test 1: Get Plans
    print("\nTest 1: GET /api/subscription/plans")
    response = client.get('/api/subscription/plans')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = json.loads(response.data)
    assert 'plans' in data
    assert 'free' in data['plans']
    assert 'basic' in data['plans']
    assert 'pro' in data['plans']
    print(f"✅ Available plans: {list(data['plans'].keys())}")
    
    # Test 2: Verify plan structure
    print("\nTest 2: Plan Structure Validation")
    for tier_name, tier_data in data['plans'].items():
        assert 'name' in tier_data
        assert 'price' in tier_data
        assert 'monthly_interviews' in tier_data
        assert 'features' in tier_data
        print(f"  ✅ {tier_name.upper()}: ${tier_data['price']}/month, {tier_data['monthly_interviews']} interviews")
    
    # Test 3: Free plan details
    print("\nTest 3: Free Plan Details")
    free_plan = data['plans']['free']
    assert free_plan['price'] == 0
    assert free_plan['monthly_interviews'] == 3
    assert free_plan['features']['basic_feedback'] == True
    assert free_plan['features']['video_analysis'] == False
    print(f"✅ Free plan: {free_plan['monthly_interviews']} interviews, basic feedback only")
    
    # Test 4: Basic plan details
    print("\nTest 4: Basic Plan Details")
    basic_plan = data['plans']['basic']
    assert basic_plan['price'] == 5
    assert basic_plan['monthly_interviews'] == 15
    assert basic_plan['features']['video_analysis'] == True
    assert basic_plan['features']['unlimited_history'] == True
    print(f"✅ Basic plan: {basic_plan['monthly_interviews']} interviews, advanced features")
    
    # Test 5: Pro plan details
    print("\nTest 5: Pro Plan Details")
    pro_plan = data['plans']['pro']
    assert pro_plan['price'] == 10
    # Handle both infinity and dict representation (MongoDB JSON serialization)
    pro_interviews = pro_plan['monthly_interviews']
    is_unlimited = (pro_interviews == float('inf') or 
                   (isinstance(pro_interviews, dict) and '$numberDouble' in pro_interviews) or
                   pro_interviews == 'unlimited')
    assert is_unlimited, f"Pro plan should have unlimited interviews, got {pro_interviews}"
    assert pro_plan['features']['unlimited_history'] == True
    assert pro_plan['features']['custom_scenarios'] == True
    assert pro_plan['features']['resume_review'] == True
    assert pro_plan['features']['priority_support'] == True
    print(f"✅ Pro plan: unlimited interviews, all premium features")
    
    # Test 6: Feature comparison
    print("\nTest 6: Feature Comparison Across Tiers")
    feature_names = set()
    for tier_data in data['plans'].values():
        feature_names.update(tier_data['features'].keys())
    
    print(f"✅ Total unique features: {len(feature_names)}")
    for feature in sorted(feature_names):
        free_has = data['plans']['free']['features'].get(feature, False)
        basic_has = data['plans']['basic']['features'].get(feature, False)
        pro_has = data['plans']['pro']['features'].get(feature, False)
        
        status = []
        if free_has:
            status.append("Free")
        if basic_has:
            status.append("Basic")
        if pro_has:
            status.append("Pro")
        
        print(f"   {feature}: {', '.join(status)}")
    
    # Test 7: Razorpay amount configuration
    print("\nTest 7: Razorpay Order Amounts")
    from app.config import Config
    for tier, amount in Config.RAZORPAY_ORDER_AMOUNTS.items():
        amount_inr = amount / 100
        print(f"✅ {tier.upper()}: {amount} paise = ₹{amount_inr}")
    
    print("\n" + "="*60)
    print("✅ ALL SUBSCRIPTION ENDPOINT TESTS PASSED!")
    print("="*60)
