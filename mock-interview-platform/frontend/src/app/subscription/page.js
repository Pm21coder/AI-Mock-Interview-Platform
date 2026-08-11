'use client';

import { useState, useEffect } from 'react';
import Navigation from '@/components/Navigation';
import { getSubscriptionStatus, createCheckoutSession } from '@/utils/api';

const fetchSubscriptionStatus = async (setSubscription, setLoading, setError) => {
  try {
    setLoading(true);
    const data = await getSubscriptionStatus();
    if (data.error) {
      setError('Failed to load subscription data');
    } else {
      setSubscription(data);
    }
  } catch (err) {
    setError('Failed to load subscription data');
  } finally {
    setLoading(false);
  }
};

export default function SubscriptionPage() {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchSubscriptionStatus(setSubscription, setLoading, setError);
  }, [setSubscription, setLoading, setError]);

  const handleSubscribe = async (tier) => {
    try {
      setProcessing(true);
      const data = await createCheckoutSession({ tier });
      if (data.url) {
        window.location.assign(data.url);
      } else {
        setError('Failed to create checkout session');
      }
    } catch (err) {
      setError('Failed to initiate subscription');
    } finally {
      setProcessing(false);
    }
  };

  const plans = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      interval: 'forever',
      interviews: 3,
      features: [
        '3 mock interviews per month',
        'Basic AI feedback',
        'Standard question categories',
        '7-day feedback history',
      ],
      cta: subscription?.tier === 'free' ? 'Current Plan' : 'Downgrade',
      disabled: subscription?.tier === 'free',
    },
    {
      id: 'basic',
      name: 'Basic',
      price: 9,
      interval: 'month',
      interviews: 15,
      features: [
        '15 mock interviews per month',
        'Advanced AI feedback',
        'All question categories',
        'Unlimited feedback history',
        'Video recording analysis',
        'Email support',
      ],
      cta: subscription?.tier === 'basic' ? 'Current Plan' : 'Upgrade to Basic',
      disabled: subscription?.tier === 'basic',
      popular: true,
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 19,
      interval: 'month',
      interviews: 'Unlimited',
      features: [
        'Unlimited mock interviews',
        'Premium AI coaching',
        'Custom interview scenarios',
        'Advanced analytics dashboard',
        'Priority support',
        'Resume review integration',
      ],
      cta: subscription?.tier === 'pro' ? 'Current Plan' : 'Upgrade to Pro',
      disabled: subscription?.tier === 'pro',
    },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center space-x-3 text-gray-600">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
              <span>Loading subscription details...</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold text-gray-900">Choose Your Plan</h1>
          <p className="text-lg text-gray-600">
            Start free and upgrade as you grow. All plans include a 7-day money-back guarantee.
          </p>
        </div>

        {/* Current Subscription Status */}
        {subscription && subscription.tier !== 'free' && (
          <div className="mb-8 rounded-lg bg-blue-50 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-blue-900">Current Plan: {subscription.tier.toUpperCase()}</h3>
                <p className="text-sm text-blue-700">
                  Status: {subscription.status} | Interviews used this month: {subscription.interviews_used_this_month}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-blue-600">
                  {subscription.interviews_remaining === 'unlimited' 
                    ? 'Unlimited interviews remaining' 
                    : `${subscription.interviews_remaining} interviews remaining`}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-8 rounded-lg bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Pricing Cards */}
        <div className="grid gap-8 lg:grid-cols-3">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl bg-white p-8 shadow-lg ${
                plan.popular ? 'ring-2 ring-blue-600' : ''
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-blue-600 px-4 py-1 text-sm font-semibold text-white">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h3 className="mb-2 text-2xl font-bold text-gray-900">{plan.name}</h3>
                <div className="flex items-baseline">
                  <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
                  <span className="ml-2 text-gray-600">/{plan.interval}</span>
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  {plan.interviews === 'Unlimited' 
                    ? 'Unlimited interviews' 
                    : `${plan.interviews} interviews per month`}
                </p>
              </div>

              <ul className="mb-8 space-y-3">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <svg
                      className="mr-2 h-5 w-5 shrink-0 text-green-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="text-sm text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={plan.disabled || processing}
                className={`w-full rounded-lg py-3 px-4 font-semibold transition-colors ${
                  plan.disabled
                    ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                    : plan.popular
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-900 text-white hover:bg-gray-800'
                }`}
              >
                {processing && plan.id === subscription?.tier ? 'Processing...' : plan.cta}
              </button>
            </div>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-16 rounded-xl bg-white p-8 shadow-lg">
          <h2 className="mb-6 text-2xl font-bold text-gray-900">Frequently Asked Questions</h2>
          <div className="space-y-6">
            <div>
              <h3 className="mb-2 font-semibold text-gray-900">Can I cancel anytime?</h3>
              <p className="text-gray-600">
                Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your billing period.
              </p>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-gray-900">What happens when I reach my interview limit?</h3>
              <p className="text-gray-600">
                You can upgrade your plan or wait until the next billing cycle when your interview count resets.
              </p>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-gray-900">Do you offer refunds?</h3>
              <p className="text-gray-600">
                Yes, we offer a 7-day money-back guarantee for all paid plans. No questions asked.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}