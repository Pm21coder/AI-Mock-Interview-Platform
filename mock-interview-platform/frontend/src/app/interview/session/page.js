'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Navigation from '@/components/Navigation';
import QuestionDisplay from '@/components/QuestionDisplay';
import VideoRecorder from '@/components/VideoRecorder';
import FeedbackDisplay from '@/components/FeedbackDisplay';
import { getQuestions, submitAnswer, getFeedback } from '@/utils/api';

export default function InterviewSessionPage() {
  return (
    <Suspense fallback={<SessionLoading />}>
      <InterviewSessionContentWrapper />
    </Suspense>
  );
}

function InterviewSessionContentWrapper() {
  const router = useRouter();
  const params = useSearchParams();
  
  return <InterviewSessionContent router={router} params={params} />;
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

function InterviewSessionContent({ router, params }) {
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loadError, setLoadError] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const recognitionRef = useRef(null);
  const answerBeforeSpeechRef = useRef('');
  const timerRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return undefined;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join('');
      setAnswer((prevAnswer) => `${answerBeforeSpeechRef.current}${transcript}`.replace(/\s+/g, ' ').trimStart());
    };
    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        toast.error(event.error === 'not-allowed' ? 'Microphone access was denied.' : 'Voice transcription stopped unexpectedly.');
      }
    };
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;

    return () => recognition.abort();
  }, []);

  useEffect(() => {
    const loadQuestions = async () => {
      const jobRole = params.get('job_role') || 'Software Engineer';
      const category = params.get('category') || 'technical';
      const difficulty = params.get('difficulty') || 'medium';
      const numQuestions = Number(params.get('num_questions') || 5);

      try {
        const data = await getQuestions({
          job_role: jobRole,
          category,
          difficulty,
          num_questions: numQuestions,
        });
        setSessionId(data.session_id || 'session_123');
        setQuestions(data.questions || []);
      } catch (error) {
        setLoadError(error.response?.data?.error || 'Failed to load interview questions. Please ensure the backend is running.');
        toast.error('Failed to load interview questions');
      }
    };

    loadQuestions();
  }, [params]);

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
    toast.success('Recording started');
  };

  const toggleVoiceInput = () => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      toast.error('Voice input is not supported by this browser. Try Chrome or Edge.');
      return;
    }

    if (isListening) {
      recognition.stop();
      return;
    }

    answerBeforeSpeechRef.current = answer ? `${answer.trim()} ` : '';
    try {
      recognition.start();
      setIsListening(true);
    } catch {
      toast.error('Voice input is already starting. Please try again in a moment.');
    }
  };

  const handleStopRecording = async (videoBlob) => {
    setIsProcessing(true);

    try {
      const currentQuestion = questions[currentIndex];
      if (!answer.trim()) {
        toast.error('Please write your answer before submitting it.');
        return;
      }

      const result = await submitAnswer({
        question: currentQuestion.question,
        answer,
        expected_answer: currentQuestion.expected_answer,
        session_id: sessionId,
        question_index: currentIndex,
        video_data: Boolean(videoBlob),
      });

      setFeedback(result);
      toast.success('Answer analyzed successfully!');
    } catch (error) {
      toast.error('Failed to analyze answer');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleNextQuestion = async () => {
    if (isListening) recognitionRef.current?.stop();
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setFeedback(null);
      setAnswer('');
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
        <div className="flex h-64 items-center justify-center">
          <div className="max-w-lg text-center text-xl text-gray-600">
            {loadError || 'Loading questions...'}
          </div>
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
            <VideoRecorder isRecording={false} onStart={handleStartRecording} onStop={handleStopRecording} />

            <label htmlFor="answer" className="mt-4 mb-2 block font-medium text-gray-700">
              Your answer
            </label>
            <textarea
              id="answer"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
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