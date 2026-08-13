import Link from 'next/link';
import { useState, useEffect } from 'react';

export default function SubscriptionUsageAlert({ subscription }) {
  const [isVisible, setIsVisible] = useState(true);

  if (!subscription || !isVisible) return null;

  const { tier, interviews_remaining, monthly_limit, is_trial } = subscription;

  // Don't show alerts for free tier or when unlimited
  if (tier === 'free' || monthly_limit === 'unlimited') {
    return null;
  }

  // Check if approaching limit (2 or fewer remaining)
  if (interviews_remaining > 2) {
    return null;
  }

  const getAlertType = () => {
    if (interviews_remaining === 0) return 'error';
    return 'warning';
  };

  const getAlertMessage = () => {
    if (interviews_remaining === 0) {
      return `You've reached your monthly interview limit of ${monthly_limit}. Upgrade your plan to continue.`;
    }
    return `You have ${interviews_remaining} interview${interviews_remaining === 1 ? '' : 's'} remaining this month. ${
      tier === 'basic' ? 'Upgrade to Pro for unlimited interviews.' : ''
    }`;
  };

  const alertType = getAlertType();
  const message = getAlertMessage();

  const bgColor = alertType === 'error' ? 'bg-red-50' : 'bg-yellow-50';
  const borderColor = alertType === 'error' ? 'border-red-200' : 'border-yellow-200';
  const textColor = alertType === 'error' ? 'text-red-800' : 'text-yellow-800';
  const iconColor = alertType === 'error' ? 'text-red-500' : 'text-yellow-500';

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-4`}>
      <div className="flex items-start gap-3">
        <svg
          className={`mt-0.5 h-5 w-5 shrink-0 ${iconColor}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          {alertType === 'error' ? (
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          ) : (
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          )}
        </svg>

        <div className="flex-1">
          <p className={`font-semibold ${textColor}`}>{message}</p>
          {interviews_remaining === 0 && (
            <Link
              href="/subscription"
              className="mt-2 inline-block font-semibold text-blue-600 hover:text-blue-700"
            >
              Upgrade Now →
            </Link>
          )}
        </div>

        <button
          onClick={() => setIsVisible(false)}
          className={`shrink-0 ${textColor} hover:opacity-70`}
        >
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {is_trial && (
        <p className={`mt-3 text-sm ${textColor}`}>
          💡 Tip: This is a trial subscription. Consider upgrading to a paid plan to get continuous access.
        </p>
      )}
    </div>
  );
}
