'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Navigation from '@/components/Navigation';
import { login, register } from '@/utils/api';

export default function AuthPage() {
  const router = useRouter();
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = window.localStorage.getItem('auth_token');
      if (token) {
        const params = new URLSearchParams(window.location.search);
        const nextPath = params.get('next');
        router.push(nextPath?.startsWith('/') ? nextPath : '/interview/setup');
      }
    }
  }, [router]);

  const submit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const result = await (isRegistering ? register : login)({ email, password });
      window.localStorage.setItem('auth_token', result.token);
      window.localStorage.setItem('auth_email', result.user.email);
      window.dispatchEvent(new Event('auth-change'));
      toast.success(isRegistering ? 'Account created.' : 'Signed in successfully.');
      const params = new URLSearchParams(window.location.search);
      const nextPath = params.get('next');
      router.push(nextPath?.startsWith('/') ? nextPath : '/interview/setup');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="container mx-auto flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="rounded-xl bg-white p-8 shadow-lg">
            <div className="mb-6 text-center">
              <div className="mb-4 text-4xl">🔐</div>
              <h1 className="text-2xl font-bold text-gray-900">
                {isRegistering ? 'Create an account' : 'Welcome back'}
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                Save interview activity when a database is configured, or use the app in practice mode.
              </p>
            </div>

            <form onSubmit={submit} className="space-y-5" action="#" method="post">
              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">Email address</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                  className="input-field"
                />
              </div>
              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">Password</label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="At least 8 characters"
                  autoComplete="current-password"
                  minLength="8"
                  required
                  className="input-field"
                />
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white transition-all duration-200 hover:bg-blue-700 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                    Please wait...
                  </span>
                ) : isRegistering ? (
                  'Create account'
                ) : (
                  'Sign in'
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => setIsRegistering((value) => !value)}
                className="text-sm text-blue-600 hover:text-blue-700 hover:underline"
              >
                {isRegistering ? 'Already have an account? Sign in' : 'New here? Create an account'}
              </button>
            </div>

            <div className="mt-6 border-t border-gray-200 pt-4 text-center">
              <p className="text-xs text-gray-500">
                Demo: demo@mockinterview.app / demo12345
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
