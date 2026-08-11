'use client';

import { useState, useEffect } from 'react';
import Navigation from '@/components/Navigation';
import { getSubscriptionStatus, createCheckoutSession, getUpiInfo, createUpiPayment } from '@/utils/api';

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
  const [showUpiModal, setShowUpiModal] = useState(false);
  const [selectedTier, setSelectedTier] = useState(null);
  const [upiInfo, setUpiInfo] = useState(null);
  const [transactionId, setTransactionId] = useState('');
  const [upiProcessing, setUpiProcessing] = useState(false);

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

  const handleUpiPayment = async (tier) => {
    setSelectedTier(tier);
    setShowUpiModal(true);
    // Fetch UPI info
    try {
      const data = await getUpiInfo();
      setUpiInfo(data);
    } catch (err) {
      setError('Failed to load UPI information');
    }
  };

  const submitUpiPayment = async () => {
    if (!transactionId.trim()) {
      setError('Please enter transaction ID');
      return;
    }

    try {
      setUpiProcessing(true);
      const data = await createUpiPayment({
        tier: selectedTier,
        transaction_id: transactionId
      });
      
      if (data.message) {
        alert('Payment request submitted! Your subscription will be activated within 24 hours after verification.');
        setShowUpiModal(false);
        setTransactionId('');
        setSelectedTier(null);
      }
    } catch (err) {
      setError('Failed to submit payment request');
    } finally {
      setUpiProcessing(false);
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Navigation />
      
      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold text-gray-900 md:text-5xl">
            Choose Your Plan
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-gray-600">
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

              <div className="space-y-2">
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
                
                {!plan.disabled && plan.id !== 'free' && (
                  <button
                    onClick={() => handleUpiPayment(plan.id)}
                    className="w-full rounded-lg border-2 border-blue-600 py-3 px-4 font-semibold text-blue-600 hover:bg-blue-50 transition-colors"
                  >
                    Pay with UPI
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* UPI Payment Modal */}
        {showUpiModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
            <div className="max-w-md rounded-xl bg-white p-8 shadow-2xl">
              <div className="mb-6 flex items-center justify-between">
                <h3 className="text-2xl font-bold text-gray-900">Pay with UPI</h3>
                <button
                  onClick={() => setShowUpiModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {upiInfo && (
                <>
                  <div className="mb-6 rounded-lg bg-blue-50 p-4">
                    <p className="text-sm font-semibold text-blue-900">Selected Plan: {upiInfo.plans[selectedTier]?.name}</p>
                    <p className="text-lg font-bold text-blue-700">{upiInfo.plans[selectedTier]?.upi_amount}</p>
                  </div>

                  <div className="mb-6">
                    <p className="mb-2 text-sm font-medium text-gray-700">Scan QR Code or use UPI ID:</p>
                    <div className="rounded-lg bg-gray-50 p-4 text-center">
                      <p className="text-lg font-mono font-semibold text-gray-900">{upiInfo.upi_id}</p>
                      <p className="text-sm text-gray-600">{upiInfo.upi_name}</p>
                    </div>
                  </div>

                  <div className="mb-6 rounded-lg bg-yellow-50 border border-yellow-200 p-4">
                    <p className="text-sm text-yellow-800">
                      <strong>Instructions:</strong>
                    </p>
                    <ol className="mt-2 list-inside list-decimal text-sm text-yellow-700">
                      <li>Open any UPI app (Paytm, GPay, PhonePe, etc.)</li>
                      <li>Scan QR code or enter UPI ID: {upiInfo.upi_id}</li>
                      <li>Pay amount: {upiInfo.plans[selectedTier]?.upi_amount}</li>
                      <li>Copy the transaction ID from your payment app</li>
                      <li>Paste it below and submit</li>
                    </ol>
                  </div>

                  <div className="mb-6">
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Transaction ID <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={transactionId}
                      onChange={(e) => setTransactionId(e.target.value)}
                      placeholder="Enter your UPI transaction ID"
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
                      required
                    />
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowUpiModal(false)}
                      className="flex-1 rounded-lg border border-gray-300 py-3 px-4 font-semibold text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={submitUpiPayment}
                      disabled={upiProcessing}
                      className="flex-1 rounded-lg bg-blue-600 py-3 px-4 font-semibold text-white hover:bg-blue-700 disabled:bg-blue-400"
                    >
                      {upiProcessing ? 'Submitting...' : 'Submit Payment'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

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
