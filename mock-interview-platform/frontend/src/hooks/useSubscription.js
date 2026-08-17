import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from './useAuth';
import {
  getSubscriptionStatus,
  invalidateAllSubscriptionCaches,
  invalidateQuestionCategoriesCache,
} from '../utils/api';

const STORAGE_KEY = 'subscription_data';
const CACHE_DURATION = 60 * 1000; // Show cached data instantly; revalidate every minute.
const inFlightRequests = new Map();

function getCachedSubscription(accountEmail) {
  if (typeof window === 'undefined' || !accountEmail) return null;

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    const { accountEmail: cachedEmail, data, timestamp } = JSON.parse(stored);
    if (cachedEmail !== accountEmail || !data || Date.now() - timestamp > CACHE_DURATION) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    return data;
  } catch {
    return null;
  }
}

function cacheSubscription(data, accountEmail) {
  if (typeof window === 'undefined' || !accountEmail) return;

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      accountEmail,
      data,
      timestamp: Date.now(),
    }));
  } catch {
    // localStorage may be full or unavailable.
  }
}

function requestSubscription(accountKey) {
  const pendingRequest = inFlightRequests.get(accountKey);
  if (pendingRequest) return pendingRequest;

  const request = getSubscriptionStatus().finally(() => {
    inFlightRequests.delete(accountKey);
  });
  inFlightRequests.set(accountKey, request);
  return request;
}

/** Clear the current user's subscription and dependent API caches. */
export function invalidateSubscriptionCache() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(STORAGE_KEY);
  invalidateAllSubscriptionCaches();
}

/**
 * Read subscription details with a cache-first, network-revalidated strategy.
 * Cached data makes navigation immediate; the status endpoint remains the
 * source of truth and is revalidated on mount, on demand, and every minute.
 */
export function useSubscription() {
  const { isAuthenticated, email } = useAuth();
  const [subscription, setSubscription] = useState(() => getCachedSubscription(email));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const subscriptionTierRef = useRef(subscription?.tier || null);

  const applySubscription = useCallback((data) => {
    if (subscriptionTierRef.current && data?.tier && subscriptionTierRef.current !== data.tier) {
      // Categories are plan-dependent, so an upgrade/downgrade must not reuse
      // a response cached for the former plan.
      invalidateQuestionCategoriesCache();
    }

    subscriptionTierRef.current = data?.tier || null;
    setSubscription(data);
    cacheSubscription(data, email);
  }, [email]);

  const fetchSubscription = useCallback(async () => {
    if (!isAuthenticated || typeof window === 'undefined') {
      subscriptionTierRef.current = null;
      setSubscription(null);
      setLoading(false);
      return null;
    }

    const cached = getCachedSubscription(email);
    if (cached) {
      applySubscription(cached);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await requestSubscription(email || '__authenticated__');
      if (!data || data.error) {
        throw new Error(data?.error || 'Failed to load subscription');
      }

      applySubscription(data);
      return data;
    } catch {
      // Keep the last verified value visible if the user is temporarily offline.
      if (!cached) {
        setError('Failed to load subscription data');
      }
      return cached;
    } finally {
      setLoading(false);
    }
  }, [applySubscription, email, isAuthenticated]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      if (!isAuthenticated) {
        subscriptionTierRef.current = null;
        setSubscription(null);
        setLoading(false);
        return;
      }

      const cached = getCachedSubscription(email);
      if (cached) applySubscription(cached);
      void fetchSubscription();
    }, 0);

    return () => window.clearTimeout(initialLoad);
  }, [applySubscription, email, fetchSubscription, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return undefined;

    const interval = window.setInterval(() => {
      void fetchSubscription();
    }, CACHE_DURATION);

    const refreshOnResume = () => {
      if (document.visibilityState === 'visible') {
        void fetchSubscription();
      }
    };

    const handlePageShow = () => {
      void fetchSubscription();
    };

    document.addEventListener('visibilitychange', refreshOnResume);
    window.addEventListener('pageshow', handlePageShow);
    window.addEventListener('focus', handlePageShow);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', refreshOnResume);
      window.removeEventListener('pageshow', handlePageShow);
      window.removeEventListener('focus', handlePageShow);
    };
  }, [fetchSubscription, isAuthenticated]);

  return {
    subscription,
    loading,
    error,
    refetch: fetchSubscription,
    isGuest: !isAuthenticated,
  };
}
