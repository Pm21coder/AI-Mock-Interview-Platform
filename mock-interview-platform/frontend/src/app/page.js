'use client';

import Link from 'next/link';
import Navigation from '../components/Navigation';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <Navigation />

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Hero Section */}
        <section className="py-8 sm:py-12 md:py-16 lg:py-20">
          <div className="mb-8 text-center sm:mb-12 md:mb-16">
            <h1 className="mb-3 text-3xl font-bold text-gray-900 sm:text-4xl md:text-5xl lg:text-6xl leading-tight">
              AI-Powered Mock Interview Platform
            </h1>
            <p className="mx-auto max-w-2xl px-2 text-base text-gray-600 sm:text-lg md:text-xl">
              Practice your interview skills with real-time feedback using AI, computer vision, and natural language processing.
            </p>
          </div>

          {/* CTA Button - Mobile Friendly */}
          <div className="flex justify-center mb-12 sm:mb-16">
            <Link
              href="/interview/setup"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-semibold text-white transition-all duration-200 hover:bg-blue-700 hover:shadow-lg active:scale-95 sm:px-8 sm:py-4 sm:text-lg"
            >
              Start Practice Interview
              <span className="text-lg">→</span>
            </Link>
          </div>
        </section>

        {/* Feature Cards */}
        <section className="py-8 sm:py-12 md:py-16">
          <div className="grid gap-4 sm:gap-6 md:gap-8 md:grid-cols-3">
            <FeatureCard
              icon="🎯"
              title="Smart Question Generation"
              description="Get personalized interview questions based on your role and experience level."
            />
            <FeatureCard
              icon="👁️"
              title="Computer Vision Analysis"
              description="Real-time analysis of eye contact, facial expressions, and body language."
            />
            <FeatureCard
              icon="🤖"
              title="AI Feedback"
              description="Instant feedback on your answers using advanced NLP and Gemini AI."
            />
          </div>
        </section>

        {/* How It Works */}
        <section className="py-8 sm:py-12 md:py-16">
          <div className="max-w-3xl mx-auto">
            <h2 className="mb-6 text-center text-2xl font-bold text-gray-900 sm:mb-8 md:text-3xl">How It Works</h2>
            <div className="space-y-3 sm:space-y-4">
              <Step
                number={1}
                title="Set Up Your Interview"
                description="Choose your job role, question category, difficulty level, and number of questions."
              />
              <Step
                number={2}
                title="Practice & Record"
                description="Answer questions with video recording and optional voice-to-text transcription."
              />
              <Step
                number={3}
                title="Get AI Feedback"
                description="Receive instant feedback on content, structure, clarity, and confidence."
              />
              <Step
                number={4}
                title="Track Progress"
                description="View your dashboard with interview statistics and recent activity."
              />
            </div>
          </div>
        </section>

        {/* Benefits Section */}
        <section className="py-8 sm:py-12 md:py-16">
          <div className="rounded-lg bg-blue-50 p-6 sm:p-8 md:p-12 border border-blue-200">
            <h2 className="mb-4 text-2xl font-bold text-blue-900 sm:mb-6 md:text-3xl">Why Choose MockInterview AI?</h2>
            <ul className="grid gap-3 sm:gap-4 md:grid-cols-2">
              <li className="flex items-start gap-3">
                <span className="text-xl text-blue-600 flex-shrink-0">✓</span>
                <span className="text-gray-800">Unlimited practice interviews with AI-generated questions</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-xl text-blue-600 flex-shrink-0">✓</span>
                <span className="text-gray-800">Real-time performance metrics and analytics</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-xl text-blue-600 flex-shrink-0">✓</span>
                <span className="text-gray-800">Personalized feedback based on your industry</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-xl text-blue-600 flex-shrink-0">✓</span>
                <span className="text-gray-800">Track progress across multiple interview sessions</span>
              </li>
            </ul>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-12 sm:mt-16 md:mt-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
          <p className="text-center text-sm text-gray-600">
            © {new Date().getFullYear()} MockInterview AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="rounded-lg bg-white p-4 sm:p-6 shadow-lg transition-all duration-200 hover:shadow-xl hover:-translate-y-1">
      <div className="mb-3 text-4xl sm:text-5xl">{icon}</div>
      <h3 className="mb-2 text-lg font-semibold text-gray-900 sm:text-xl">{title}</h3>
      <p className="text-sm text-gray-600 sm:text-base">{description}</p>
    </div>
  );
}

function Step({ number, title, description }) {
  return (
    <div className="flex gap-3 sm:gap-4 rounded-lg bg-white p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex h-8 w-8 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
        <span className="text-sm font-bold sm:text-base">{number}</span>
      </div>
      <div className="min-w-0">
        <h3 className="font-semibold text-gray-900 text-sm sm:text-base">{title}</h3>
        <p className="text-xs text-gray-600 sm:text-sm mt-1">{description}</p>
      </div>
    </div>
  );
}
