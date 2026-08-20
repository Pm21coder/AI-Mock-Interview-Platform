'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Navigation from '../../components/Navigation';
import { useInterviewSync, useSubscriptionSync } from '../../hooks/useInterviewSync';
import { useSubscription } from '../../hooks/useSubscription';
import {
  createRazorpayOrder,
  verifyRazorpayPayment,
  validateCoupon,
} from '../../utils/api';

const RAZORPAY_SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';

const loadRazorpayScript = () => {
  if (typeof window === 'undefined') return Promise.resolve(false);
  if (window.Razorpay) return Promise.resolve(true);

  return new Promise((resolve, reject) => {
    let script = document.querySelector(`script[src="${RAZORPAY_SCRIPT_URL}"]`);
    const createdScript = !script;

    if (!script) {
      script = document.createElement('script');
      script.src = RAZORPAY_SCRIPT_URL;
      // Keep async but set crossorigin to reduce CSP-related issues
      script.async = true;
      script.crossOrigin = 'anonymous';
    }

    let resolved = false;

    const cleanup = () => {
      window.clearTimeout(timeoutId);
      script.removeEventListener('load', handleLoad);
      script.removeEventListener('error', handleError);
    };

    const handleLoad = () => {
      // Allow a short moment for the global to be defined
      setTimeout(() => {
        cleanup();
        if (window.Razorpay) {
          resolved = true;
          resolve(true);
        } else {
          resolved = true;
          reject(new Error('Razorpay SDK loaded but window.Razorpay is undefined. Check CSP/ad-blockers.'));
        }
      }, 200);
    };

    const handleError = () => {
      cleanup();
      resolved = true;
      reject(new Error('Failed to load Razorpay SDK (network error or blocked by extension).'));
    };

    const timeoutId = window.setTimeout(() => {
      if (!resolved) {
        cleanup();
        if (window.Razorpay) {
          resolve(true);
        } else {
          reject(new Error('Timed out loading Razorpay SDK. Possible network/CSP/adblock interference.'));
        }
      }
    }, 10000);

    script.addEventListener('load', handleLoad);
    script.addEventListener('error', handleError);

    if (createdScript) {
      document.body.appendChild(script);
    }
  });
};

const hasAuthToken = () => (
  typeof window !== 'undefined' && Boolean(window.localStorage.getItem('auth_token'))
);

export default function SubscriptionPage() {
  return (
    <Suspense fallback={<SubscriptionLoading />}>
      <SubscriptionPageContent />
    </Suspense>
  );
}

function SubscriptionLoading() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="container mx-auto px-4 py-16 text-center text-gray-600">
        Loading subscription details...
      </main>
    </div>
  );
}

