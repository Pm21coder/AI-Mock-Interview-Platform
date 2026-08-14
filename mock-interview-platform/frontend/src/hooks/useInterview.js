/**
 * ⚠️ DEPRECATED - This hook is dead code and should not be used
 *
 * This was part of an early reference implementation for direct Gemini integration
 * from the frontend. However, the live application uses a different architecture:
 *
 * LIVE ARCHITECTURE:
 * - Frontend communicates with Flask backend at /api/interview/*
 * - Backend handles Gemini API integration, authentication, and data persistence
 * - Socket.IO broadcasts dashboard updates to connected clients
 *
 * DEAD CODE ARCHITECTURE (this file):
 * - Frontend calls Gemini API directly from browser
 * - This has several problems:
 *   1. Exposes Gemini API keys to the browser (security risk)
 *   2. Can't track usage or enforce rate limiting
 *   3. Can't persist interview data to database
 *   4. Doesn't integrate with subscription system
 *
 * This file is kept for reference only. Do not import or use it.
 * Delete this file and frontend/src/components/InterviewSessionExample.js
 * and the orphaned API routes in frontend/src/app/api/interview/ when cleaning up.
 *
 * For the real interview implementation, see:
 * - frontend/src/app/interview/session/page.js (live interview page)
 * - backend/app/routes/interview.py (backend interview logic)
 */

// Placeholder to prevent import errors during cleanup
export function useInterview() {
  throw new Error('useInterview is deprecated dead code - use the Flask backend integration instead');
}

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
