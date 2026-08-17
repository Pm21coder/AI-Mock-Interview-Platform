'use client';

import Link from 'next/link';
import { useSyncExternalStore } from 'react';

const COOKIE_CONSENT_EVENT = 'cookie-consent-change';

function subscribeToCookieConsent(callback) {
  window.addEventListener('storage', callback);
  window.addEventListener(COOKIE_CONSENT_EVENT, callback);

  return () => {
    window.removeEventListener('storage', callback);
    window.removeEventListener(COOKIE_CONSENT_EVENT, callback);
  };
}

function getCookieConsent() {
  return window.localStorage.getItem('cookie-consent');
}

function getServerCookieConsent() {
  return 'unknown';
}

export default function CookieBanner() {
  const cookieConsent = useSyncExternalStore(
    subscribeToCookieConsent,
    getCookieConsent,
    getServerCookieConsent,
  );

  const setCookieConsent = (value) => {
    window.localStorage.setItem('cookie-consent', value);
    window.dispatchEvent(new Event(COOKIE_CONSENT_EVENT));
  };

  const handleAccept = () => {
    setCookieConsent('accepted');
    // Load analytics and tracking scripts
    loadAnalyticsScripts();
  };

  const handleDecline = () => {
    setCookieConsent('declined');
  };

  const loadAnalyticsScripts = () => {
    // Google Analytics is already loaded via Next.js third-party, so this is just a placeholder
    console.log('Analytics tracking enabled');
  };

  if (cookieConsent) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur-sm dark:border-slate-700 dark:bg-slate-900/95 sm:p-6">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-4 sm:items-center sm:justify-between sm:gap-6">
          <div className="flex-1">
            <p className="text-sm text-slate-700 dark:text-slate-300">
              We use cookies to improve your experience, remember preferences, and analyze site usage.
              <Link
                href="/privacy"
                className="ml-2 font-semibold text-blue-600 underline hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
              >
                Learn more
              </Link>
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
            <button
              onClick={handleDecline}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-all hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Decline
            </button>
            <button
              onClick={handleAccept}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
            >
              Accept
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