function SubscriptionPageContent() {
  const router = useRouter();
  const params = useSearchParams();
  const {
    subscription,
    loading,
    error: subscriptionError,
    refetch,
  } = useSubscription();
  const [error, setError] = useState(null);
  const [upgradePrompt, setUpgradePrompt] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [processingTier, setProcessingTier] = useState(null);
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState(null);
  const [couponApplying, setCouponApplying] = useState(false);
  const [couponPreview, setCouponPreview] = useState(null);

  const refreshSubscription = useCallback(() => refetch(), [refetch]);

  useEffect(() => {
    refreshSubscription();
    // Check for upgrade prompt in URL
    const prompt = params.get('upgrade_prompt');
    if (prompt === 'limit_reached') {
      const promptTimer = window.setTimeout(() => {
        setUpgradePrompt('limit_reached');
      }, 0);
      return () => window.clearTimeout(promptTimer);
    }

    return undefined;
  }, [params, refreshSubscription]);

  // Refresh usage as soon as another page starts an interview.
  useInterviewSync(() => {
    console.log('Interview usage changed, refreshing subscription data...');
    refreshSubscription();
  });

  // Listen for subscription updates from other pages/tabs
  useSubscriptionSync(() => {
    console.log('Subscription updated, refreshing...');
    refreshSubscription();
  });

  const handleRazorpayCheckout = async (tier) => {
    if (!['basic', 'pro'].includes(tier)) {
      setError('Please select a valid paid subscription plan.');
      return;
    }

    if (!hasAuthToken()) {
      setError('Please sign in before making a payment.');
      router.push('/auth?next=/subscription');
      return;
    }

    try {
      setProcessing(true);
      setProcessingTier(tier);
      setError(null);
      const scriptLoaded = await loadRazorpayScript();

      if (!scriptLoaded || !window.Razorpay) {
        console.error('Razorpay SDK not available. Payment cannot proceed.');
        setError('Payment service is currently unavailable. Please try again later or contact support.');
        setProcessing(false);
        setProcessingTier(null);
        return;
      }

      let orderData;
      try {
        orderData = await createRazorpayOrder({ tier, coupon_code: couponCode ? couponCode.trim() : undefined });
      } catch (orderError) {
        // If order creation fails with 400 (missing credentials), surface a clear error
        if (orderError.status === 400 && orderError.message?.toLowerCase?.().includes('not configured')) {
          console.error('Razorpay credentials not configured on server.');
          setError('Payment gateway is not configured. Please contact support.');
          setProcessing(false);
          setProcessingTier(null);
          return;
        }

        // Coupon validation error - show inline message and stop processing
        if (orderError.status === 400 && orderError.message?.toLowerCase?.().includes('coupon')) {
          setCouponMessage(orderError.message || 'Invalid or expired coupon code');
          setProcessing(false);
          setProcessingTier(null);
          return;
        }

        throw orderError;
      }

      const key = orderData.key_id || process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID;

      if (!orderData.order_id || !key) {
        throw new Error(orderData.error || 'Unable to initialize Razorpay checkout');
      }

      const authEmail = window.localStorage.getItem('auth_email') || '';

      const razorpay = new window.Razorpay({
        key,
        order_id: orderData.order_id,
        currency: orderData.currency || 'INR',
        amount: orderData.amount,
        name: 'MockInterview AI',
        description: `${tier === 'basic' ? 'Basic' : 'Pro'} plan subscription`,
        prefill: {
          email: authEmail,
        },
        notes: {
          subscription_tier: tier,
        },
        handler: async (response) => {
          try {
            const result = await verifyRazorpayPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            if (result.status !== 'success') {
              throw new Error(result.error || 'Payment verification failed');
            }
            await refreshSubscription();
            alert('Payment verified successfully! Your subscription is now active.');
          } catch (err) {
            setError(err.response?.data?.error || err.message || 'Payment verification failed');
          } finally {
            setProcessing(false);
            setProcessingTier(null);
          }
        },
        modal: {
          ondismiss: () => {
            setProcessing(false);
            setProcessingTier(null);
            setError('Payment was cancelled.');
          },
        },
        theme: {
          color: '#2563eb',
        },
      });
      razorpay.on('payment.failed', (response) => {
        setProcessing(false);
        setProcessingTier(null);
        setError(response.error?.description || 'Payment failed. Please try again.');
      });
      razorpay.open();
    } catch (err) {
      setProcessing(false);
      setProcessingTier(null);

      const serverMsg = err.response?.data?.error || err.message || '';
      const status = err.response?.status ?? err.status;
      const isAuthError = status === 401 && (
        serverMsg.toLowerCase().includes('token') ||
        serverMsg.toLowerCase().includes('expired') ||
        serverMsg.toLowerCase().includes('user not found') ||
        serverMsg.toLowerCase().includes('sign in with an account')
      );

      if (isAuthError) {
        window.localStorage.removeItem('auth_token');
        window.localStorage.removeItem('auth_email');
        setError('Your session expired. Please sign in again before making a payment.');
        router.push('/auth?next=/subscription');
        return;
      }

      setError(serverMsg || 'Failed to initiate Razorpay payment');
    }
  };


  const plans = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      priceInr: '₹0',
      interval: 'forever',
      interviews: 3,
      features: [
        '3 mock interviews per month',
        'Basic AI feedback',
        'Standard question categories',
        '7-day feedback history',
      ],
      cta: subscription?.tier === 'free' ? 'Current Plan' : 'Downgrade',
      disabled: true,
    },
    {
      id: 'basic',
      name: 'Basic',
      price: 5,
      priceInr: '₹375',
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
      price: 10,
      priceInr: '₹750',
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

  // Initialize Razorpay script
  useEffect(() => {
    loadRazorpayScript();
  }, []);

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

        {/* Upgrade Prompt Alert */}
        {upgradePrompt === 'limit_reached' && (
          <div className="mb-8 rounded-lg border border-orange-200 bg-orange-50 p-6">
            <div className="flex items-start gap-4">
              <div className="text-3xl">📊</div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-orange-900">Monthly Interview Limit Reached</h3>
                <p className="mt-2 text-sm text-orange-700">
                  You&apos;ve used all your monthly interviews on the Free plan. Upgrade your plan to continue practicing and unlock premium features like video analysis and all question categories.
                </p>
                <button
                  onClick={() => setUpgradePrompt(null)}
                  className="mt-3 text-sm font-medium text-orange-600 hover:text-orange-700 underline"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Current Subscription Status */}
        {subscription && (
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
        {(error || subscriptionError) && (
          <div className="mb-8 rounded-lg bg-red-50 p-4 text-red-700">
            {error || subscriptionError}
          </div>
        )}

        {/* Coupon input */}
          <div className="mb-6 flex items-center justify-center">
         <div className="w-full max-w-2xl">
           <label className="mb-2 block text-sm font-medium text-gray-700">Have a coupon code?</label>
           <div className="flex gap-2">
             <input
               type="text"
               value={couponCode}
               onChange={(e) => { setCouponCode(e.target.value); setCouponMessage(null); }}
               placeholder="Enter coupon code"
               className="w-full rounded-lg border px-4 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
             />
             <button
               onClick={async () => {
                 try {
                   setCouponApplying(true);
                   setCouponMessage(null);
                   setCouponPreview(null);
                   const resp = await validateCoupon(couponCode.trim());
                   if (resp && resp.coupon) {
                     setCouponPreview(resp.coupon);
                     setCouponMessage(`Coupon applied: ${resp.coupon.discount_percent}% off`);
                   } else {
                     setCouponMessage('Coupon looks invalid');
                   }
                 } catch (err) {
                   setCouponMessage(err.message || 'Invalid or expired coupon code');
                   setCouponPreview(null);
                 } finally {
                   setCouponApplying(false);
                 }
               }}
               className={`rounded-lg px-4 py-2 font-medium ${couponApplying ? 'bg-gray-300' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
               disabled={couponApplying || !couponCode.trim()}
             >
               {couponApplying ? 'Checking...' : 'Apply'}
             </button>
           </div>
           {couponMessage && (
             <div className="mt-2 text-sm text-gray-700">{couponMessage}</div>
           )}
         </div>
          </div>

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
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold text-gray-900">{plan.priceInr}</span>
                  <span className="text-lg text-gray-600">/ {plan.interval}</span>
                </div>
                {couponPreview && couponPreview.discount_percent && plan.id !== 'free' && (
                  <div className="mt-2 text-sm text-green-700">
                    {couponPreview.discount_percent}% off applied • Approx. price: {
                      (() => {
                        try {
                          const digits = plan.priceInr.replace(/[^0-9.]/g, '');
                          const base = parseFloat(digits) || 0;
                          const discounted = Math.max(1, Math.round(base * (100 - couponPreview.discount_percent) / 100));
                          return `₹${discounted}`;
                        } catch (e) {
                          return '';
                        }
                      })()
                    }
                  </div>
                )}
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
                  onClick={() => handleRazorpayCheckout(plan.id)}
                  disabled={plan.disabled || processing}
                  className={`w-full rounded-lg py-3 px-4 font-semibold transition-colors ${
                    plan.disabled
                      ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                      : plan.popular
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                >
                  {processing && processingTier === plan.id
                    ? 'Processing...'
                    : plan.cta}
                </button>
              </div>
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
                Yes, you can cancel your subscription at any time. You will continue to have access until the end of your billing period.
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
