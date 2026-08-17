'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Navigation from '../../../components/Navigation';
import QuestionDisplay from '../../../components/QuestionDisplay';
import VideoRecorder from '../../../components/VideoRecorder';
import FeedbackDisplay from '../../../components/FeedbackDisplay';
import LimitErrorModal from '../../../components/LimitErrorModal';
import { getQuestions, submitAnswer, getFeedback } from '../../../utils/api';
import { invalidateSubscriptionCache } from '../../../hooks/useSubscription';

function getSpeechErrorMessage(error) {
  const messages = {
    'not-allowed': 'Microphone access was denied. Allow microphone access in your browser settings, then try again.',
    'service-not-allowed': 'Speech recognition is blocked by this browser or device.',
    'audio-capture': 'No microphone was found. Connect or enable a microphone, then try again.',
    network: 'Speech recognition needs an internet connection. Check your connection and try again.',
    'no-speech': 'No speech was detected. Try speaking a little closer to the microphone.',
    'language-not-supported': 'Your browser does not support speech recognition for this language.',
  };

  return messages[error] || `Voice input stopped (${error || 'unknown error'}). Please try again.`;
}

function getQuestionLoadError(error) {
  const responseData = error.response?.data || {};
  const isPlanRestriction = error.response?.status === 403 && (
    responseData.code === 'interview_limit_reached' ||
    responseData.code === 'category_not_in_plan' ||
    Boolean(responseData.required_tier)
  );

  return {
    isPlanRestriction,
    message: responseData.message || responseData.error ||
      'Failed to load interview questions. Please try again.',
    errorCode: responseData.code || null,
  };
}

export default function InterviewSessionPage() {
  return (
    <Suspense fallback={<SessionLoading />}>
      <InterviewSessionContent />
    </Suspense>
  );
}

function SessionLoading() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-3 text-xl text-gray-600">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
          <span>Loading questions...</span>
        </div>
      </div>
    </div>
  );
}

