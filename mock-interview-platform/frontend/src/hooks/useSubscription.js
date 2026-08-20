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
// Simple SWR-style in-memory cache keyed by accountEmail
const swrCache = new Map(); // key -> { data, timestamp }

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

/**
 * requestSubscription: deduplicate in-flight requests and provide a basic
 * stale-while-revalidate cache. Returns a promise that resolves to the
 * subscription data. If cache exists and is fresh it returns cached data
 * immediately and triggers a background revalidation.
 */
function requestSubscription(accountKey) {
  // If a cached fresh value exists, return it immediately but trigger
  // a background revalidation to update the cache.
  const cached = swrCache.get(accountKey);
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    // Background revalidate (do not await)
    if (!inFlightRequests.has(accountKey)) {
      const bg = getSubscriptionStatus()
        .then((data) => {
          swrCache.set(accountKey, { data, timestamp: Date.now() });
          try { cacheSubscription(data, accountKey); } catch (e) {}
          return data;
        })
        .finally(() => inFlightRequests.delete(accountKey));
      inFlightRequests.set(accountKey, bg);
    }
    return Promise.resolve(cached.data);
  }

  // If a fetch is already in-flight, return that promise
  const pending = inFlightRequests.get(accountKey);
  if (pending) return pending;

  // Otherwise, fetch and cache the result
  const req = getSubscriptionStatus()
    .then((data) => {
      swrCache.set(accountKey, { data, timestamp: Date.now() });
      try { cacheSubscription(data, accountKey); } catch (e) {}
      return data;
    })
    .finally(() => {
      inFlightRequests.delete(accountKey);
    });

  inFlightRequests.set(accountKey, req);
  return req;
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
  // Backoff handling for rate-limited responses (429)
  const backoffUntilRef = useRef(0); // timestamp (ms) until which polling is suppressed
  const backoffMsRef = useRef(60 * 1000); // initial backoff 1 minute
  const [isUsingBackoffCache, setIsUsingBackoffCache] = useState(false); // shows UI when cached due to backoff

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

    // If we're currently in a backoff period due to previous 429, avoid hitting the server
    if (Date.now() < backoffUntilRef.current) {
      console.warn('[useSubscription] Skipping fetch due to backoff until', new Date(backoffUntilRef.current).toISOString());
      setLoading(false);
      setIsUsingBackoffCache(true);
      return cached;
    }

    try {
      const data = await requestSubscription(email || '__authenticated__');
      if (!data || data.error) {
        throw new Error(data?.error || 'Failed to load subscription');
      }

      // On success reset backoff
      backoffMsRef.current = 60 * 1000;
      backoffUntilRef.current = 0;
      setIsUsingBackoffCache(false);

      applySubscription(data);
      setError(null);  // Clear error on success
      return data;
    } catch (err) {
      // If server responded with 429, apply exponential backoff to avoid spamming the endpoint
      const status = err?.response?.status || (err?.status || null);
      if (status === 429) {
        const prev = backoffMsRef.current || 60 * 1000;
        const next = Math.min(prev * 2, 60 * 60 * 1000); // cap at 1 hour
        backoffMsRef.current = next;
        backoffUntilRef.current = Date.now() + next;
        console.warn('[useSubscription] Received 429, backing off for ms=', next);
        setIsUsingBackoffCache(true);
      }

      // Keep the last verified value visible if the user is temporarily offline.
      if (!cached) {
        // Only show error if it's not a network issue or if we have no fallback data
        const isNetworkError = !err?.response;
        const errorMsg = err?.message || 'Unable to load subscription';
        console.warn('[useSubscription] Failed to fetch:', { isNetworkError, message: errorMsg });
        
        // Don't show "Failed to load subscription data" - instead use a fallback subscription
        // This prevents the error message from appearing when user hasn't purchased a plan yet
        setSubscription({
          tier: 'free',
          status: 'active',
          interviews_remaining: 3,
          monthly_limit: 3,
          features: [],
          is_trial: false
        });
        setError(null);  // Don't show error - use fallback silently
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
    isUsingBackoffCache,
  };
}
