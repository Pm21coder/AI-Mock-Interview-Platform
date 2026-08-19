'use client';

import Link from 'next/link';
import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../hooks/useAuth';
import { disconnectSocket } from '../utils/socket';

const navigationLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/interview/setup', label: 'New Interview' },
  { href: '/resume', label: 'Resume Analyzer' },
  { href: '/subscription', label: 'Pricing' },
  { href: '/contact', label: 'Contact' },
];

const themeOptions = [
  { key: 'light', label: 'Light' },
  { key: 'dark', label: 'Dark' },
  { key: 'gradient-pink', label: 'Gradient Pink' },
];

export default function Navigation() {
  const router = useRouter();
  const { email, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const updateTheme = () => {
      const savedTheme = window.localStorage.getItem('theme-preference') || 'light';
      const nextTheme = themeOptions.some((option) => option.key === savedTheme) ? savedTheme : 'light';
      setTheme(nextTheme);
      document.documentElement.setAttribute('data-theme', nextTheme);
      document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    };

    updateTheme();
    window.addEventListener('storage', updateTheme);
    window.addEventListener('theme-preference-changed', updateTheme);

    return () => {
      window.removeEventListener('storage', updateTheme);
      window.removeEventListener('theme-preference-changed', updateTheme);
    };
  }, []);

  const applyTheme = useCallback((nextTheme) => {
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    window.localStorage.setItem('theme-preference', nextTheme);
    window.dispatchEvent(new CustomEvent('theme-preference-changed'));
    setIsSettingsOpen(false);
  }, []);

  const signOut = useCallback(() => {
    disconnectSocket();
    logout();
    setIsMenuOpen(false);
    router.push('/');
  }, [router, logout]);

  const closeMenu = useCallback(() => {
    setIsMenuOpen(false);
  }, []);

  const isDarkTheme = theme === 'dark' || theme === 'midnight';

  const navClass = isDarkTheme
    ? 'sticky top-0 z-50 w-full border-b border-white/10 bg-slate-950/80 text-white shadow-lg shadow-slate-950/30 backdrop-blur-xl'
    : 'sticky top-0 z-50 w-full border-b border-slate-200 bg-white/80 text-slate-900 shadow-sm backdrop-blur-xl';

  const linkClass = isDarkTheme
    ? 'rounded-md px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-white/5 hover:text-white lg:px-4 lg:py-2'
    : 'rounded-md px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900 lg:px-4 lg:py-2';

  const buttonBase = isDarkTheme
    ? 'rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition hover:brightness-110'
    : 'rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition hover:brightness-110';

  return (
    <nav className={navClass}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between sm:h-20">
          <Link
            href="/"
            className="flex-shrink-0 text-xl font-black tracking-tight text-blue-500 transition-colors hover:text-blue-400 sm:text-2xl"
            onClick={closeMenu}
          >
            MockInterview<span className="hidden sm:inline text-slate-400"> AI</span>
          </Link>

          <div className="hidden items-center gap-1 md:flex lg:gap-2">
            {navigationLinks.map((link) => (
              link.href !== '/contact' && (
                <Link key={link.href} href={link.href} className={linkClass}>
                  {link.label}
                </Link>
              )
            ))}
            <Link href="/contact" className={buttonBase}>
              Contact Us
            </Link>
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsSettingsOpen((prev) => !prev)}
                className={isDarkTheme
                  ? 'inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10'
                  : 'inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-white'}
                aria-label="Open theme settings"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
                  <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 0 0-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 0 0-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 0 0-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 0 0-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 0 0 1.066-2.573c-.94-1.543.826-3.31 2.37-2.37a1.724 1.724 0 0 0 2.572-1.065Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <span>Settings</span>
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
                  <path fillRule="evenodd" d="M5.22 7.22a.75.75 0 0 1 1.06 0L10 10.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 8.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                </svg>
              </button>

              {isSettingsOpen && (
                <div className={isDarkTheme
                  ? 'absolute right-0 top-12 z-20 w-48 rounded-2xl border border-white/10 bg-slate-900/95 p-2 shadow-2xl shadow-slate-950/40 backdrop-blur-xl'
                  : 'absolute right-0 top-12 z-20 w-48 rounded-2xl border border-slate-200 bg-white/90 p-2 shadow-xl shadow-slate-200/80 backdrop-blur-xl'}>
                  {themeOptions.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => applyTheme(option.key)}
                      className={theme === option.key
                        ? 'flex w-full items-center justify-between rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-3 py-2 text-left text-sm font-semibold text-white'
                        : isDarkTheme
                          ? 'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-200 transition hover:bg-white/5'
                          : 'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-100'}
                    >
                      <span>{option.label}</span>
                      {theme === option.key && (
                        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
                          <path fillRule="evenodd" d="M16.704 4.296a1 1 0 0 1 0 1.414l-7.071 7.071a1 1 0 0 1-1.414 0L3.296 8.89a1 1 0 1 1 1.414-1.414l3.636 3.636 6.364-6.364a1 1 0 0 1 1.414 0Z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {email ? (
              <>
                <span className={isDarkTheme ? 'rounded-md px-3 py-2 text-sm text-slate-300' : 'rounded-md px-3 py-2 text-sm text-gray-600'}>
                  {email}
                </span>
                <button onClick={signOut} className={buttonBase}>
                  Sign out
                </button>
              </>
            ) : (
              <Link href="/auth" className={buttonBase}>
                Sign in
              </Link>
            )}
          </div>

          <div className="flex items-center gap-2 md:hidden">
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsSettingsOpen((prev) => !prev)}
                className={isDarkTheme ? 'inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10' : 'inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white/80 text-slate-700 hover:bg-white'}
                aria-label="Open theme settings"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
                  <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 0 0-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 0 0-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 0 0-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 0 0-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 0 0 1.066-2.573c-.94-1.543.826-3.31 2.37-2.37a1.724 1.724 0 0 0 2.572-1.065Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>

              {isSettingsOpen && (
                <div className={isDarkTheme
                  ? 'absolute right-0 top-12 z-20 w-40 rounded-2xl border border-white/10 bg-slate-900/95 p-2 shadow-2xl shadow-slate-950/40 backdrop-blur-xl'
                  : 'absolute right-0 top-12 z-20 w-40 rounded-2xl border border-slate-200 bg-white/90 p-2 shadow-xl shadow-slate-200/80 backdrop-blur-xl'}>
                  {themeOptions.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => applyTheme(option.key)}
                      className={theme === option.key
                        ? 'flex w-full items-center justify-between rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-3 py-2 text-left text-xs font-semibold text-white'
                        : isDarkTheme
                          ? 'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-xs font-medium text-slate-200 transition hover:bg-white/5'
                          : 'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-xs font-medium text-slate-700 transition hover:bg-slate-100'}
                    >
                      <span>{option.label}</span>
                      {theme === option.key && (
                        <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
                          <path fillRule="evenodd" d="M16.704 4.296a1 1 0 0 1 0 1.414l-7.071 7.071a1 1 0 0 1-1.414 0L3.296 8.89a1 1 0 1 1 1.414-1.414l3.636 3.636 6.364-6.364a1 1 0 0 1 1.414 0Z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className={isDarkTheme ? 'inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-200 hover:bg-white/5' : 'inline-flex h-10 w-10 items-center justify-center rounded-md text-gray-600 hover:bg-gray-100'}
              aria-expanded={isMenuOpen}
              aria-label="Toggle navigation menu"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isMenuOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} />
              </svg>
            </button>
          </div>
        </div>

        {isMenuOpen && (
          <div className={isDarkTheme ? 'border-t border-white/10 md:hidden' : 'border-t border-gray-200 md:hidden'}>
            <div className="space-y-1 px-2 py-3">
              {navigationLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={isDarkTheme ? 'block rounded-md px-3 py-2 text-base font-medium text-slate-200 hover:bg-white/5 hover:text-white' : 'block rounded-md px-3 py-2 text-base font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900'}
                  onClick={closeMenu}
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href="/contact"
                className={isDarkTheme ? 'block w-full rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 mt-2 text-center text-sm font-medium text-white transition hover:brightness-110' : 'block w-full rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 mt-2 text-center text-sm font-medium text-white transition hover:brightness-110'}
                onClick={closeMenu}
              >
                Contact Us
              </Link>
            </div>

            <div className={isDarkTheme ? 'space-y-2 border-t border-white/10 px-2 py-3' : 'space-y-2 border-t border-gray-200 px-2 py-3'}>
              {email ? (
                <>
                  <p className={isDarkTheme ? 'px-3 py-2 text-sm text-slate-300' : 'px-3 py-2 text-sm text-gray-600'}>{email}</p>
                  <button
                    onClick={signOut}
                    className="w-full rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:brightness-110"
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <Link
                  href="/auth"
                  className="block w-full rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-center text-sm font-medium text-white transition hover:brightness-110"
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
