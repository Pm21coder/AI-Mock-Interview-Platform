import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';

/**
 * Persistent authentication store with localStorage support.
 * Automatically syncs with auth-change events and storage changes.
 */
const EMPTY_AUTH_SNAPSHOT = Object.freeze({ token: null, email: null });
let cachedAuthSnapshot = EMPTY_AUTH_SNAPSHOT;

const authStore = {
  getSnapshot: () => {
    if (typeof window === 'undefined') return EMPTY_AUTH_SNAPSHOT;

    const nextSnapshot = {
      token: window.localStorage.getItem('auth_token'),
      email: window.localStorage.getItem('auth_email'),
    };

    if (
      cachedAuthSnapshot.token === nextSnapshot.token &&
      cachedAuthSnapshot.email === nextSnapshot.email
    ) {
      return cachedAuthSnapshot;
    }

    cachedAuthSnapshot = nextSnapshot;
    return cachedAuthSnapshot;
  },
  subscribe: (callback) => {
    if (typeof window === 'undefined') return () => {};

    window.addEventListener('storage', callback);
    window.addEventListener('auth-change', callback);
    return () => {
      window.removeEventListener('storage', callback);
      window.removeEventListener('auth-change', callback);
    };
  },
};

const getServerSnapshot = () => EMPTY_AUTH_SNAPSHOT;

/**
 * Hook to access persistent authentication state.
 * Returns { token, email, isAuthenticated }
 */
export function useAuth() {
  const auth = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, getServerSnapshot);
  
  const isAuthenticated = Boolean(auth.token);
  
  const login = useCallback((token, email) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('auth_token', token);
      window.localStorage.setItem('auth_email', email);
      window.dispatchEvent(new Event('auth-change'));
    }
  }, []);
  
  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('auth_token');
      window.localStorage.removeItem('auth_email');
      window.dispatchEvent(new Event('auth-change'));
    }
  }, []);
  
  return {
    token: auth.token,
    email: auth.email,
    isAuthenticated,
    login,
    logout,
  };
}

/**
 * Hook to get display name from email (e.g., "john.doe@example.com" -> "John Doe")
 */
export function useDisplayName() {
  const { email } = useAuth();
  
  if (!email || email === 'guest@local') return '';
  
  const localPart = email.split('@')[0] || '';
  return localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}
