import test from 'node:test';
import assert from 'node:assert/strict';
import { canStartInterview } from './interviewQuota.mjs';

test('blocks interview start when quota is exhausted', () => {
  const result = canStartInterview({ tier: 'free', monthly_limit: 3, interviews_remaining: 0 });
  assert.equal(result.allowed, false);
  assert.equal(result.reason, 'limit_reached');
});

test('allows interview start when the plan still has interviews left', () => {
  const result = canStartInterview({ tier: 'free', monthly_limit: 3, interviews_remaining: 2 });
  assert.equal(result.allowed, true);
  assert.equal(result.reason, null);
});
