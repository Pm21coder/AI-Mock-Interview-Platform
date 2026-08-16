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
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 backdrop-blur-sm transition-opacity duration-150 ${isClosing ? 'opacity-0' : 'opacity-100'}`}>
      <div className={`w-full max-w-lg overflow-hidden rounded-2xl border bg-white shadow-[0_25px_80px_rgba(15,23,42,0.22)] transition-all duration-150 ${isClosing ? 'scale-95 opacity-90' : 'scale-100 opacity-100'}`}>
        {/* Header */}
        <div className={`border-b px-6 py-5 ${isLimitError ? 'border-red-100 bg-gradient-to-r from-red-50 to-rose-50' : 'border-orange-100 bg-gradient-to-r from-orange-50 to-amber-50'}`}>
          <div className="flex items-start gap-3">
            <div className={`flex h-11 w-11 items-center justify-center rounded-xl text-2xl shadow-sm ${isLimitError ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'}`}>
              {isLimitError ? '📊' : '🔒'}
            </div>
            <div className="flex-1">
              <h3 className={`text-lg font-bold ${isLimitError ? 'text-red-900' : 'text-orange-900'}`}>
                {isLimitError ? 'Interview Limit Reached' : 'Feature Unavailable'}
              </h3>
              <p className={`mt-1 text-sm ${isLimitError ? 'text-red-700' : 'text-orange-700'}`}>
                {isLimitError
                  ? "You've used all your monthly interviews"
                  : 'This feature is only available on paid plans'}
              </p>
            </div>
            <button
              onClick={handleClose}
              className={`flex h-8 w-8 items-center justify-center rounded-full text-lg transition hover:opacity-80 ${isLimitError ? 'bg-red-100 text-red-500' : 'bg-orange-100 text-orange-500'}`}
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5">
          <div className={`mb-5 rounded-xl border p-4 ${isLimitError ? 'border-red-100 bg-red-50' : 'border-orange-100 bg-orange-50'}`}>
            <p className={`text-sm leading-relaxed ${isLimitError ? 'text-red-900' : 'text-orange-900'}`}>
              {error}
            </p>
          </div>

          {/* Plan comparison info */}
          <div className="mb-5 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Available Plans</p>
            <div className="grid gap-2">
              <div className="flex items-center gap-2 rounded-xl bg-gray-50 p-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-lg shadow-sm">🆓</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900">Free</p>
                  <p className="text-xs text-gray-600">3 interviews/month</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-xl border border-blue-100 bg-blue-50 p-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-lg shadow-sm">⭐</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-blue-900">Basic</p>
                  <p className="text-xs text-blue-700">15 interviews/month</p>
                </div>
                {!isLimitError && (
                  <span className="rounded-full bg-blue-600 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-white">Recommended</span>
                )}
              </div>
              <div className="flex items-center gap-2 rounded-xl border border-purple-100 bg-purple-50 p-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-lg shadow-sm">👑</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-purple-900">Pro</p>
                  <p className="text-xs text-purple-700">Unlimited interviews</p>
                </div>
              </div>
            </div>
          </div>

          {/* Benefits */}
          <div className="mb-6">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Unlock with upgrade</p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-600">✓</span>
                More monthly interviews
              </li>
              <li className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-600">✓</span>
                All question categories
              </li>
              <li className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-600">✓</span>
                Advanced video analysis
              </li>
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 border-t border-gray-100 bg-slate-50 px-6 py-4">
          <button
            onClick={handleClose}
            className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2.5 font-medium text-gray-700 transition hover:bg-gray-100"
          >
            Back
          </button>
          <Link
            href="/subscription"
            className="flex-1 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-center font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:brightness-110"
          >
            View Plans
          </Link>
        </div>
      </div>
    </div>
  );
}
