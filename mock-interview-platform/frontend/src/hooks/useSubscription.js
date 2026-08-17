import { useCallback, useEffect, useState, useRef } from 'react';
import { useAuth } from './useAuth';
import { getSubscriptionStatus, invalidateAllSubscriptionCaches } from '../utils/api';

const STORAGE_KEY = 'subscription_data';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Get cached subscription data from localStorage.
 * Returns null if cache is expired.
 */
function getCachedSubscription() {
  if (typeof window === 'undefined') return null;
  
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    
    const { data, timestamp } = JSON.parse(stored);
    
    // Check if cache has expired
    if (Date.now() - timestamp > CACHE_DURATION) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    
    return data;
  } catch {
    return null;
  }
}

/**
 * Store subscription data in localStorage with timestamp.
 */
function cacheSubscription(data) {
  if (typeof window === 'undefined') return;
  
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      data,
      timestamp: Date.now(),
    }));
  } catch {
    // localStorage may be full or unavailable
  }
}

/**
 * Clear cached subscription data (exported for external use).
 */
export function invalidateSubscriptionCache() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(STORAGE_KEY);
  invalidateAllSubscriptionCaches();
}

/**
 * Hook to access persistent subscription data.
 * Automatically fetches and caches subscription status.
 */
export function useSubscription() {
  const { isAuthenticated } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const isFetchingRef = useRef(false);
  const lastFetchRef = useRef(0);

  /**
   * Fetch subscription from API and cache it.
   * Debounces rapid calls to avoid redundant requests.
   * Optimized to load cached data immediately and fetch in background.
   */
  const fetchSubscription = useCallback(async (skipCache = false) => {
    if (!isAuthenticated || typeof window === 'undefined') {
      setSubscription(null);
      return;
    }

    // Return cached data if available and not skipped
    if (!skipCache) {
      const cached = getCachedSubscription();
      if (cached) {
        setSubscription(cached);
        setLoading(false);
        // Silently refresh in background after 30 seconds
        const refreshTimer = setTimeout(() => {
          if (isFetchingRef.current) return;
          isFetchingRef.current = true;
          getSubscriptionStatus()
            .then(data => {
              if (data && !data.error) {
                setSubscription(data);
                cacheSubscription(data);
              }
            })
            .catch(() => {
              // Silent fail, keep cached data
            })
            .finally(() => {
              isFetchingRef.current = false;
            });
        }, 30000);
        return () => clearTimeout(refreshTimer);
      }
    }

    // Debounce rapid fetch calls
    const now = Date.now();
    if (isFetchingRef.current || (now - lastFetchRef.current < 800)) {
      return;
    }

    isFetchingRef.current = true;
    lastFetchRef.current = now;
    setLoading(true);
    setError(null);

    try {
      const data = await getSubscriptionStatus();
      if (data && !data.error) {
        setSubscription(data);
        cacheSubscription(data);
        setError(null);
      } else {
        setError(data?.error || 'Failed to load subscription');
      }
    } catch (err) {
      console.error('Failed to fetch subscription:', err);
      
      // Fall back to cached data if API fails
      const cached = getCachedSubscription();
      if (cached) {
        setSubscription(cached);
        setError(null);
      } else {
        setError('Failed to load subscription data');
      }
    } finally {
      setLoading(false);
      isFetchingRef.current = false;
    }
  }, [isAuthenticated]);

  // Load cached subscription immediately on mount
  useEffect(() => {
    if (isAuthenticated && typeof window !== 'undefined') {
      const cached = getCachedSubscription();
      if (cached) {
        setSubscription(cached);
      }
    }
  }, [isAuthenticated]);

  // Fetch subscription when authentication changes or on first load
  useEffect(() => {
    if (isAuthenticated) {
      fetchSubscription();
    } else {
      setSubscription(null);
    }
  }, [isAuthenticated, fetchSubscription]);

  // Refresh subscription every 5 minutes
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      fetchSubscription(true); // Skip cache and fetch fresh
    }, CACHE_DURATION);

    return () => clearInterval(interval);
  }, [isAuthenticated, fetchSubscription]);

  return {
    subscription,
    loading,
    error,
    refetch: () => fetchSubscription(true), // Force refresh
    isGuest: !isAuthenticated,
  };
}
