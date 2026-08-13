import { useState } from 'react';
import { generateInterviewQuestions, generateFeedback } from '../utils/api';

export function useInterview() {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState([]);
  const [feedback, setFeedback] = useState(null);

  const startInterview = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      const { role, category, difficulty } = formData;
      const result = await generateInterviewQuestions(role, category, difficulty);
      setQuestions(result.data);
      return result.data;
    } catch (err) {
      const errorMessage = err.message || 'Something went wrong';
      setError(errorMessage);
      console.error('Interview start error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const submitForFeedback = async (role, qaPairs) => {
    setLoading(true);
    setError(null);
    try {
      if (!Array.isArray(qaPairs) || qaPairs.length === 0) {
        throw new Error('No Q&A pairs provided');
      }
      if (qaPairs.some((p) => !p.answer?.trim())) {
        throw new Error('Every question needs a non-empty answer');
      }

      const result = await generateFeedback(role, qaPairs);
      setFeedback(result.data);
      return result.data;
    } catch (err) {
      const errorMessage = err.message || 'Failed to generate feedback';
      setError(errorMessage);
      console.error('Feedback error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => setError(null);
  const resetState = () => {
    setError(null);
    setQuestions([]);
    setFeedback(null);
  };

  return {
    error,
    loading,
    questions,
    feedback,
    startInterview,
    submitForFeedback,
    clearError,
    resetState,
  };
}
