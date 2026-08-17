'use client';

import { useState, useEffect, useCallback, useSyncExternalStore } from 'react';
import Navigation from '../../components/Navigation';
import { getDashboardStats } from '../../utils/api';
import { useDisplayName } from '../../hooks/useAuth';
import { useInterviewSync } from '../../hooks/useInterviewSync';
import { onSocketEvent, emitSocketEvent } from '../../utils/socket';

export default function DashboardPage() {
  const [stats, setStats] = useState({ interviews_completed: 0, average_score: 0, confidence_score: 0 });
  const [recentInterviews, setRecentInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [liveUpdate, setLiveUpdate] = useState(false);
  const [isFallbackData, setIsFallbackData] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const username = useDisplayName();

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setRetrying(false);
      const data = await getDashboardStats();
      const payload = data?.stats ? data : (data?.data ? data.data : data);
      const fallbackState = Boolean(data?.fallback || payload?.fallback);
      setIsFallbackData(fallbackState);

      if (!payload) {
        setError('Server returned an unexpected response');
        return;
      }

      if (payload.error) {
        setError('Server error. Please try again later.');
        return;
      }

      const statsObj = payload.stats || payload;
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
      setRetrying(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isFallbackData && !retrying) {
      const reconnectTimer = setTimeout(() => {
        fetchDashboardData();
      }, 8000);
      return () => clearTimeout(reconnectTimer);
    }

    return undefined;
  }, [fetchDashboardData, isFallbackData, retrying]);

  // Listen for interview completion events and refresh data
  useInterviewSync(() => {
    console.log('Interview completed, refreshing dashboard data...');
    // Refresh dashboard data immediately when interview completes
    fetchDashboardData();
  });

  useEffect(() => {
    const needsFreshFetch = typeof window !== 'undefined' && window.sessionStorage.getItem('dashboard_refresh') === 'true';
    if (needsFreshFetch) {
      window.sessionStorage.removeItem('dashboard_refresh');
    }

    const initialFetch = setTimeout(fetchDashboardData, 0);
    const interval = setInterval(fetchDashboardData, 60000); // Changed from 30s to 60s for better performance

    const handleDashboardUpdate = (data) => {
      console.debug('Received dashboard_update socket payload:', data);
      if (data && data.stats) {
        setStats({
          interviews_completed: data.stats.interviews_completed ?? 0,
          average_score: data.stats.average_score ?? 0,
          confidence_score: data.stats.confidence_score ?? 0,
        });

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
      <div className="dashboard-shell min-h-screen">
        <Navigation />
        <main className="container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-8 h-12 w-52 animate-pulse rounded-full bg-white/60" />
          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            <div className="h-40 animate-pulse rounded-[1.75rem] bg-white/60 shadow-soft" />
            <div className="h-40 animate-pulse rounded-[1.75rem] bg-white/60 shadow-soft" />
            <div className="h-40 animate-pulse rounded-[1.75rem] bg-white/60 shadow-soft" />
          </div>
          <div className="mt-8 h-72 animate-pulse rounded-[1.75rem] bg-white/60 shadow-soft" />
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-shell min-h-screen">
        <Navigation />
        <main className="container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="rounded-[1.75rem] border border-red-200 bg-red-50/90 p-6 text-red-700 shadow-soft">
            <p className="font-medium">{error}</p>
            <button onClick={fetchDashboardData} className="mt-4 rounded-xl bg-gradient-to-r from-red-500 to-rose-500 px-4 py-2 text-white shadow-lg transition hover:brightness-110">
              Try Again
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-shell min-h-screen">
      <Navigation />

      <main className="container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-indigo-600 dark:text-indigo-400">Performance overview</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-900 dark:text-slate-100 sm:text-4xl">Dashboard</h1>
            {username && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Welcome back, {username}! 👋</p>}
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3">
            {liveUpdate && (
              <span className="animate-pulse rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300">
                Live update received
              </span>
            )}
            {isFallbackData && (
              <>
                <span className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-300">
                  {retrying ? 'Retrying connection...' : 'Offline demo data'}
                </span>
                <button
                  type="button"
                  onClick={fetchDashboardData}
                  className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-300 dark:hover:bg-amber-500/15"
                >
                  Reconnect
                </button>
              </>
            )}
            {lastUpdated && <p className="text-sm text-slate-500 dark:text-slate-400">Last updated: {lastUpdated}</p>}
            <button
              onClick={fetchDashboardData}
              className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:-translate-y-0.5 hover:shadow-xl"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="mb-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard
            title="Interviews Completed"
            value={stats.interviews_completed}
            icon="🎯"
            gradient="from-blue-500 via-indigo-600 to-sky-500"
            showBar={false}
          />
          <StatCard
            title="Average Score"
            value={`${stats.average_score}%`}
            icon="📊"
            gradient="from-emerald-500 via-green-500 to-teal-500"
            score={stats.average_score}
            maxValue={100}
          />
          <StatCard
            title="Confidence Score"
            value={`${stats.confidence_score}%`}
            icon="💪"
            gradient="from-violet-500 via-purple-500 to-fuchsia-500"
            score={stats.confidence_score}
            maxValue={100}
          />
        </div>

        <div className="rounded-[1.75rem] border border-slate-200 bg-white/80 p-5 shadow-soft backdrop-blur-sm dark:border-slate-700 dark:bg-slate-900/75 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Recent Interviews</h2>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600 dark:bg-slate-800 dark:text-slate-200">
              {recentInterviews.length} sessions
            </span>
          </div>

          <div className="space-y-4">
            {recentInterviews.length > 0 ? (
              recentInterviews.map((item, index) => (
                <InterviewRow key={index} interview={item} />
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                <p className="text-lg font-semibold text-slate-700 dark:text-slate-200">No recent interviews to display.</p>
                <p className="mt-2 text-sm dark:text-slate-300">Complete an interview to see your results here.</p>
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
  const barColor = score >= 80 ? 'bg-emerald-300' : score >= 60 ? 'bg-amber-300' : 'bg-rose-300';

  return (
    <div className={`rounded-[1.75rem] bg-gradient-to-br ${gradient} p-5 text-white shadow-soft sm:p-6`}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/80">{title}</p>
          <p className="mt-3 text-3xl font-black tracking-tight">{value}</p>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-2xl shadow-inner shadow-white/10">
          {icon}
        </div>
      </div>
      {showBar && score !== undefined && (
        <div className="mt-5 h-2.5 w-full overflow-hidden rounded-full bg-white/20">
          <div
            className={`h-full rounded-full ${barColor} transition-all duration-500`}
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
  const scoreColor = score >= 80 ? 'bg-emerald-100 text-emerald-800' : score >= 60 ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800';
  const confidenceColor = confidence >= 80 ? 'bg-blue-100 text-blue-800' : confidence >= 60 ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100 text-slate-700';

  const displayScore = typeof interview.score === 'number' ? `${interview.score}%` : interview.score;
  const displayConfidence = typeof interview.confidence === 'number' ? `${interview.confidence}%` : interview.confidence;

  return (
    <div className="flex flex-col gap-3 rounded-[1.25rem] border border-slate-200 bg-gradient-to-r from-slate-50 to-white p-4 transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-slate-700 dark:from-slate-800 dark:to-slate-900 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-violet-100 text-xl shadow-inner dark:from-blue-900/70 dark:to-violet-900/70">💼</div>
        <div>
          <p className="font-bold text-slate-900 dark:text-slate-100">{interview.role}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">{new Date(interview.date).toLocaleDateString()}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:justify-end">
        <span className={`rounded-full px-3 py-1.5 text-sm font-semibold ${scoreColor}`}>
          Score: {displayScore}
        </span>
        <span className={`rounded-full px-3 py-1.5 text-sm font-semibold ${confidenceColor}`}>
          Confidence: {displayConfidence}
        </span>
      </div>
    </div>
  );
}
