'use client';

import Link from 'next/link';
import { useSyncExternalStore, useCallback } from 'react';
import { useRouter } from 'next/navigation';

// Custom store that tracks auth state changes both across tabs (via the
// 'storage' event) and within the same tab (via a custom 'auth-change' event).
const authStore = {
  getSnapshot: () => window.localStorage.getItem('auth_email') || '',
  subscribe: (callback) => {
    window.addEventListener('storage', callback);
    window.addEventListener('auth-change', callback);
    return () => {
      window.removeEventListener('storage', callback);
      window.removeEventListener('auth-change', callback);
    };
  },
};

const getServerAuthEmail = () => '';

export default function Navigation() {
  const router = useRouter();
  const email = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, getServerAuthEmail);

  const signOut = () => {
    window.localStorage.removeItem('auth_token');
    window.localStorage.removeItem('auth_email');
    window.dispatchEvent(new Event('auth-change'));
    router.push('/');
  };

  return (
    <nav className="bg-white shadow-sm">
      <div className="container mx-auto flex items-center justify-between px-4 py-3">
        <Link href="/" className="text-xl font-bold text-blue-600">
          MockInterview AI
        </Link>

        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
            Dashboard
          </Link>
          <Link href="/interview/setup" className="text-gray-600 hover:text-gray-900">
            New Interview
          </Link>
          <Link href="/resume" className="text-gray-600 hover:text-gray-900">
            Resume Analyzer
          </Link>
          <Link href="/subscription" className="text-gray-600 hover:text-gray-900">
            Pricing
          </Link>
          {email ? (
            <button onClick={signOut} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              Sign out
            </button>
          ) : (
            <Link href="/auth" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
