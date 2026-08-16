'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '../../components/Navigation';
import AdvancedAnalyticsDashboard from '../../components/AdvancedAnalyticsDashboard';
import EmailSupportWidget from '../../components/EmailSupportWidget';
import { useSubscription } from '../../hooks/useSubscription';
import {
  getUsageStats,
  getBillingHistory,
  getAvailableFeatures,
  cancelSubscription,
  getQuestionCategories,
  getFeedbackHistoryLimit,
} from '../../utils/api';

export default function SubscriptionManagementPage() {
  const router = useRouter();
  const { subscription, loading: subscriptionLoading, refetch: refetchSubscription } = useSubscription();
  const [usageStats, setUsageStats] = useState(null);
  const [billingHistory, setBillingHistory] = useState([]);
  const [features, setFeatures] = useState({});
  const [questionCategories, setQuestionCategories] = useState(null);
  const [feedbackHistoryLimit, setFeedbackHistoryLimit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [statsData, historyData, featuresData, categoriesData, historyLimitData] = await Promise.all([
          getUsageStats(),
          getBillingHistory(),
          getAvailableFeatures(),
          getQuestionCategories().catch(() => null),
          getFeedbackHistoryLimit().catch(() => null),
        ]);

        if (statsData && !statsData.error) {
          setUsageStats(statsData);
        }

        if (historyData && historyData.billing_history) {
          setBillingHistory(historyData.billing_history);
        }

        if (featuresData && featuresData.features) {
          setFeatures(featuresData.features);
        }

        if (categoriesData) {
          setQuestionCategories(categoriesData);
        }

        if (historyLimitData) {
          setFeedbackHistoryLimit(historyLimitData);
        }
      } catch (err) {
        setError('Failed to load subscription data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [subscription]); // Refetch other data when subscription changes

  const handleCancelSubscription = async () => {
    try {
      setCancelLoading(true);
      await cancelSubscription();
      setShowCancelConfirm(false);
      // Refresh subscription data from cache
      await refetchSubscription();
      alert('Subscription cancelled successfully');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to cancel subscription');
    } finally {
      setCancelLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getProgressPercentage = () => {
    if (!subscription || !usageStats) return 0;
    const limit = subscription.monthly_limit;
    if (limit === 'unlimited') return 0;
    return Math.round((usageStats.interviews_this_month / limit) * 100);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center space-x-3 text-gray-600">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
              <span>Loading subscription details...</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Navigation />

      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Subscription Management</h1>
          <p className="text-gray-600">View and manage your subscription, usage, and billing</p>
        </div>

        {error && (
          <div className="mb-8 rounded-lg bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Cancel Confirmation Modal */}
        {showCancelConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-gray-900">Cancel Subscription?</h2>
              <p className="mb-6 text-gray-600">
                Are you sure you want to cancel your {subscription?.tier.toUpperCase()} subscription?
                You will lose access to premium features and be downgraded to the Free plan.
              </p>
              <div className="flex gap-4">
                <button
                  onClick={() => setShowCancelConfirm(false)}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
                >
                  Keep Subscription
                </button>
                <button
                  onClick={handleCancelSubscription}
                  disabled={cancelLoading}
                  className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {cancelLoading ? 'Canceling...' : 'Cancel Subscription'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Current Plan Card */}
          <div className="rounded-lg bg-white p-6 shadow-lg lg:col-span-3">
            <h2 className="mb-4 text-xl font-bold text-gray-900">Current Plan</h2>
            <div className="grid gap-6 md:grid-cols-3">
              <div>
                <p className="text-sm text-gray-600">Plan Tier</p>
                <p className="text-2xl font-bold text-gray-900 capitalize">
                  {subscription?.tier}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Status</p>
                <p className="text-2xl font-bold capitalize">
                  <span className={subscription?.status === 'active' ? 'text-green-600' : 'text-orange-600'}>
                    {subscription?.status}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">
                  {subscription?.is_trial ? 'Trial Ends' : 'Renews'}
                </p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatDate(subscription?.subscription_end_date)}
                </p>
              </div>
            </div>
            {subscription?.tier !== 'free' && (
              <div className="mt-6">
                <button
                  onClick={() => setShowCancelConfirm(true)}
                  className="rounded-lg border border-red-300 px-4 py-2 text-red-600 hover:bg-red-50"
                >
                  Cancel Subscription
                </button>
              </div>
            )}
          </div>

          {/* Usage Stats */}
          <div className="rounded-lg bg-white p-6 shadow-lg lg:col-span-2">
            <h2 className="mb-4 text-xl font-bold text-gray-900">Interview Usage</h2>

            {usageStats && (
              <>
                <div className="space-y-4">
                  <div>
                    <div className="mb-2 flex justify-between">
                      <p className="text-sm font-medium text-gray-700">Monthly Limit</p>
                      <p className="text-sm font-bold text-gray-900">
                        {usageStats.interviews_this_month} / {subscription?.monthly_limit}
                      </p>
                    </div>
                    {subscription?.monthly_limit !== 'unlimited' && (
                      <div className="h-3 w-full rounded-full bg-gray-200">
                        <div
                          className="h-3 rounded-full bg-blue-600 transition-all duration-300"
                          style={{ width: `${getProgressPercentage()}%` }}
                        ></div>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-4">
                    <div className="rounded-lg bg-blue-50 p-4">
                      <p className="text-sm text-blue-600">Used This Month</p>
                      <p className="text-2xl font-bold text-blue-900">
                        {usageStats.interviews_this_month}
                      </p>
                    </div>
                    <div className="rounded-lg bg-green-50 p-4">
                      <p className="text-sm text-green-600">Remaining</p>
                      <p className="text-2xl font-bold text-green-900">
                        {subscription?.interviews_remaining === 'unlimited'
                          ? '∞'
                          : subscription?.interviews_remaining}
                      </p>
                    </div>
                  </div>

                  {usageStats.total_interviews > 0 && (
                    <>
                      <div className="border-t pt-4">
                        <p className="text-sm text-gray-600">Most Common Role</p>
                        <p className="font-semibold text-gray-900">
                          {usageStats.most_common_role || 'N/A'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Average Score</p>
                        <p className="text-lg font-bold text-gray-900">
                          {usageStats.average_score
                            ? `${Math.round(usageStats.average_score)}%`
                            : 'N/A'}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Features Card */}
          <div className="rounded-lg bg-white p-6 shadow-lg">
            <h2 className="mb-4 text-lg font-bold text-gray-900">Available Features</h2>

            <div className="space-y-3">
              {Object.entries(features).map(([feature, enabled]) => (
                <div key={feature} className="flex items-center gap-3">
                  {enabled ? (
                    <svg
                      className="h-5 w-5 text-green-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="h-5 w-5 text-gray-300"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  <span className={enabled ? 'text-gray-900' : 'text-gray-400'}>
                    {feature.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Additional Subscription Details */}
        <div className="mt-8 space-y-8">
          {/* Question Categories Info */}
          {questionCategories && (
            <div className="rounded-lg bg-white p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-gray-900">📚 Question Categories</h2>
              <p className="mb-4 text-gray-600">Available question categories for your tier:</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {questionCategories.available_categories.map((category) => (
                  <div key={category} className="rounded-lg bg-blue-50 p-3 text-center">
                    <p className="font-medium text-blue-900 capitalize">{category.replace('_', ' ')}</p>
                  </div>
                ))}
              </div>
              {!questionCategories.all_categories_available && (
                <p className="mt-4 text-sm text-amber-700 bg-amber-50 p-3 rounded-lg">
                  💡 Upgrade to Basic or Pro to access all question categories.
                </p>
              )}
            </div>
          )}

          {/* Feedback History Limit */}
          {feedbackHistoryLimit && (
            <div className="rounded-lg bg-white p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-gray-900">📋 Feedback History Retention</h2>
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg">
                <p className="text-lg font-semibold text-gray-900">{feedbackHistoryLimit.message}</p>
                <p className="text-sm text-gray-600 mt-2">
                  Your feedback and interview records are securely stored and accessible on your dashboard.
                </p>
              </div>
            </div>
          )}

          {/* Advanced Analytics - Pro Only */}
          {subscription?.tier === 'pro' && (
            <div className="rounded-lg bg-white p-6 shadow-lg">
              <AdvancedAnalyticsDashboard />
            </div>
          )}

          {/* Email Support - Basic+ */}
          {(subscription?.tier === 'basic' || subscription?.tier === 'pro') && (
            <div className="rounded-lg bg-white p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-gray-900">💬 Email Support</h2>
              <p className="mb-4 text-gray-600">Get help from our support team. We&apos;ll respond within 24 hours.</p>
              <EmailSupportWidget />
            </div>
          )}
        </div>

        {/* Billing History */}
        <div className="mt-8 rounded-lg bg-white p-6 shadow-lg">
          <h2 className="mb-6 text-xl font-bold text-gray-900">Billing History</h2>

          {billingHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Date</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Event</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Tier</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {billingHistory.map((record, idx) => (
                    <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {formatDate(record.timestamp)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 capitalize">
                        {record.event_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium capitalize text-gray-900">
                        {record.tier}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {record.amount ? `₹${record.amount}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-600">No billing history available</p>
          )}
        </div>
      </main>
    </div>
  );
}
