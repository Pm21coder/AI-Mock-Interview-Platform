'use client';

import { useState, useEffect } from 'react';
import { getAdvancedAnalytics } from '../utils/api';

export default function AdvancedAnalyticsDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getAdvancedAnalytics();
        setAnalytics(data);
      } catch (err) {
        if (err.response?.status === 403) {
          setError('Advanced analytics is only available with a Pro subscription');
        } else {
          setError('Failed to load analytics');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="rounded-lg bg-white p-8 shadow-lg">
        <div className="flex items-center justify-center space-x-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
          <span className="text-gray-600">Loading analytics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-blue-50 p-6 border border-blue-200">
        <h3 className="font-semibold text-blue-900 mb-2">Pro Feature</h3>
        <p className="text-blue-800">{error}</p>
        <a href="/subscription" className="mt-3 inline-block text-blue-600 hover:text-blue-700 font-semibold">
          Upgrade to Pro →
        </a>
      </div>
    );
  }

  if (!analytics) return null;

  const { performance_trend, detailed_breakdown, interviews_by_category, most_common_role, average_score } = analytics;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Advanced Analytics</h2>
        <p className="text-gray-600 mt-1">Detailed insights into your interview performance</p>
      </div>

      {/* Performance Trend Card */}
      <div className="rounded-lg bg-white p-6 shadow-lg border-l-4 border-blue-600">
        <h3 className="font-bold text-gray-900 mb-4">Performance Trend</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Overall Trend</p>
            <p className="text-2xl font-bold">
              {performance_trend.trend === 'improving' && '📈 Improving'}
              {performance_trend.trend === 'declining' && '📉 Declining'}
              {performance_trend.trend === 'stable' && '➡️ Stable'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Average Score</p>
            <p className="text-2xl font-bold text-green-600">{performance_trend.average}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Recent Average</p>
            <p className="text-2xl font-bold text-blue-600">{performance_trend.recent_average}%</p>
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg bg-white p-6 shadow-lg">
          <p className="text-sm text-gray-600 mb-2">Most Practiced Role</p>
          <p className="text-xl font-bold text-gray-900">{most_common_role || 'N/A'}</p>
        </div>
        <div className="rounded-lg bg-white p-6 shadow-lg">
          <p className="text-sm text-gray-600 mb-2">Average Performance</p>
          <p className="text-xl font-bold text-green-600">{average_score ? `${average_score}%` : 'N/A'}</p>
        </div>
        <div className="rounded-lg bg-white p-6 shadow-lg">
          <p className="text-sm text-gray-600 mb-2">Interview Categories</p>
          <p className="text-xl font-bold text-blue-600">{Object.keys(interviews_by_category || {}).length}</p>
        </div>
      </div>

      {/* Detailed Breakdown */}
      {detailed_breakdown && Object.keys(detailed_breakdown).length > 0 && (
        <div className="rounded-lg bg-white p-6 shadow-lg">
          <h3 className="font-bold text-gray-900 mb-4">Performance by Category</h3>
          <div className="space-y-3">
            {Object.entries(detailed_breakdown).map(([category, data]) => (
              <div key={category} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900 capitalize">{category}</p>
                  <p className="text-sm text-gray-600">{data.count} interview{data.count !== 1 ? 's' : ''}</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-32 h-2 bg-gray-200 rounded-full">
                    <div
                      className="h-2 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
                      style={{ width: `${data.average_score}%` }}
                    />
                  </div>
                  <span className="text-lg font-bold text-blue-600">{data.average_score}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categories Breakdown */}
      {interviews_by_category && Object.keys(interviews_by_category).length > 0 && (
        <div className="rounded-lg bg-white p-6 shadow-lg">
          <h3 className="font-bold text-gray-900 mb-4">Questions by Category</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(interviews_by_category).map(([category, count]) => (
              <div key={category} className="text-center p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{count}</p>
                <p className="text-sm text-gray-600 capitalize">{category}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
