'use client';

import { useState, useEffect, useCallback, useSyncExternalStore } from 'react';
import Navigation from '@/components/Navigation';
import { getDashboardStats } from '@/utils/api';
import { onSocketEvent, emitSocketEvent } from '@/utils/socket';

function getDisplayName(email) {
  const localPart = email?.split('@')[0] || '';
  return localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}

function getUsernameSnapshot() {
  if (typeof window === 'undefined') return '';
  return getDisplayName(window.localStorage.getItem('auth_email'));
}

function subscribeToAuthChanges(callback) {
  window.addEventListener('storage', callback);
  window.addEventListener('auth-change', callback);
  return () => {
    window.removeEventListener('storage', callback);
    window.removeEventListener('auth-change', callback);
  };
}

export default function DashboardPage() {
  const [stats, setStats] = useState({ interviews_completed: 0, average_score: 0, confidence_score: 0 });
  const [recentInterviews, setRecentInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [liveUpdate, setLiveUpdate] = useState(false);
  const username = useSyncExternalStore(subscribeToAuthChanges, getUsernameSnapshot, () => '');

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getDashboardStats();
      // Normalize multiple possible response shapes from API/axios
      // server may return { stats: {...}, recent_interviews: [...] }
      // or axios wrappers may nest under .data
      const payload = data?.stats ? data : (data?.data ? data.data : data);

      if (!payload) {
        setError('Server returned an unexpected response');
        return;
      }

      if (payload.error) {
        setError('Server error. Please try again later.');
        return;
      }

      const statsObj = payload.stats || payload;
      // Defensive mapping: support both `interviews_completed` and `completed_interviews`
      const normalizedStats = {
        interviews_completed: statsObj.interviews_completed ?? statsObj.completed_interviews ?? 0,
        average_score: statsObj.average_score ?? statsObj.avg_score ?? 0,
        confidence_score: statsObj.confidence_score ?? statsObj.confidence ?? 0,
      };
      setStats(normalizedStats);

      const recent = payload.recent_interviews || payload.recentInterviews || [];
      if (Array.isArray(recent)) {
        setRecentInterviews(recent);
      }
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Failed to load dashboard data. Please check your connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If the user just completed an interview, the session page sets this
    // flag to signal that a fresh fetch is needed immediately on mount.
    const needsFreshFetch = typeof window !== 'undefined' && window.sessionStorage.getItem('dashboard_refresh') === 'true';
    if (needsFreshFetch) {
      window.sessionStorage.removeItem('dashboard_refresh');
    }

    // Defer the initial (always fresh) fetch to avoid synchronous setState
    // within the effect. This also handles a completed-interview refresh.
    const initialFetch = setTimeout(fetchDashboardData, 0);
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds

    // Subscribe to real-time dashboard updates via Socket.IO.
    // When an interview completes, the backend emits `dashboard_update`
    // with the fresh stats, so we update the UI immediately.
    const handleDashboardUpdate = (data) => {
      console.debug('Received dashboard_update socket payload:', data);
      if (data && data.stats) {
        setStats({
          interviews_completed: data.stats.interviews_completed ?? 0,
          average_score: data.stats.average_score ?? 0,
          confidence_score: data.stats.confidence_score ?? 0,
        });
        // Normalize recent interviews to a consistent array of objects
        const incomingRecent = data.stats.recent_interviews || data.stats.recentInterviews || [];
        if (Array.isArray(incomingRecent)) {
          setRecentInterviews(incomingRecent.map((it) => ({
            role: it.role || it.job_role || 'N/A',
            score: typeof it.score === 'number' ? it.score : (it.score ? Number(it.score) : it.score),
            date: it.date || it.created_at || new Date().toISOString(),
            confidence: typeof it.confidence === 'number' ? it.confidence : (it.confidence ? Number(it.confidence) : it.confidence),
          })));
        }
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
        setLiveUpdate(true);
        setTimeout(() => setLiveUpdate(false), 3000);
      }
    };

    const unsubscribe = onSocketEvent('dashboard_update', handleDashboardUpdate);
    // Explicitly join the dashboard room so the backend can route updates.
    emitSocketEvent('join_dashboard', {
      token: typeof window !== 'undefined' ? window.localStorage.getItem('auth_token') : null,
    });

    return () => {
      clearTimeout(initialFetch);
      clearInterval(interval);
      unsubscribe();
    };
  }, [fetchDashboardData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="container mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
          {/* Skeleton loader for perceived performance */}
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="h-36 animate-pulse rounded-xl bg-white p-6 shadow" />
            <div className="h-36 animate-pulse rounded-xl bg-white p-6 shadow" />
            <div className="h-36 animate-pulse rounded-xl bg-white p-6 shadow" />
          </div>
          <div className="mt-8 rounded-xl bg-white p-6 shadow-lg">
            <div className="h-64 animate-pulse rounded" />
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="container mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
          <div className="rounded-lg bg-red-50 p-6 text-red-700">
            <p className="font-medium">{error}</p>
            <button onClick={fetchDashboardData} className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors">
              Try Again
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            {username && <p className="mt-1 text-sm text-gray-600">Welcome back, {username}! 👋</p>}
          </div>
          <div className="flex items-center gap-4">
            {liveUpdate && (
              <span className="animate-pulse rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800">
                Live update received
              </span>
            )}
            {lastUpdated && <p className="text-sm text-gray-500">Last updated: {lastUpdated}</p>}
            <button
              onClick={fetchDashboardData}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Stat Cards with Score Bars */}
        <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="Interviews Completed"
            value={stats.interviews_completed}
            icon="🎯"
            gradient="from-blue-500 to-indigo-600"
            showBar={false}
          />
          <StatCard
            title="Average Score"
            value={`${stats.average_score}%`}
            icon="📊"
            gradient="from-green-500 to-emerald-600"
            score={stats.average_score}
            maxValue={100}
          />
          <StatCard
            title="Confidence Score"
            value={`${stats.confidence_score}%`}
            icon="💪"
            gradient="from-purple-500 to-violet-600"
            score={stats.confidence_score}
            maxValue={100}
          />
        </div>

        {/* Recent Interviews */}
        <div className="rounded-xl bg-white p-6 shadow-lg">
          <h2 className="mb-4 text-xl font-semibold text-gray-900">Recent Interviews</h2>

          <div className="space-y-4">
            {recentInterviews.length > 0 ? (
              recentInterviews.map((item, index) => (
                <InterviewRow key={index} interview={item} />
              ))
            ) : (
              <div className="py-8 text-center text-gray-500">
                <p>No recent interviews to display.</p>
                <p className="mt-2 text-sm">Complete an interview to see your results here.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ title, value, icon, gradient, score, maxValue, showBar = true }) {
  const barWidth = showBar && score !== undefined ? Math.min(100, Math.max(0, (score / maxValue) * 100)) : 0;
  const barColor = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className={`rounded-xl bg-gradient-to-r ${gradient} p-6 text-white shadow-lg`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-blue-100">{title}</p>
          <p className="mt-2 text-3xl font-bold">{value}</p>
        </div>
        <div className="text-3xl">{icon}</div>
      </div>
      {showBar && score !== undefined && (
        <div className="mt-4 h-2 w-full rounded-full bg-white/20">
          <div
            className={`h-2 rounded-full ${barColor} transition-all duration-500`}
            style={{ width: `${barWidth}%` }}
          />
        </div>
      )}
    </div>
  );
}

function InterviewRow({ interview }) {
  const score = typeof interview.score === 'number' ? interview.score : 0;
  const confidence = typeof interview.confidence === 'number' ? interview.confidence : 0;
  const scoreColor = score >= 80 ? 'bg-green-100 text-green-800' : score >= 60 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800';
  const confidenceColor = confidence >= 80 ? 'bg-blue-100 text-blue-800' : confidence >= 60 ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-800';

  const displayScore = typeof interview.score === 'number' ? `${interview.score}%` : interview.score;
  const displayConfidence = typeof interview.confidence === 'number' ? `${interview.confidence}%` : interview.confidence;

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4 transition-colors hover:bg-gray-50">
      <div className="flex items-center gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-xl">
          💼
        </div>
        <div>
          <p className="font-semibold text-gray-900">{interview.role}</p>
          <p className="text-sm text-gray-500">{new Date(interview.date).toLocaleDateString()}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className={`rounded-full px-3 py-1 text-sm font-medium ${scoreColor}`}>
          Score: {displayScore}
        </span>
        <span className={`rounded-full px-3 py-1 text-sm font-medium ${confidenceColor}`}>
          Confidence: {displayConfidence}
        </span>
      </div>
    </div>
  );
}
