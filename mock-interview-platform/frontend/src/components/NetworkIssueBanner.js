'use client';

import { useEffect, useState } from 'react';

const STORAGE_KEY = 'last_network_issue';
const DISMISS_KEY = 'network_issue_dismissed_at';

function readLastIssue() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

export default function NetworkIssueBanner() {
  const [visible, setVisible] = useState(false);
  const [issue, setIssue] = useState(null);

  useEffect(() => {
    function evaluate() {
      const last = readLastIssue();
      if (!last) {
        setVisible(false);
        setIssue(null);
        return;
      }
      try {
        const dismissedAt = Number(window.localStorage.getItem(DISMISS_KEY)) || 0;
        // Auto-hide if user dismissed within last 5 minutes
        if (dismissedAt && Date.now() - dismissedAt < 1000 * 60 * 5) {
          setVisible(false);
          setIssue(null);
          return;
        }
      } catch (e) {}
      setIssue(last);
      setVisible(true);
    }

    evaluate();

    function onNetworkEvent(e) {
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(e.detail));
      } catch (err) {}
      evaluate();
    }

    window.addEventListener('app:network-issue', onNetworkEvent);
    // Also listen for storage events (cross-tab updates)
    function onStorage(e) {
      if (e.key === STORAGE_KEY || e.key === DISMISS_KEY) evaluate();
    }
    window.addEventListener('storage', onStorage);

    return () => {
      window.removeEventListener('app:network-issue', onNetworkEvent);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  if (!visible || !issue) return null;

  const handleDismiss = () => {
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch (e) {}
    setVisible(false);
  };

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex justify-center">
      <div className="mx-4 mt-4 max-w-3xl rounded-lg border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-800 shadow-lg dark:bg-yellow-900/80 dark:text-yellow-100">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <strong>Connection issue</strong>
            <div className="mt-1">The application had trouble contacting the backend. Some features may be unavailable.</div>
            <div className="mt-2 text-xs opacity-80">Last check: {new Date(issue.ts).toLocaleString()}</div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.location.reload()}
              className="rounded-md bg-yellow-600 px-3 py-1 text-xs font-semibold text-white hover:bg-yellow-700"
            >
              Reload
            </button>
            <button
              onClick={handleDismiss}
              className="rounded-md border border-yellow-300 bg-transparent px-2 py-1 text-xs font-medium text-yellow-800 hover:bg-yellow-100 dark:border-yellow-700 dark:text-yellow-100"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
