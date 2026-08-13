'use client';

import { useState } from 'react';
import { submitEmailSupport } from '../utils/api';
import toast from 'react-hot-toast';

export default function EmailSupportWidget() {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ subject: '', message: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.subject.trim() || !formData.message.trim()) {
      toast.error('Please fill in all fields');
      return;
    }

    try {
      setLoading(true);
      const result = await submitEmailSupport(formData.subject, formData.message);

      if (result.success) {
        toast.success(result.message);
        setFormData({ subject: '', message: '' });
        setShowForm(false);
      }
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error('Email support is only available with Basic or Pro plans');
      } else {
        toast.error(err.message || 'Failed to submit support request');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="w-full rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          📧 Contact Email Support
        </button>
      ) : (
        <div className="rounded-lg bg-white p-6 shadow-lg border border-gray-200">
          <h3 className="font-bold text-gray-900 mb-4">Send Support Request</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject
              </label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                placeholder="Briefly describe your issue"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Message
              </label>
              <textarea
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                placeholder="Describe your issue in detail..."
                rows="4"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                disabled={loading}
              />
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                disabled={loading}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send Request'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
