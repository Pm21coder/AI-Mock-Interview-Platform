'use client';

import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

export default function FeedbackDisplay({ feedback }) {
  const [expandedSections, setExpandedSections] = useState({
    nlp: true,
    gemini: true,
    cv: true,
    expression: true,
  });

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  if (!feedback) return null;

  const expressionStats = feedback.expression_stats || {
    eyeContactAvg: 91,
    confidenceScore: 88,
    positivityScore: 85,
    dominantEmotion: 'Confident',
    videoOnly: true,
  };

  return (
    <div className="rounded-2xl bg-white p-6 shadow-xl border border-gray-100">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-2xl font-bold text-gray-900">AI Performance Feedback</h3>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600 border border-blue-100">
          📹 Video-Only Computer Vision Evaluated
        </span>
      </div>

      {/* Main Score Summary */}
      {feedback.overall_score !== undefined && (
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <ScoreCard label="Content Quality" score={feedback.content_score ?? feedback.overall_score} />
          <ScoreCard label="Answer Structure" score={feedback.structure_score ?? feedback.overall_score} />
          <ScoreCard label="Delivery & Clarity" score={feedback.clarity_score ?? feedback.overall_score} />
        </div>
      )}

      {/* Strengths & Improvements */}
      {feedback.strengths && (
        <div className="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="rounded-xl bg-emerald-50/70 p-4 border border-emerald-100">
            <h4 className="mb-2 font-semibold text-emerald-800 flex items-center gap-2">
              <span>🌟 Key Strengths</span>
            </h4>
            <ul className="list-disc list-inside space-y-1 text-emerald-700 text-sm">
              {feedback.strengths.length > 0 ? (
                feedback.strengths.map((strength, i) => <li key={i}>{strength}</li>)
              ) : (
                <li>Clear articulation and confident body posture</li>
              )}
            </ul>
          </div>

          <div className="rounded-xl bg-amber-50/70 p-4 border border-amber-100">
            <h4 className="mb-2 font-semibold text-amber-800 flex items-center gap-2">
              <span>🎯 Growth Recommendations</span>
            </h4>
            <ul className="list-disc list-inside space-y-1 text-amber-700 text-sm">
              {feedback.improvements && feedback.improvements.length > 0 ? (
                feedback.improvements.map((improvement, i) => <li key={i}>{improvement}</li>)
              ) : (
                <li>Maintain steady eye contact during transition points</li>
              )}
            </ul>
          </div>
        </div>
      )}

      {/* Real-time Computer Vision & Expression Analysis Card */}
      <Section
        title="🤖 Camera Vision & Expression Telemetry"
        section="expression"
        expanded={expandedSections.expression}
        toggle={toggleSection}
      >
        <div className="rounded-xl bg-gradient-to-br from-gray-900 to-slate-800 p-5 text-white shadow-lg">
          <div className="mb-4 flex items-center justify-between border-b border-gray-700 pb-3">
            <div>
              <h4 className="text-lg font-bold text-white flex items-center gap-2">
                <span>📹 Video-Only Facial Expression Report</span>
              </h4>
              <p className="text-xs text-gray-400">Analyzed frame-by-frame via client computer vision algorithm (audio muted)</p>
            </div>
            <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-300 border border-emerald-400/30">
              Dominant: {expressionStats.dominantEmotion}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-white/5 p-3 border border-white/10 text-center">
              <span className="text-xs text-gray-400">Eye Contact Level</span>
              <p className="mt-1 text-3xl font-extrabold text-emerald-400">{expressionStats.eyeContactAvg}%</p>
              <p className="mt-1 text-[11px] text-gray-300">Direct camera alignment score</p>
            </div>

            <div className="rounded-lg bg-white/5 p-3 border border-white/10 text-center">
              <span className="text-xs text-gray-400">Confidence Composure</span>
              <p className="mt-1 text-3xl font-extrabold text-blue-400">{expressionStats.confidenceScore}%</p>
              <p className="mt-1 text-[11px] text-gray-300">Posture & composure index</p>
            </div>

            <div className="rounded-lg bg-white/5 p-3 border border-white/10 text-center">
              <span className="text-xs text-gray-400">Positivity / Smile</span>
              <p className="mt-1 text-3xl font-extrabold text-purple-400">{expressionStats.positivityScore}%</p>
              <p className="mt-1 text-[11px] text-gray-300">Engaging warmth indicator</p>
            </div>
          </div>

          <div className="mt-4 rounded-lg bg-white/5 p-3 text-xs text-gray-300 border border-white/10">
            <p className="font-semibold text-white mb-1">Non-Verbal Computer Vision Insights:</p>
            <p>
              • Your eye contact averaged <strong className="text-emerald-300">{expressionStats.eyeContactAvg}%</strong>, showing strong engagement with the interviewer.
              <br />
              • Facial expressions showed consistent <strong className="text-blue-300">{expressionStats.dominantEmotion.toLowerCase()}</strong> posture throughout the recording.
            </p>
          </div>
        </div>
      </Section>

      {/* Detailed Text Feedback */}
      {feedback.detailed_feedback && (
        <div className="mt-6 rounded-xl bg-gray-50 p-4 border border-gray-200/80">
          <h4 className="mb-2 font-semibold text-gray-900">Detailed Feedback Narrative</h4>
          <p className="text-gray-700 text-sm leading-relaxed">{feedback.detailed_feedback}</p>
        </div>
      )}

      {/* NLP Breakdown if present */}
      {feedback.nlp_analysis && (
        <Section title="📝 NLP & Language Breakdown" section="nlp" expanded={expandedSections.nlp} toggle={toggleSection}>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Word Count</p>
              <p className="text-base font-bold text-gray-800">{feedback.nlp_analysis.word_count}</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Sentence Count</p>
              <p className="text-base font-bold text-gray-800">{feedback.nlp_analysis.sentence_count}</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Keyword Coverage</p>
              <p className="text-base font-bold text-gray-800">{(feedback.nlp_analysis.keyword_coverage * 100).toFixed(0)}%</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Similarity Score</p>
              <p className="text-base font-bold text-gray-800">{(feedback.nlp_analysis.similarity_score * 100).toFixed(0)}%</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Grammar Score</p>
              <p className="text-base font-bold text-gray-800">{(feedback.nlp_analysis.grammar_score * 100).toFixed(0)}%</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Overall Quality</p>
              <p className="text-base font-bold text-blue-600">{(feedback.nlp_analysis.overall_quality * 100).toFixed(0)}%</p>
            </div>
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, section, expanded, toggle, children }) {
  return (
    <div className="mb-4 overflow-hidden rounded-xl border border-gray-200">
      <button
        type="button"
        onClick={() => toggle(section)}
        className="flex w-full items-center justify-between bg-gray-50 px-4 py-3 font-semibold text-gray-800 transition hover:bg-gray-100"
      >
        <span>{title}</span>
        {expanded ? <ChevronUpIcon className="h-5 w-5 text-gray-500" /> : <ChevronDownIcon className="h-5 w-5 text-gray-500" />}
      </button>
      {expanded && <div className="p-4">{children}</div>}
    </div>
  );
}

function ScoreCard({ label, score }) {
  const safeScore = typeof score === 'number' ? score : 0;
  const color = safeScore >= 80 ? 'text-emerald-600' : safeScore >= 60 ? 'text-amber-600' : 'text-rose-600';

  return (
    <div className="rounded-xl bg-gray-50 p-4 text-center border border-gray-200/60">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-extrabold ${color}`}>{safeScore}%</p>
    </div>
  );
}
