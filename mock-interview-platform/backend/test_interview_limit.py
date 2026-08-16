#!/usr/bin/env python
"""Test script to verify interview limit behavior."""

from app import create_app
from bson.objectid import ObjectId
import json

app = create_app()

with app.app_context():
    from app.services.subscription_service import SubscriptionService
    sub_service = SubscriptionService()
    
    # Test with a free tier user
    test_user_id = ObjectId()
    
    # Simulate creating 4 interviews (limit is 3)
    print('Testing Free Tier Interview Limit (limit=3):')
    print('=' * 60)
    
    for i in range(4):
        can_proceed, error = sub_service.check_interview_limit(test_user_id)
        
        if can_proceed:
            sub_service.increment_interview_count(test_user_id)
            sub = sub_service.get_user_subscription(test_user_id)
            print(f'\nInterview {i+1}: ✓ ALLOWED')
            print(f'  Used: {sub["interviews_used_this_month"]}/{sub["monthly_limit"]}')
            print(f'  Remaining: {sub["interviews_remaining"]}')
        else:
            print(f'\nInterview {i+1}: ✗ BLOCKED')
            print(f'  Error Code: {error["code"]}')
            print(f'  Status: 403 Forbidden')
            print(f'  Full Error Response:')
            print(json.dumps(error, indent=2))
    
    print('\n' + '=' * 60)
    print('Test Complete')
