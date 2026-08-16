#!/usr/bin/env python
"""Debug script to trace the interview increment flow."""

from app import create_app
from bson.objectid import ObjectId
from app.models.interview import InterviewSession, InterviewQuestion
from app.services.subscription_service import SubscriptionService
import json

app = create_app()

with app.app_context():
    from app import mongo
    
    # Simulate creating a test user like the register endpoint does
    test_email = f'test_debug_{ObjectId()}@example.com'
    test_user = {
        'email': test_email,
        'password_hash': 'hashed_pwd',
        'subscription_tier': 'free',
        'subscription_status': 'active',
        'interviews_used_this_month': 0,
    }
    
    print("=" * 70)
    print("SIMULATING INTERVIEW QUOTA FLOW")
    print("=" * 70)
    
    # Insert the test user
    result = mongo.db.users.insert_one(test_user)
    user_id = result.inserted_id
    print(f"\n1. Created test user with _id: {user_id}")
    
    # Get initial subscription state
    sub_service = SubscriptionService()
    sub = sub_service.get_user_subscription(user_id)
    print(f"\n2. Initial subscription state:")
    print(f"   Tier: {sub['tier']}")
    print(f"   Monthly Limit: {sub['monthly_limit']}")
    print(f"   Used This Month: {sub['interviews_used_this_month']}")
    print(f"   Remaining: {sub['interviews_remaining']}")
    
    # Simulate taking 1 interview (incrementing the count)
    print(f"\n3. Incrementing interview count...")
    new_count = sub_service.increment_interview_count(user_id)
    print(f"   Returned count from increment: {new_count}")
    
    # Check subscription state after increment
    sub = sub_service.get_user_subscription(user_id)
    print(f"\n4. Subscription state after increment:")
    print(f"   Used This Month: {sub['interviews_used_this_month']}")
    print(f"   Remaining: {sub['interviews_remaining']}")
    
    # Verify the MongoDB update actually happened
    user_doc = mongo.db.users.find_one({'_id': user_id})
    print(f"\n5. Direct check from MongoDB:")
    print(f"   interviews_used_this_month in DB: {user_doc.get('interviews_used_this_month', 'NOT FOUND')}")
    
    # Clean up
    mongo.db.users.delete_one({'_id': user_id})
    print(f"\n6. Test user cleaned up")
    
    print("\n" + "=" * 70)
    if sub['interviews_remaining'] == 2:
        print("✓ SUCCESS: Interview count is being tracked correctly!")
        print("  After 1 interview, remaining = 2 (out of 3)")
    else:
        print("✗ FAILED: Interview count is NOT being tracked!")
        print(f"  Expected remaining=2, got remaining={sub['interviews_remaining']}")
    print("=" * 70)
