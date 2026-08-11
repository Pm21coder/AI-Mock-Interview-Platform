import Link from 'next/link';
import Navigation from '@/components/Navigation';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="container mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="mb-16 text-center">
          <h1 className="mb-4 text-4xl font-bold text-gray-900 md:text-5xl">
            AI-Powered Mock Interview Platform
          </h1>
          <p className="mx-auto max-w-2xl text-xl text-gray-600">
            Practice your interview skills with real-time feedback using AI, computer vision, and natural language processing.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-3">
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

        {/* CTA */}
        <div className="mt-16 text-center">
          <Link
            href="/interview/setup"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-8 py-3 text-lg font-semibold text-white transition-all duration-200 hover:bg-blue-700 hover:shadow-lg"
          >
            Start Practice Interview
          </Link>
        </div>

        {/* How It Works */}
        <div className="mt-16 max-w-3xl">
          <h2 className="mb-6 text-center text-2xl font-bold text-gray-900">How It Works</h2>
          <div className="space-y-4">
            <Step number={1} title="Set Up Your Interview" description="Choose your job role, question category, difficulty level, and number of questions." />
            <Step number={2} title="Practice & Record" description="Answer questions with video recording and optional voice-to-text transcription." />
            <Step number={3} title="Get AI Feedback" description="Receive instant feedback on content, structure, clarity, and confidence." />
            <Step number={4} title="Track Progress" description="View your dashboard with interview statistics and recent activity." />
          </div>
        </div>
      </main>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-lg transition-all duration-200 hover:shadow-xl">
      <div className="mb-4 text-4xl">{icon}</div>
      <h3 className="mb-2 text-xl font-semibold text-gray-900">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

function Step({ number, title, description }) {
  return (
    <div className="flex items-start gap-4 rounded-lg bg-white p-4 shadow-sm">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
        <span className="text-sm font-bold">{number}</span>
      </div>
      <div>
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </div>
  );
}
