#!/usr/bin/env python3
"""Test that fallback feedback is now responsive to actual answers."""

from app.services.gemini_service import GeminiService

svc = GeminiService()

# Test fallback with different answer lengths
short_answer = 'I like working with people.'
long_answer = 'I genuinely enjoy collaborating with diverse team members. For example, at my previous company, I led a cross-functional team of 5 engineers and designers to ship a feature that improved user engagement by 25%. I believe that strong communication and mutual respect are key to building effective teams. Specifically, I try to ensure everyone has a voice in meetings and can contribute their perspective.'

print('Short answer feedback:')
fb1 = svc.get_fallback_feedback(user_answer=short_answer)
print(f"  overall_score: {fb1['overall_score']}")
print(f"  content_score: {fb1['content_score']}")
print(f"  word_count: {len(short_answer.split())}")
print(f"  strengths: {fb1['strengths']}")
print()

print('Long answer feedback:')
fb2 = svc.get_fallback_feedback(user_answer=long_answer)
print(f"  overall_score: {fb2['overall_score']}")
print(f"  content_score: {fb2['content_score']}")
print(f"  word_count: {len(long_answer.split())}")
print(f"  strengths: {fb2['strengths']}")
print()

print(f'✓ Scores are different: {fb1["overall_score"] != fb2["overall_score"]}')
print(f'✓ Long answer scores higher: {fb2["overall_score"] > fb1["overall_score"]}')
