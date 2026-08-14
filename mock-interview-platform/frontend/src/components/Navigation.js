'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';
import { useSyncExternalStore } from 'react';
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

const navigationLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/interview/setup', label: 'New Interview' },
  { href: '/resume', label: 'Resume Analyzer' },
  { href: '/subscription', label: 'Pricing' },
];

export default function Navigation() {
  const router = useRouter();
  const email = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, getServerAuthEmail);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const signOut = useCallback(() => {
    window.localStorage.removeItem('auth_token');
    window.localStorage.removeItem('auth_email');
    window.dispatchEvent(new Event('auth-change'));
    setIsMenuOpen(false);
    router.push('/');
  }, [router]);

  const closeMenu = useCallback(() => {
    setIsMenuOpen(false);
  }, []);

  return (
    <nav className="sticky top-0 z-50 w-full bg-white shadow-sm">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between sm:h-20">
          {/* Logo */}
          <Link
            href="/"
            className="flex-shrink-0 text-xl font-bold text-blue-600 hover:text-blue-700 transition-colors sm:text-2xl"
            onClick={closeMenu}
          >
            MockInterview<span className="hidden sm:inline"> AI</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1 lg:gap-2">
            {navigationLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors lg:px-4 lg:py-2"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Auth Buttons - Desktop */}
          <div className="hidden md:flex items-center gap-3">
            {email ? (
              <>
                <span className="text-sm text-gray-600 px-3 py-2 rounded-md">
                  {email}
                </span>
                <button
                  onClick={signOut}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/auth"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                Sign in
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden inline-flex items-center justify-center p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            aria-expanded={isMenuOpen}
            aria-label="Toggle navigation menu"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={
                  isMenuOpen
                    ? 'M6 18L18 6M6 6l12 12'
                    : 'M4 6h16M4 12h16M4 18h16'
                }
              />
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-gray-200">
            <div className="space-y-1 px-2 py-3">
              {navigationLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="block px-3 py-2 rounded-md text-base font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors"
                  onClick={closeMenu}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            {/* Mobile Auth Section */}
            <div className="border-t border-gray-200 px-2 py-3 space-y-2">
              {email ? (
                <>
                  <p className="text-sm text-gray-600 px-3 py-2">
                    {email}
                  </p>
                  <button
                    onClick={signOut}
                    className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <Link
                  href="/auth"
                  className="block w-full text-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                  onClick={closeMenu}
                >
                  Sign in
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
