export function canStartInterview(subscription = {}) {
  const tier = subscription.tier || 'free';
  const monthlyLimit = subscription.monthly_limit;
  const interviewsRemaining = subscription.interviews_remaining;

  if (monthlyLimit === 'unlimited' || monthlyLimit === Infinity) {
    return { allowed: true, reason: null };
  }

  const remaining = Number(interviewsRemaining ?? monthlyLimit ?? 0);
  if (Number.isFinite(remaining) && remaining <= 0) {
    return {
      allowed: false,
      reason: 'limit_reached',
      message: `You have used all ${monthlyLimit} interviews for this month. Please upgrade your plan to continue.`,
      requiredTier: tier === 'free' ? 'basic' : 'pro',
    };
  }

  return { allowed: true, reason: null };
}
