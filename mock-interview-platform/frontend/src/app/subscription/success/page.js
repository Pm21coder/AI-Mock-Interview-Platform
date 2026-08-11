'use client';

import { useState, useEffect } from 'react';
import Navigation from '@/components/Navigation';
import Link from 'next/link';

export default function SubscriptionSuccessPage() {
  const [sessionId, setSessionId] = useState('');
  
  if (typeof window !== 'undefined' && !sessionId) {
    const urlParams = new URLSearchParams(window.location.search);
    const session = urlParams.get('session_id');
    if (session) {
      setSessionId(session);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <main className="container mx-auto px-4 py-8">
        <div className="mx-auto max-w-2xl">
          <div className="rounded-xl bg-white p-8 shadow-lg">
            <div className="mb-6 flex items-center justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <svg
                  className="h-8 w-8 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>

            <h1 className="mb-4 text-center text-3xl font-bold text-gray-900">
              Subscription Successful!
            </h1>

            <p className="mb-8 text-center text-gray-600">
              Thank you for subscribing! Your account has been upgraded and you can now access all the features of your new plan.
            </p>

            {sessionId && (
              <div className="mb-6 rounded-lg bg-gray-50 p-4">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Session ID:</span> {sessionId}
                </p>
              </div>
            )}

            <div className="space-y-4">
              <Link
                href="/dashboard"
                className="block w-full rounded-lg bg-blue-600 py-3 px-4 text-center font-semibold text-white hover:bg-blue-700 transition-colors"
              >
                Go to Dashboard
              </Link>

              <Link
                href="/subscription"
                className="block w-full rounded-lg border border-gray-300 py-3 px-4 text-center font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                View Subscription Details
              </Link>
            </div>

            <div className="mt-8 rounded-lg bg-blue-50 p-6">
              <h3 className="mb-2 font-semibold text-blue-900">What's Next?</h3>
              <ul className="space-y-2 text-sm text-blue-800">
                <li>✓ Your subscription is now active</li>
                <li>✓ You can start using all premium features immediately</li>
                <li>✓ Check your email for a confirmation receipt</li>
                <li>✓ Manage your subscription anytime from the subscription page</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}