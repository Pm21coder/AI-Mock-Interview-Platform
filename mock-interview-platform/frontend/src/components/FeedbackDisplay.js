'use client';

import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

export default function FeedbackDisplay({ feedback }) {
  const [expandedSections, setExpandedSections] = useState({
    nlp: true,
    gemini: true,
    cv: false,
  });

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  if (!feedback) return null;

  if (feedback.overall_score !== undefined) {
    return (
      <div className="rounded-lg bg-white p-6 shadow-lg">
        <h3 className="mb-4 text-xl font-bold">Interview Feedback</h3>

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <ScoreCard label="Content" score={feedback.content_score ?? feedback.overall_score} />
          <ScoreCard label="Structure" score={feedback.structure_score ?? feedback.overall_score} />
          <ScoreCard label="Clarity" score={feedback.clarity_score ?? feedback.overall_score} />
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="rounded-lg bg-green-50 p-4">
            <h4 className="mb-2 font-semibold text-green-800">Strengths</h4>
            <ul className="list-disc list-inside space-y-1 text-green-700">
              {(feedback.strengths && feedback.strengths.length > 0) ? feedback.strengths.map((strength, i) => <li key={i}>{strength}</li>) : <li>No strengths listed</li>}
            </ul>
          </div>

          <div className="rounded-lg bg-yellow-50 p-4">
            <h4 className="mb-2 font-semibold text-yellow-800">Areas for Improvement</h4>
            <ul className="list-disc list-inside space-y-1 text-yellow-700">
              {(feedback.improvements && feedback.improvements.length > 0) ? feedback.improvements.map((improvement, i) => <li key={i}>{improvement}</li>) : <li>No improvements listed</li>}
            </ul>
          </div>
        </div>

        {feedback.detailed_feedback && (
          <div className="mt-6 rounded-lg bg-gray-50 p-4">
            <h4 className="mb-2 font-semibold">Detailed Feedback</h4>
            <p className="text-gray-700">{feedback.detailed_feedback}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white p-6 shadow-lg">
      <h3 className="mb-4 text-xl font-bold">Combined Analysis</h3>

      {feedback.nlp_analysis && (
        <Section title="NLP Analysis" section="nlp" expanded={expandedSections.nlp} toggle={toggleSection}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Word Count</p>
              <p className="font-semibold">{feedback.nlp_analysis.word_count}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Sentences</p>
              <p className="font-semibold">{feedback.nlp_analysis.sentence_count}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Keyword Coverage</p>
              <p className="font-semibold">{(feedback.nlp_analysis.keyword_coverage * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Similarity Score</p>
              <p className="font-semibold">{(feedback.nlp_analysis.similarity_score * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Grammar Score</p>
              <p className="font-semibold">{(feedback.nlp_analysis.grammar_score * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Overall Quality</p>
              <p className="font-semibold">{(feedback.nlp_analysis.overall_quality * 100).toFixed(0)}%</p>
            </div>
          </div>
        </Section>
      )}

      {feedback.gemini_feedback && (
        <Section title="AI Analysis (Gemini)" section="gemini" expanded={expandedSections.gemini} toggle={toggleSection}>
          <div className="grid grid-cols-3 gap-4">
            <ScoreCard label="Content" score={feedback.gemini_feedback.content_score} />
            <ScoreCard label="Structure" score={feedback.gemini_feedback.structure_score} />
            <ScoreCard label="Clarity" score={feedback.gemini_feedback.clarity_score} />
          </div>
        </Section>
      )}

      {feedback.cv_analysis && (
        <Section title="Visual Analysis" section="cv" expanded={expandedSections.cv} toggle={toggleSection}>
          <div className="space-y-2">
            <p>
              <span className="font-medium">Confidence:</span>{' '}
              {(feedback.cv_analysis.average_confidence * 100).toFixed(0)}%
            </p>
            <p>
              <span className="font-medium">Assessment:</span>{' '}
              {feedback.cv_analysis.overall_assessment}
            </p>
            <p className="text-sm text-gray-600">Frames analyzed: {feedback.cv_analysis.total_frames_analyzed}</p>
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, section, expanded, toggle, children }) {
  return (
    <div className="mb-4 overflow-hidden rounded-lg border">
      <button
        onClick={() => toggle(section)}
        className="flex w-full items-center justify-between bg-gray-50 px-4 py-3 transition hover:bg-gray-100"
      >
        <span className="font-medium">{title}</span>
        {expanded ? <ChevronUpIcon className="h-5 w-5" /> : <ChevronDownIcon className="h-5 w-5" />}
      </button>
      {expanded && <div className="p-4">{children}</div>}
    </div>
  );
}

function ScoreCard({ label, score }) {
  const safeScore = typeof score === 'number' ? score : 0;
  const color = safeScore >= 80 ? 'text-green-600' : safeScore >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="text-center">
      <p className="text-sm text-gray-600">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{safeScore}%</p>
    </div>
  );
}