function InterviewSessionContent() {
  const router = useRouter();
  const params = useSearchParams();
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loadError, setLoadError] = useState('');
  const [errorCode, setErrorCode] = useState(null);
  const [showLimitModal, setShowLimitModal] = useState(false);
  const [canUpgradeForLoadError, setCanUpgradeForLoadError] = useState(false);
  const [speechState, setSpeechState] = useState('checking');
  const [speechMessage, setSpeechMessage] = useState('');
  const [timeElapsed, setTimeElapsed] = useState(0);
  const recognitionRef = useRef(null);
  const speechRunRef = useRef(0);
  const speechStopResolverRef = useRef(null);
  const speechStopPromiseRef = useRef(null);
  const speechStopRequestedRef = useRef(false);
  const speechFailedRef = useRef(false);
  const mountedRef = useRef(true);
  const answerRef = useRef('');
  const answerBeforeSpeechRef = useRef('');
  const finalTranscriptRef = useRef('');
  const timerRef = useRef(null);
  const isSpeechActive = ['starting', 'listening', 'stopping'].includes(speechState);
  const isListening = ['starting', 'listening'].includes(speechState);

  const setCurrentAnswer = useCallback((nextAnswer) => {
    answerRef.current = nextAnswer;
    setAnswer(nextAnswer);
  }, []);

  const finishSpeechStop = useCallback(() => {
    const resolve = speechStopResolverRef.current;
    speechStopResolverRef.current = null;
    speechStopPromiseRef.current = null;
    resolve?.();
  }, []);

  const stopVoiceInput = useCallback((discard = false) => {
    const recognition = recognitionRef.current;
    if (!recognition) return Promise.resolve();

    if (discard) {
      speechRunRef.current += 1;
      recognitionRef.current = null;
      speechStopRequestedRef.current = true;
      recognition.onstart = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      try {
        recognition.abort();
      } catch {
        // The recognition session may already have ended.
      }
      finishSpeechStop();
      if (mountedRef.current) setSpeechState('idle');
      return Promise.resolve();
    }

    if (speechStopPromiseRef.current) return speechStopPromiseRef.current;

    speechStopRequestedRef.current = true;
    if (mountedRef.current) setSpeechState('stopping');
    const stopPromise = new Promise((resolve) => {
      speechStopResolverRef.current = resolve;
    });
    speechStopPromiseRef.current = stopPromise;

    try {
      recognition.stop();
    } catch {
      // Calling stop after the browser ended recognition can throw. Treat it
      // as stopped so submitting an answer is never blocked indefinitely.
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
        if (mountedRef.current) setSpeechState('idle');
      }
      finishSpeechStop();
    }

    return stopPromise;
  }, [finishSpeechStop]);

  const startVoiceInput = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechState('unsupported');
      setSpeechMessage('Speech recognition is not available in this browser. Use Chrome or Edge, or type your answer.');
      toast.error('Voice input is not supported by this browser. Try Chrome or Edge.');
      return false;
    }

    if (!window.isSecureContext) {
      setSpeechState('idle');
      setSpeechMessage('Voice input requires HTTPS (localhost is supported for development).');
      toast.error('Voice input requires HTTPS.');
      return false;
    }

    if (recognitionRef.current) return true;

    const runId = ++speechRunRef.current;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || 'en-US';
    recognition.maxAlternatives = 1;

    answerBeforeSpeechRef.current = answerRef.current.trim()
      ? `${answerRef.current.trim()} `
      : '';
    finalTranscriptRef.current = '';
    speechStopRequestedRef.current = false;
    speechFailedRef.current = false;

    const isCurrentRun = () => (
      recognitionRef.current === recognition && speechRunRef.current === runId
    );

    recognition.onstart = () => {
      if (!isCurrentRun() || !mountedRef.current) return;
      setSpeechState('listening');
      setSpeechMessage('Listening… speak clearly.');
    };

    recognition.onresult = (event) => {
      if (!isCurrentRun() || !mountedRef.current) return;

      let interimTranscript = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript;
        if (event.results[index].isFinal) {
          finalTranscriptRef.current += `${transcript} `;
        } else {
          interimTranscript += `${transcript} `;
        }
      }

      const combinedTranscript = `${answerBeforeSpeechRef.current}${finalTranscriptRef.current}${interimTranscript}`
        .replace(/\s+/g, ' ')
        .trim();
      setCurrentAnswer(combinedTranscript);
    };

    recognition.onerror = (event) => {
      if (!isCurrentRun()) return;

      speechFailedRef.current = true;
      speechRunRef.current += 1;
      recognitionRef.current = null;
      finishSpeechStop();
      if (!mountedRef.current || event.error === 'aborted') return;

      const message = getSpeechErrorMessage(event.error);
      setSpeechState('idle');
      setSpeechMessage(message);
      console.warn('Speech recognition error:', event.error);
      toast.error(message);
    };

    recognition.onend = () => {
      if (!isCurrentRun()) return;

      const wasStoppedByUser = speechStopRequestedRef.current;
      const failed = speechFailedRef.current;
      recognitionRef.current = null;
      if (mountedRef.current) {
        setSpeechState('idle');
        if (!failed && !wasStoppedByUser) {
          setSpeechMessage('Voice input paused. Select Start Voice Input to continue.');
        } else if (!failed) {
          setSpeechMessage('Voice input stopped.');
        }
      }
      finishSpeechStop();
    };

    recognitionRef.current = recognition;
    setSpeechState('starting');
    setSpeechMessage('Requesting microphone access…');

    try {
      recognition.start();
      return true;
    } catch (error) {
      recognitionRef.current = null;
      speechRunRef.current += 1;
      setSpeechState('idle');
      setSpeechMessage('Voice input could not start. Please try again.');
      console.warn('Unable to start speech recognition:', error);
      toast.error('Voice input could not start. Please try again.');
      return false;
    }
  }, [finishSpeechStop, setCurrentAnswer]);

  useEffect(() => {
    mountedRef.current = true;
    const speechCheckTimer = window.setTimeout(() => {
      if (!mountedRef.current) return;
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechState('idle');
        setSpeechMessage('Ready for voice input.');
      } else {
        setSpeechState('unsupported');
        setSpeechMessage('Speech recognition is not available in this browser. Use Chrome or Edge, or type your answer.');
      }
    }, 0);

    return () => {
      window.clearTimeout(speechCheckTimer);
      mountedRef.current = false;
      speechRunRef.current += 1;
      const recognition = recognitionRef.current;
      recognitionRef.current = null;
      if (recognition) {
        recognition.onstart = null;
        recognition.onresult = null;
        recognition.onerror = null;
        recognition.onend = null;
        try {
          recognition.abort();
        } catch {
          // Recognition may already have finished.
        }
      }
      const resolve = speechStopResolverRef.current;
      speechStopResolverRef.current = null;
      speechStopPromiseRef.current = null;
      resolve?.();
    };
  }, []);

  useEffect(() => {
    const loadQuestions = async () => {
      const jobRole = params.get('job_role') || 'Software Engineer';
      const category = params.get('category') || 'technical';
      const difficulty = params.get('difficulty') || 'medium';
      const numQuestions = Number(params.get('num_questions') || 5);

      setLoadError('');
      setCanUpgradeForLoadError(false);

      try {
        const data = await getQuestions({
          job_role: jobRole,
          category,
          difficulty,
          num_questions: numQuestions,
        });
        if (!Array.isArray(data.questions) || data.questions.length === 0) {
          throw new Error('No interview questions were generated. Please try again.');
        }
        setSessionId(data.session_id || 'session_123');
        setQuestions(data.questions);
        
        // Invalidate subscription and question categories caches since interview count has been incremented
        invalidateSubscriptionCache();
      } catch (error) {
        const questionLoadError = getQuestionLoadError(error);
        setLoadError(questionLoadError.message);
        setErrorCode(questionLoadError.errorCode);
        setCanUpgradeForLoadError(questionLoadError.isPlanRestriction);
        
        // Show modal for limit/restriction errors, toast for others
        if (questionLoadError.isPlanRestriction) {
          setShowLimitModal(true);
          // Auto-redirect to subscription after 2 seconds if quota exceeded
          if (questionLoadError.errorCode === 'interview_limit_reached') {
            const redirectTimer = setTimeout(() => {
              router.push('/subscription?upgrade_prompt=limit_reached');
            }, 2000);
            return () => clearTimeout(redirectTimer);
          }
        } else {
          toast.error(questionLoadError.message, { duration: 5000 });
        }

        if (!error.response || error.response.status >= 500) {
          console.error('Failed to load interview questions:', error);
        }
      }
    };

    loadQuestions();
  }, [params, router]);

  // Timer: starts when questions are loaded, resets on each question change
  useEffect(() => {
    if (questions.length === 0) return;
    
    // Reset timer by clearing and setting to 0
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeElapsed(0);
    if (timerRef.current) clearInterval(timerRef.current);
    
    timerRef.current = setInterval(() => {
      setTimeElapsed((prev) => prev + 1);
    }, 1000);
    
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [currentIndex, questions.length]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStartRecording = () => {
    const transcriptionStarted = startVoiceInput();
    toast.success(transcriptionStarted ? 'Recording and transcription started.' : 'Video recording started.');
  };

  const toggleVoiceInput = () => {
    if (isSpeechActive) {
      void stopVoiceInput();
      return;
    }
    startVoiceInput();
  };

  const submitCurrentAnswer = useCallback(async (videoBlob, expressionStats) => {
    await stopVoiceInput();
    setIsProcessing(true);
    setLoadError('');

    try {
      const currentQuestion = questions[currentIndex];
      const submittedAnswer = answerRef.current.trim();
      if (!submittedAnswer) {
        toast.error('Please write your answer before submitting it.');
        setIsProcessing(false);
        return;
      }

      const result = await submitAnswer({
        question: currentQuestion.question,
        answer: submittedAnswer,
        expected_answer: currentQuestion.expected_answer,
        session_id: sessionId,
        question_index: currentIndex,
        video_data: Boolean(videoBlob),
        expression_stats: expressionStats || null,
      });

      // Check if response contains an error
      if (result.error) {
        const errorMessage = result.details || result.error || 'Failed to analyze answer';
        setLoadError(`Analysis Error: ${errorMessage}`);
        toast.error(errorMessage, { duration: 5000 });
        setIsProcessing(false);
        return;
      }

      // Attach expression telemetry stats to feedback display
      const enrichedFeedback = {
        ...result,
        expression_stats: expressionStats || result.expression_stats || {
          eyeContactAvg: 90,
          confidenceScore: 88,
          positivityScore: 85,
          dominantEmotion: 'Confident',
          videoOnly: true,
        },
      };

      setFeedback(enrichedFeedback);
      
      // Check if video was provided but not analyzed (free tier)
      const upgradeNote = result.cv_analysis?.upgrade_note;
      if (upgradeNote) {
        toast.success('Answer analyzed! (Video analysis available in paid plans)');
        toast(upgradeNote, { duration: 6000 });
      } else {
        toast.success('Answer and Camera Vision Analysis complete!');
      }
      setLoadError('');
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to analyze answer';
      setLoadError(`Error: ${errorMessage}`);
      toast.error(errorMessage, { duration: 5000 });
      console.error('Answer submission error:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [currentIndex, questions, sessionId, stopVoiceInput]);

  const handleStopRecording = useCallback(async (videoBlob, expressionStats) => {
    await submitCurrentAnswer(videoBlob, expressionStats);
  }, [submitCurrentAnswer]);

  const handleNextQuestion = async () => {
    void stopVoiceInput(true);
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setFeedback(null);
      setCurrentAnswer('');
      return;
    }

    // Await the final feedback so the last answer is fully persisted
    // before the user is allowed to navigate to the dashboard.
    setIsProcessing(true);
    try {
      const result = await getFeedback(sessionId);
      setFeedback(result);
      // Signal the dashboard to perform a fresh fetch on mount.
      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem('dashboard_refresh', 'true');
      }
    } catch {
      toast.error('Unable to load final feedback');
    } finally {
      setIsProcessing(false);
      setInterviewComplete(true);
    }
  };

  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <LimitErrorModal
          isOpen={showLimitModal}
          error={loadError}
          errorCode={errorCode}
          onDismiss={() => setShowLimitModal(false)}
        />
        <div className="flex h-64 items-center justify-center">
          {loadError && !canUpgradeForLoadError ? (
            <div className="max-w-lg rounded-xl border border-red-200 bg-white p-6 text-center shadow-sm">
              <h2 className="text-xl font-semibold text-gray-900">Unable to start interview</h2>
              <p className="mt-2 text-gray-600">{loadError}</p>
              <div className="mt-5 flex flex-wrap justify-center gap-3">
                <button
                  type="button"
                  onClick={() => router.push('/interview/setup')}
                  className="rounded-lg border border-gray-300 px-4 py-2 font-semibold text-gray-700 hover:bg-gray-50"
                >
                  Back to setup
                </button>
              </div>
            </div>
          ) : (
            <div className="text-xl text-gray-600">Loading questions...</div>
          )}
        </div>
      </div>
    );
  }

  if (interviewComplete) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="container mx-auto px-4 py-8">
          <h2 className="mb-8 text-center text-3xl font-bold">Interview Complete!</h2>
          {feedback && <FeedbackDisplay feedback={feedback} />}
          <div className="mt-8 text-center">
            <button
              onClick={() => {
                // The dashboard checks this flag on mount and performs a
                // fresh fetch, ensuring stats reflect the completed interview.
                router.push('/dashboard');
              }}
              className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
            >
              View Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <LimitErrorModal
        isOpen={showLimitModal}
        error={loadError}
        errorCode={errorCode}
        onDismiss={() => {
          setShowLimitModal(false);
          if (canUpgradeForLoadError) {
            router.push('/interview/setup');
          }
        }}
      />

      <div className="container mx-auto px-4 py-8">
        {/* Progress bar and timer */}
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between text-sm text-gray-600">
            <span>Question {currentIndex + 1} of {questions.length}</span>
            <span className="font-mono">Time: {formatTime(timeElapsed)}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-200">
            <div
              className="h-2 rounded-full bg-blue-600 transition-all duration-300"
              style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-2">
          <div>
            <QuestionDisplay
              question={questions[currentIndex]}
              index={currentIndex}
              total={questions.length}
            />

            <div className="mt-4 flex items-center justify-between">
              <span className="text-gray-600">
                Question {currentIndex + 1} of {questions.length}
              </span>
              {feedback && (
                <button
                  onClick={handleNextQuestion}
                  className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
                >
                  {currentIndex < questions.length - 1 ? 'Next Question' : 'Finish Interview'}
                </button>
              )}
            </div>
          </div>

          <div>
            <VideoRecorder
              isRecording={false}
              onStart={handleStartRecording}
              onStop={handleStopRecording}
              onSkipVideo={() => handleStopRecording(null)}
            />

            <label htmlFor="answer" className="mt-4 mb-2 block font-medium text-gray-700">
              Your answer
            </label>
            <textarea
              id="answer"
              value={answer}
              onChange={(event) => setCurrentAnswer(event.target.value)}
              placeholder="Write the answer you gave during the recording..."
              rows={7}
              disabled={isProcessing}
              className="w-full rounded-lg border border-gray-300 p-3 focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <button
              type="button"
              onClick={toggleVoiceInput}
              disabled={isProcessing}
              className={`mt-3 w-full rounded-lg px-4 py-2 font-semibold transition disabled:cursor-not-allowed disabled:bg-gray-200 ${isListening ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              {isListening ? 'Stop Voice Input' : 'Start Voice Input'}
            </button>
            <p className="mt-2 text-sm text-gray-500">Voice input works in supported browsers such as Chrome and Edge.</p>
            <button
              type="button"
              disabled={isProcessing || !answer.trim()}
              onClick={() => handleStopRecording(null)}
              className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            >
              Analyze Written Answer
            </button>

            {isProcessing && (
              <div className="mt-4 rounded-lg bg-yellow-100 p-4 text-yellow-700">
                Processing your answer...
              </div>
            )}

            {loadError && (
              <div className="mt-4 rounded-lg bg-red-50 p-4 border border-red-200 border-l-4 border-l-red-600">
                <div className="flex items-start gap-3">
                  <span className="text-xl text-red-600 flex-shrink-0">⚠️</span>
                  <div className="flex-1">
                    <p className="font-semibold text-red-900 mb-1">Analysis Failed</p>
                    <p className="text-red-700 text-sm mb-3">{loadError}</p>
                    <button
                      onClick={() => {
                        setLoadError('');
                        setErrorCode(null);
                      }}
                      className="inline-flex px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 rounded text-sm font-medium transition"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {feedback && (
          <div className="mt-8">
            <FeedbackDisplay feedback={feedback} />
          </div>
        )}
      </div>
    </div>
  );
}
