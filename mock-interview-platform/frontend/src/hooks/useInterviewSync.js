'use client';

import { useCallback, useEffect, useRef } from 'react';
import { invalidateSubscriptionCache } from './useSubscription';
import { onSocketEvent } from '../utils/socket';

/**
 * Keep views that show subscription usage in sync after an interview starts.
 * The quota is consumed when questions are generated; the dashboard has its
 * own `dashboard_update` event for completed-interview performance metrics.
 */
export function useInterviewSync(onInterviewUsageChange) {
  const processedSessionIds = useRef(new Set());

  const syncUsage = useCallback((data) => {
    const sessionId = data?.session_id;
    if (sessionId) {
      if (processedSessionIds.current.has(sessionId)) return;
      processedSessionIds.current.add(sessionId);
    }

    invalidateSubscriptionCache();
    onInterviewUsageChange?.(data);
  }, [onInterviewUsageChange]);

  useEffect(() => {
    const handleInterviewUsageUpdate = (data) => {
      console.debug('Interview usage update received:', data);
      syncUsage(data);

      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('dashboard_stats_cache');
      }

      if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
        try {
          const channel = new BroadcastChannel('interview_sync');
          channel.postMessage({
            type: 'interview_usage_updated',
            data: data,
          });
          channel.close();
        } catch (e) {
          console.warn('BroadcastChannel not available:', e);
        }
      }
    };

    const unsubscribe = onSocketEvent('interview_usage_updated', handleInterviewUsageUpdate);

    const handleMessage = (event) => {
      if (event.data?.type === 'interview_usage_updated') {
        console.debug('Interview usage updated from another tab:', event.data);
        syncUsage(event.data.data);
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem('dashboard_stats_cache');
        }
      }
    };
    
    if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
      try {
        const channel = new BroadcastChannel('interview_sync');
        channel.addEventListener('message', handleMessage);
        return () => {
          channel.removeEventListener('message', handleMessage);
          channel.close();
          unsubscribe?.();
        };
      } catch (e) {
        console.warn('BroadcastChannel setup failed:', e);
        return () => unsubscribe?.();
      }
    }
    
    return () => unsubscribe?.();
  }, [syncUsage]);
}

/**
 * Hook to listen for subscription/quota changes from server.
 * Useful for syncing when user upgrades their plan.
 */
export function useSubscriptionSync(onSubscriptionChange) {
  useEffect(() => {
    const handleSubscriptionUpdate = (data) => {
      console.debug('Subscription updated event received:', data);
      
      // Invalidate subscription cache
      invalidateSubscriptionCache();
      
      // Broadcast to other tabs
      if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
        try {
          const channel = new BroadcastChannel('subscription_sync');
          channel.postMessage({
            type: 'subscription_updated',
            data: data,
            timestamp: new Date().toISOString(),
          });
          channel.close();
        } catch (e) {
          console.warn('BroadcastChannel not available:', e);
        }
      }
      
      onSubscriptionChange?.(data);
    };
    
    const unsubscribe = onSocketEvent('subscription_updated', handleSubscriptionUpdate);
    
    const handleMessage = (event) => {
      if (event.data?.type === 'subscription_updated') {
        console.debug('Subscription updated from another tab:', event.data);
        invalidateSubscriptionCache();
        onSubscriptionChange?.(event.data);
      }
    };
    
    if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
      try {
        const channel = new BroadcastChannel('subscription_sync');
        channel.addEventListener('message', handleMessage);
        return () => {
          channel.removeEventListener('message', handleMessage);
          channel.close();
          unsubscribe?.();
        };
      } catch (e) {
        return () => unsubscribe?.();
      }
    }
    
    return () => unsubscribe?.();
  }, [onSubscriptionChange]);
}
