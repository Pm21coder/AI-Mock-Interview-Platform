/**
 * ⚠️ DEPRECATED - This component is dead code and should not be used
 *
 * This was a reference implementation for direct Gemini integration from the frontend.
 * However, the live application uses a different architecture:
 *
 * LIVE ARCHITECTURE:
 * - Frontend communicates with Flask backend at /api/interview/*
 * - Backend handles Gemini API integration, authentication, and data persistence
 * - Socket.IO broadcasts dashboard updates to connected clients
 * - Interview sessions are stored in MongoDB with full audit trail
 *
 * DEAD CODE ARCHITECTURE (this file):
 * - Frontend calls Gemini API directly from browser
 * - This approach was abandoned because:
 *   1. Exposes API keys to the browser (security risk)
 *   2. No server-side rate limiting or usage tracking
 *   3. Can't persist data across sessions
 *   4. Doesn't integrate with subscription tiers
 *   5. No audit trail for compliance
 *
 * This file is kept for reference only. Do not import or use it.
 *
 * For the actual interview implementation, see:
 * - frontend/src/app/interview/session/page.js (live interview page)
 * - backend/app/routes/interview.py (backend interview logic)
 *
 * TODO: Delete this file and useInterview.js, and the orphaned Next.js API routes
 * in frontend/src/app/api/interview/ as part of code cleanup.
 */

export default function InterviewSessionExample() {
  throw new Error('InterviewSessionExample is deprecated dead code - use /interview/session/page.js instead');
}
      )}

      {/* Interview Setup Form */}
      {!sessionStarted && (
        <form onSubmit={handleStartInterview} className="space-y-4 mb-6">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="e.g., Software Engineer"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option>Technical</option>
                <option>Behavioral</option>
                <option>General</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option>Easy</option>
                <option>Medium</option>
                <option>Hard</option>
              </select>
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Generating Questions...' : 'Start Interview'}
          </button>
        </form>
      )}

      {/* Questions and Answers */}
      {sessionStarted && questions.length > 0 && (
        <div className="space-y-6 mb-6">
          <h2 className="text-2xl font-bold">Interview Session</h2>
          {qaPairs.map((pair, index) => (
            <div key={index} className="border rounded-lg p-4 space-y-3">
              <div>
                <p className="text-sm text-gray-600">Question {index + 1}</p>
                <p className="font-medium text-lg">{pair.question}</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Your Answer</label>
                <textarea
                  value={pair.answer}
                  onChange={(e) => handleAnswerChange(index, e.target.value)}
                  placeholder="Type your answer here..."
                  rows={4}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ))}
          <button
            onClick={handleSubmitForFeedback}
            disabled={loading || qaPairs.some((p) => !p.answer?.trim())}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
          >
            {loading ? 'Generating Feedback...' : 'Get Feedback'}
          </button>
        </div>
      )}

      {/* Feedback Display */}
      {feedback && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 space-y-4">
          <div>
            <h3 className="text-lg font-bold text-blue-900">Overall Score</h3>
            <p className="text-3xl font-bold text-blue-600">{feedback.overallScore}/100</p>
            <p className="text-gray-700 mt-2">{feedback.overallSummary}</p>
          </div>

          <div className="border-t pt-4">
            <h4 className="font-bold mb-4">Per-Question Feedback</h4>
            <div className="space-y-4">
              {feedback.perQuestion?.map((item, idx) => (
                <div key={idx} className="bg-white p-4 rounded-lg border-l-4 border-blue-400">
                  <div className="flex justify-between items-start mb-2">
                    <p className="font-medium">{item.question}</p>
                    <span className="text-lg font-bold text-blue-600">{item.score}</span>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="font-semibold text-green-700 mb-1">Strengths:</p>
                      <ul className="list-disc pl-5 space-y-1">
                        {item.strengths?.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="font-semibold text-orange-700 mb-1">Improvements:</p>
                      <ul className="list-disc pl-5 space-y-1">
                        {item.improvements?.map((imp, i) => (
                          <li key={i}>{imp}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex justify-center items-center p-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Generating...</p>
          </div>
        </div>
      )}
    </div>
  );
}
