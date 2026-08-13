/* eslint-disable react-hooks/set-state-in-effect */
'use client';

import { useState, useCallback, useEffect, useSyncExternalStore } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '../../components/Navigation';
import toast from 'react-hot-toast';
import { uploadResume, getResumeHistory, getResumeAnalysis } from '../../utils/api';

// Custom store that tracks auth state
const authStore = {
  getSnapshot: () => window.localStorage.getItem('auth_email') || '',
  subscribe: (callback) => {
    window.addEventListener('storage', callback);
    window.addEventListener('auth-change', callback);
    return () => {
      window.removeEventListener('storage', callback);
      window.removeEventListener('auth-change', callback);
    };
  },
};

const getServerAuthEmail = () => '';

export default function ResumePage() {
  const router = useRouter();
  const userEmail = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, getServerAuthEmail);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  const loadHistory = useCallback(async () => {
    try {
      const data = await getResumeHistory();
      if (data.resumes) {
        setHistory(data.resumes);
      }
    } catch (error) {
      console.error('Failed to load resume history:', error);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const allowedTypes = ['.pdf', '.docx', '.doc', '.txt'];
      const fileExt = '.' + selectedFile.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExt)) {
        toast.error('Please upload a PDF, DOCX, or TXT file');
        return;
      }
      
      setFile(selectedFile);
      setAnalysis(null);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    
    // Check authentication
    if (!userEmail) {
      toast.error('Please sign in to analyze your resume');
      router.push('/auth');
      return;
    }
    
    if (!file) {
      toast.error('Please select a file to upload');
      return;
    }

    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await uploadResume(formData);
      
      if (result.success) {
        toast.success('Resume uploaded and analyzed successfully!');
        setAnalysis(result.analysis);
        setFile(null);
        // Reset file input
        e.target.reset();
        // Reload history
        loadHistory();
      } else {
        toast.error(result.error || 'Failed to analyze resume');
      }
    } catch (error) {
      toast.error('Failed to upload resume. Please try again.');
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleViewAnalysis = async (resumeId) => {
    try {
      const result = await getResumeAnalysis(resumeId);
      if (result.analysis) {
        setAnalysis(result.analysis);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } catch (error) {
      toast.error('Failed to load analysis');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="container mx-auto px-4 py-8">
        <div className="mx-auto max-w-4xl">
          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="mb-2 text-3xl font-bold text-gray-900">Resume Analyzer</h1>
            <p className="text-gray-600">
              Upload your resume and get AI-powered feedback to improve it
            </p>
          </div>

          {/* Upload Section */}
          <div className="mb-8 rounded-xl bg-white p-8 shadow-lg">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Upload Your Resume</h2>
            
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label htmlFor="resume-upload" className="mb-2 block text-sm font-medium text-gray-700">
                  Select Resume File (PDF, DOCX, or TXT)
                </label>
                <input
                  id="resume-upload"
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={handleFileChange}
                  className="block w-full rounded-lg border border-gray-300 p-3 text-gray-900 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-white hover:file:bg-blue-700"
                  disabled={uploading}
                />
                {file && (
                  <p className="mt-2 text-sm text-gray-600">
                    Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={!file || uploading || !userEmail}
                className="w-full rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-all duration-200 hover:bg-blue-700 hover:shadow-lg disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                {uploading ? 'Analyzing Resume...' : 'Upload and Analyze'}
              </button>
              
              {!userEmail && (
                <p className="mt-3 text-sm text-amber-600 bg-amber-50 p-3 rounded-lg">
                  ℹ️ Please <a href="/auth" className="font-semibold underline hover:text-amber-700">sign in</a> to analyze your resume.
                </p>
              )}
            </form>
          </div>

          {/* Analysis Results */}
          {analysis && (
            <div className="mb-8 rounded-xl bg-white p-8 shadow-lg">
              <h2 className="mb-6 text-2xl font-bold text-gray-900">Analysis Results</h2>
              
              {/* Overall Score */}
              <div className="mb-6 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-600 p-6 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-100">Overall Score</p>
                    <p className="text-4xl font-bold">{analysis.overall_score}%</p>
                  </div>
                  <div className="text-4xl">📊</div>
                </div>
              </div>

              {/* Section Scores */}
              {analysis.sections && (
                <div className="mb-6 grid gap-4 md:grid-cols-2">
                  {Object.entries(analysis.sections).map(([section, data]) => (
                    <div key={section} className="rounded-lg border border-gray-200 p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900 capitalize">{section}</h3>
                        <span className={`rounded-full px-3 py-1 text-sm font-medium ${
                          data.score >= 80 ? 'bg-green-100 text-green-800' :
                          data.score >= 60 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {data.score}%
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">{data.feedback}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* ATS Optimization */}
              {analysis.ats_optimization && (
                <div className="mb-6 rounded-lg bg-purple-50 p-4">
                  <h3 className="mb-2 font-semibold text-purple-900">ATS Optimization</h3>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="flex-1 h-2 rounded-full bg-purple-200">
                      <div
                        className="h-2 rounded-full bg-purple-600 transition-all duration-500"
                        style={{ width: `${analysis.ats_optimization.score}%` }}
                      />
                    </div>
                    <span className="font-semibold text-purple-900">{analysis.ats_optimization.score}%</span>
                  </div>
                  <p className="text-sm text-purple-700">{analysis.ats_optimization.feedback}</p>
                </div>
              )}

              {/* Strengths */}
              {analysis.strengths && analysis.strengths.length > 0 && (
                <div className="mb-6 rounded-lg bg-green-50 p-4">
                  <h3 className="mb-2 font-semibold text-green-800">Strengths</h3>
                  <ul className="space-y-1">
                    {analysis.strengths.map((strength, index) => (
                      <li key={index} className="flex items-start gap-2 text-green-700">
                        <span className="mt-1 text-green-500">✓</span>
                        <span>{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Improvements */}
              {analysis.improvements && analysis.improvements.length > 0 && (
                <div className="mb-6 rounded-lg bg-yellow-50 p-4">
                  <h3 className="mb-2 font-semibold text-yellow-800">Areas for Improvement</h3>
                  <ul className="space-y-1">
                    {analysis.improvements.map((improvement, index) => (
                      <li key={index} className="flex items-start gap-2 text-yellow-700">
                        <span className="mt-1 text-yellow-500">•</span>
                        <span>{improvement}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Suggestions */}
              {analysis.suggestions && analysis.suggestions.length > 0 && (
                <div className="mb-6 rounded-lg bg-blue-50 p-4">
                  <h3 className="mb-2 font-semibold text-blue-800">Suggestions</h3>
                  <ul className="space-y-1">
                    {analysis.suggestions.map((suggestion, index) => (
                      <li key={index} className="flex items-start gap-2 text-blue-700">
                        <span className="mt-1 text-blue-500">💡</span>
                        <span>{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Detailed Feedback */}
              {analysis.detailed_feedback && (
                <div className="rounded-lg bg-gray-50 p-4">
                  <h3 className="mb-2 font-semibold text-gray-900">Detailed Feedback</h3>
                  <p className="text-gray-700">{analysis.detailed_feedback}</p>
                </div>
              )}
            </div>
          )}

          {/* Resume History */}
          <div className="rounded-xl bg-white p-8 shadow-lg">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Previous Analyses</h2>
            
            {loadingHistory ? (
              <div className="py-8 text-center text-gray-500">Loading history...</div>
            ) : history.length > 0 ? (
              <div className="space-y-3">
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 p-4 transition-colors hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-xl">
                        📄
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">{item.filename}</p>
                        <p className="text-sm text-gray-500">
                          {new Date(item.uploaded_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`rounded-full px-3 py-1 text-sm font-medium ${
                        item.overall_score >= 80 ? 'bg-green-100 text-green-800' :
                        item.overall_score >= 60 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        Score: {item.overall_score}%
                      </span>
                      <button
                        onClick={() => handleViewAnalysis(item.id)}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
                      >
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-gray-500">
                <p>No previous analyses yet.</p>
                <p className="mt-2 text-sm">Upload a resume to see it here.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
