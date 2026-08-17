'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '../../../components/Navigation';
import toast from 'react-hot-toast';
import { getQuestionCategories } from '../../../utils/api';
import { useSubscription } from '../../../hooks/useSubscription';
import { useInterviewSync } from '../../../hooks/useInterviewSync';
import { canStartInterview } from '../../../utils/interviewQuota.mjs';

export default function InterviewSetup() {
  const router = useRouter();
  const { subscription, loading: subscriptionLoading, refetch } = useSubscription();
  const [availableCategories, setAvailableCategories] = useState(['technical', 'behavioral']);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [planDetails, setPlanDetails] = useState({
    tier: 'free',
    interviewsRemaining: 3,
    monthlyLimit: 3,
  });
  const [formData, setFormData] = useState({
    job_role: '',
    category: 'technical',
    difficulty: 'medium',
    num_questions: 5,
  });

  // Refresh quota and available categories when another tab starts an
  // interview for this account.
  useInterviewSync(refetch);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await getQuestionCategories();
        const categories = response?.available_categories || ['technical', 'behavioral'];
        setAvailableCategories(categories);
        setPlanDetails({
          tier: response?.tier || 'free',
          interviewsRemaining: response?.interviews_remaining ?? 3,
          monthlyLimit: response?.monthly_limit ?? 3,
        });
        setFormData((prev) => (
          categories.includes(prev.category)
            ? prev
            : { ...prev, category: categories[0] || 'technical' }
        ));
      } catch (error) {
        console.error('Failed to load question categories:', error);
        setAvailableCategories(['technical', 'behavioral']);
      } finally {
        setLoadingCategories(false);
      }
    };

    fetchCategories();
  }, [subscription]); // Re-fetch when subscription changes


  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.job_role) {
      toast.error('Please enter a job role');
      return;
    }

    const quotaStatus = canStartInterview({
      tier: subscription?.tier || planDetails.tier,
      monthly_limit: subscription?.monthly_limit ?? planDetails.monthlyLimit,
      interviews_remaining: subscription?.interviews_remaining ?? planDetails.interviewsRemaining,
    });

    if (!quotaStatus.allowed) {
      toast.error(quotaStatus.message || 'Your monthly interview limit has been reached. Please upgrade your plan.');
      router.replace('/subscription?upgrade_prompt=limit_reached');
      return;
    }

    if (!availableCategories.includes(formData.category)) {
      toast.error('This category is not available on your current plan.');
      return;
    }

    router.push(
      `/interview/session?job_role=${encodeURIComponent(formData.job_role)}&category=${formData.category}&difficulty=${formData.difficulty}&num_questions=${formData.num_questions}`
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 transition-colors duration-200 dark:bg-slate-950">
      <Navigation />

      <div className="container mx-auto max-w-3xl px-4 py-12">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-slate-100">Setup Your Mock Interview</h1>
          <p className="mt-2 text-gray-600 dark:text-slate-300">
            Configure your interview settings and start practicing with AI-powered feedback.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-lg transition-colors duration-200 dark:border-slate-700 dark:bg-slate-900">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Job Role *</label>
              <input
                type="text"
                value={formData.job_role}
                onChange={(e) => setFormData({ ...formData, job_role: e.target.value })}
                placeholder="e.g., Software Engineer, Product Manager, Data Scientist"
                className="input-field"
                required
              />
            </div>

            <div className="grid gap-6 sm:grid-cols-2 sm:gap-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">Question Category</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="input-field"
                  disabled={loadingCategories || availableCategories.length === 0}
                >
                  {availableCategories.length === 0 ? (
                    <option value="technical">Technical</option>
                  ) : (
                    availableCategories.map((category) => (
                      <option key={category} value={category}>
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">Difficulty Level</label>
                <select
                  value={formData.difficulty}
                  onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                  className="input-field"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
            </div>

            {!loadingCategories && (
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
                <p className="font-semibold">
                  {planDetails.tier.charAt(0).toUpperCase() + planDetails.tier.slice(1)} plan access
                </p>
                <p className="mt-1 text-blue-800">
                  {planDetails.monthlyLimit === 'unlimited'
                    ? 'Unlimited mock interviews and all question categories.'
                    : `${planDetails.interviewsRemaining} of ${planDetails.monthlyLimit} mock interviews remain this month.`}
                </p>
                {planDetails.tier === 'free' && (
                  <button
                    type="button"
                    onClick={() => router.push('/subscription')}
                    className="mt-3 font-semibold text-blue-700 underline hover:text-blue-900"
                  >
                    Upgrade to unlock all categories and more interviews
                  </button>
                )}
              </div>
            )}

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Number of Questions</label>
              <div className="flex items-center gap-4">
                <input
                  type="number"
                  min="3"
                  max="10"
                  value={formData.num_questions}
                  onChange={(e) => setFormData({ ...formData, num_questions: parseInt(e.target.value) || 5 })}
                  className="input-field w-24"
                />
                <span className="text-sm text-gray-500">
                  Recommended: 5 questions (15-20 minutes)
                </span>
              </div>
            </div>

            <div className="border-t border-gray-200 pt-6">
              <button
                type="submit"
                className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white transition-all duration-200 hover:bg-blue-700 hover:shadow-lg"
              >
                Start Interview
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
