'use client';

import Link from 'next/link';
import { useState } from 'react';

/**
 * Enhanced error modal for limit and restriction errors.
 * Provides clear messaging and upgrade CTAs.
 */
export default function LimitErrorModal({
  isOpen,
  error,
  errorCode,
  onDismiss,
  onUpgrade,
  onRetry,
}) {
  const [isClosing, setIsClosing] = useState(false);

  if (!isOpen || !error) return null;

  const isLimitError = errorCode === 'interview_limit_reached';
  const isCategoryError = errorCode === 'category_not_in_plan';

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onDismiss?.();
      setIsClosing(false);
    }, 150);
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 transition-opacity duration-150 ${isClosing ? 'opacity-0' : 'opacity-100'}`}>
      <div className={`w-full max-w-md rounded-2xl bg-white shadow-2xl transition-all duration-150 ${isClosing ? 'scale-95' : 'scale-100'}`}>
        {/* Header */}
        <div className={`border-b px-6 py-5 ${isLimitError ? 'bg-red-50 border-red-100' : 'bg-orange-50 border-orange-100'}`}>
          <div className="flex items-start gap-3">
            <div className={`text-2xl ${isLimitError ? 'text-red-600' : 'text-orange-600'}`}>
              {isLimitError ? '📊' : '🔒'}
            </div>
            <div className="flex-1">
              <h3 className={`text-lg font-bold ${isLimitError ? 'text-red-900' : 'text-orange-900'}`}>
                {isLimitError ? 'Interview Limit Reached' : 'Feature Unavailable'}
              </h3>
              <p className={`text-sm mt-1 ${isLimitError ? 'text-red-700' : 'text-orange-700'}`}>
                {isLimitError
                  ? "You've used all your monthly interviews"
                  : 'This feature is only available on paid plans'}
              </p>
            </div>
            <button
              onClick={handleClose}
              className={`text-xl hover:opacity-70 transition ${isLimitError ? 'text-red-400' : 'text-orange-400'}`}
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5">
          <div className={`mb-5 rounded-lg p-4 ${isLimitError ? 'bg-red-50 border border-red-100' : 'bg-orange-50 border border-orange-100'}`}>
            <p className={`text-sm leading-relaxed ${isLimitError ? 'text-red-900' : 'text-orange-900'}`}>
              {error}
            </p>
          </div>

          {/* Plan comparison info */}
          <div className="mb-5 space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Available Plans</p>
            <div className="grid gap-2">
              <div className="flex items-center gap-2 rounded-lg bg-gray-50 p-3">
                <span className="text-lg">🆓</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900">Free</p>
                  <p className="text-xs text-gray-600">3 interviews/month</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-blue-50 p-3 border border-blue-100">
                <span className="text-lg">⭐</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-blue-900">Basic</p>
                  <p className="text-xs text-blue-700">15 interviews/month</p>
                </div>
                {!isLimitError && (
                  <span className="text-xs font-bold text-blue-600">RECOMMENDED</span>
                )}
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-purple-50 p-3 border border-purple-100">
                <span className="text-lg">👑</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-purple-900">Pro</p>
                  <p className="text-xs text-purple-700">Unlimited interviews</p>
                </div>
              </div>
            </div>
          </div>

          {/* Benefits */}
          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Unlock with upgrade</p>
            <ul className="space-y-1 text-sm text-gray-700">
              <li className="flex items-center gap-2">
                <span className="text-green-600">✓</span>
                More monthly interviews
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">✓</span>
                All question categories
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">✓</span>
                Advanced video analysis
              </li>
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 border-t border-gray-100 bg-gray-50 px-6 py-4">
          <button
            onClick={handleClose}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 font-medium text-gray-700 hover:bg-gray-100 transition"
          >
            Back
          </button>
          <Link
            href="/subscription"
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 font-semibold text-white text-center hover:bg-blue-700 transition"
          >
            View Plans
          </Link>
        </div>
      </div>
    </div>
  );
}
