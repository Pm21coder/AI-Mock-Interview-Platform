'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import Navigation from '../components/Navigation';

const stats = [
  { label: 'Practice sessions', value: '7,000+' },
  { label: 'Hiring insights', value: '95%' },
  { label: 'Avg. confidence boost', value: '3.4x' },
];

export default function Home() {
  const [theme, setTheme] = useState('light');

  const scrollToHowItWorks = (event) => {
    const target = document.getElementById('how-it-works');
    if (!target) return;

    event.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  useEffect(() => {
    const syncTheme = () => {
      const savedTheme = window.localStorage.getItem('theme-preference') || 'light';
      const nextTheme = ['light', 'dark', 'gradient-pink'].includes(savedTheme) ? savedTheme : 'light';
      setTheme(nextTheme);
      document.documentElement.setAttribute('data-theme', nextTheme);
      document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    };

    syncTheme();
    window.addEventListener('theme-preference-changed', syncTheme);

    return () => {
      window.removeEventListener('theme-preference-changed', syncTheme);
    };
  }, []);

  useEffect(() => {
    const revealElements = document.querySelectorAll('.reveal-card');

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
          }
        });
      },
      { threshold: 0.15 }
    );

    revealElements.forEach((element) => observer.observe(element));

    return () => observer.disconnect();
  }, []);

  const themeOptions = [
    { key: 'light', label: 'Light' },
    { key: 'dark', label: 'Dark' },
    { key: 'gradient-pink', label: 'Gradient Pink' },
  ];

  const applyTheme = (nextTheme) => {
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    window.localStorage.setItem('theme-preference', nextTheme);
    window.dispatchEvent(new CustomEvent('theme-preference-changed'));
  };

  return (
    <div className="page-shell min-h-screen overflow-x-hidden">
      <Navigation />

      <main className="relative mx-auto max-w-7xl px-3 xs:px-4 sm:px-6 lg:px-8">
        <section className="relative py-10 sm:py-14 lg:py-20">
          <div className="grid items-center gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12">
            <div className="relative z-10 text-center lg:text-left">
              <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center lg:justify-start">
                <span className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-blue-700 shadow-sm backdrop-blur sm:text-sm dark:border-blue-500/30 dark:bg-slate-900/70 dark:text-blue-200">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  AI mock interview coach
                </span>

                <div className="flex flex-wrap items-center justify-center gap-2 rounded-full border border-slate-200 bg-white/80 p-1 shadow-sm dark:border-slate-700 dark:bg-slate-900/70">
                  {themeOptions.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => applyTheme(option.key)}
                      className={
                        theme === option.key
                          ? 'rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-white'
                          : 'rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                      }
                      aria-label={`Set theme to ${option.label}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <h1 className="mt-5 text-balance text-4xl font-black leading-[1.05] tracking-tight text-slate-900 xs:text-[2.8rem] sm:text-5xl lg:text-6xl dark:text-slate-100">
                Practice interviews with <span className="gradient-text">real confidence</span>
              </h1>

              <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg lg:mx-0 dark:text-slate-300">
                Simulate real job interviews with AI-generated questions, live feedback, and polished guidance that helps you improve every answer.
              </p>

              <div className="mt-7 flex flex-col items-center gap-3 sm:flex-row lg:justify-start">
                <Link
                  href="/interview/setup"
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-blue-500/25 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30 active:scale-[0.98] sm:w-auto"
                >
                  Start Practice Interview
                  <span aria-hidden="true">→</span>
                </Link>
                <Link
                  href="#how-it-works"
                  onClick={scrollToHowItWorks}
                  className="inline-flex w-full items-center justify-center rounded-2xl border border-slate-200 bg-white/80 px-6 py-3.5 text-base font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:border-slate-300 hover:bg-white sm:w-auto dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  See how it works
                </Link>
              </div>

              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                {stats.map((stat) => (
                  <div key={stat.label} className="rounded-2xl border border-slate-200 bg-white/80 p-3 shadow-soft backdrop-blur-sm dark:border-slate-700 dark:bg-slate-900/70">
                    <div className="text-xl font-black text-slate-900 sm:text-2xl dark:text-slate-100">{stat.value}</div>
                    <div className="mt-1 text-xs text-slate-600 sm:text-sm dark:text-slate-300">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-xl lg:mx-0">
              <div className="hero-glow" aria-hidden="true" />
              <div className="glass-panel relative overflow-hidden rounded-[2rem] border border-white/10 p-3 shadow-[0_30px_80px_rgba(79,70,229,0.25)] sm:p-4">
                <div className="rounded-[1.5rem] bg-[#0b1220] p-4 text-white sm:p-5">
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-rose-400" />
                      <span className="h-3 w-3 rounded-full bg-amber-400" />
                      <span className="h-3 w-3 rounded-full bg-emerald-400" />
                    </div>
                    <div className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-200">
                      Live panel
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
                    <div className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-slate-900 p-3">
                      <Image
                        src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=80"
                        alt="Interview coaching session"
                        width={400}
                        height={260}
                        priority
                        className="h-auto w-full rounded-[1.2rem] object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-tr from-blue-600/35 via-indigo-500/10 to-transparent" />
                      <div className="absolute inset-x-3 bottom-3 rounded-2xl border border-white/10 bg-slate-950/45 p-3 backdrop-blur-md">
                        <p className="text-[10px] uppercase tracking-[0.2em] text-sky-200">Confidence</p>
                        <div className="mt-2 flex items-end justify-between gap-2">
                          <span className="text-3xl font-black text-white">92%</span>
                          <span className="text-xs text-emerald-300">+18% this week</span>
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full w-[92%] rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400" />
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="rounded-[1.25rem] border border-violet-400/30 bg-gradient-to-br from-violet-500/20 to-indigo-500/10 p-4 backdrop-blur">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-violet-200">Focus</p>
                        <div className="mt-3 text-2xl font-black text-white">12 key signals</div>
                        <p className="mt-2 text-xs text-slate-300">Eye contact, clarity, pacing, structure, and confidence.</p>
                      </div>

                      <div className="rounded-[1.25rem] border border-sky-400/30 bg-gradient-to-br from-sky-500/20 to-cyan-500/10 p-4 backdrop-blur">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] uppercase tracking-[0.18em] text-sky-200">Score</span>
                          <span className="rounded-full bg-emerald-400/20 px-2 py-1 text-[10px] font-semibold text-emerald-300">Strong</span>
                        </div>
                        <div className="mt-3 text-2xl font-black text-white">8.7/10</div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full w-[87%] rounded-full bg-gradient-to-r from-sky-400 to-cyan-300" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="float-badge left-[-0.75rem] top-12 hidden sm:flex">AI feedback</div>
              <div className="float-badge right-[-0.75rem] bottom-10 hidden sm:flex">Role fit: 96%</div>
            </div>
          </div>
        </section>

        <section className="py-8 sm:py-10 lg:py-16">
          <div className="mb-6 text-center sm:mb-8">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">Why people choose us</p>
            <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl dark:text-slate-100">Practice smarter, not harder.</h2>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            <FeatureCard
              iconSrc="/images/feature-1.png"
              title="Smart question generation"
              description="Receive role-specific prompts tuned to your experience, target company, and interview level."
            />
            <FeatureCard
              iconSrc="/images/feature-2.png"
              title="Computer vision insights"
              description="Analyze eye contact, posture, energy, and speaking rhythm for a more realistic practice session."
            />
            <FeatureCard
              iconSrc="/images/feature-3.png"
              title="AI-powered coaching"
              description="Turn your responses into actionable feedback with clearer suggestions and stronger answers."
            />
          </div>
        </section>

        <section id="how-it-works" className="py-8 sm:py-10 lg:py-16">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-violet-600">How it works</p>
            <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl">A guided path to interview confidence</h2>
          </div>

          <div className="mt-8 space-y-4">
            <Step
              number={1}
              title="Set up your interview"
              description="Pick your job role, focus area, difficulty, and ideal number of questions to tailor the mock interview."
            />
            <Step
              number={2}
              title="Practice in a realistic flow"
              description="Answer questions while recording video or voice, then get comfortable with natural interview pacing."
            />
            <Step
              number={3}
              title="Receive instant AI feedback"
              description="Review structured guidance on clarity, content quality, delivery, and the key strengths you can improve."
            />
            <Step
              number={4}
              title="Track your progress"
              description="Use session analytics to monitor improvement, measure growth, and sharpen your interview preparation."
            />
          </div>
        </section>

        <section className="py-8 sm:py-10 lg:py-16">
          <div className="rounded-[2rem] border border-blue-100 section-light-bg p-6 shadow-soft sm:p-8 lg:p-12 dark:border-slate-700">
            <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">Why choose us</p>
                <h2 className="mt-3 text-3xl font-black card-title sm:text-4xl">Interview prep that feels like your real next step.</h2>
              </div>

              <ul className="space-y-4">
                {[
                  'Unlimited AI interview practice for every role and stage.',
                  'Real-time insight into confidence, clarity, and communication.',
                  'Personalized guidance that helps you improve with each session.',
                  'Clean mobile-friendly experience built for day-to-day practice.',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 rounded-2xl card-bg p-3 shadow-sm dark:border dark:border-slate-700">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400">✓</span>
                    <span className="text-sm leading-6 card-text sm:text-base">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-12 border-t border-slate-200 bg-white/80 backdrop-blur-sm sm:mt-16 dark:border-slate-700 dark:bg-slate-950/70">
        <div className="mx-auto max-w-7xl px-3 py-8 text-center text-sm text-slate-600 xs:px-4 sm:px-6 lg:px-8 dark:text-slate-300">
          © {new Date().getFullYear()} MockInterview AI. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ iconSrc, title, description }) {
  return (
    <div className="reveal-card feature-card group rounded-[1.75rem] border border-slate-200 card-bg p-5 shadow-soft sm:p-6 dark:border-slate-700">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-violet-500 text-3xl shadow-lg shadow-blue-500/20 transition-transform duration-200 group-hover:scale-105 overflow-hidden">
        <Image
          src={iconSrc}
          alt={title}
          width={64}
          height={64}
          className="h-full w-full rounded-lg object-cover"
        />
      </div>
      <h3 className="mb-2 text-xl font-bold card-title">{title}</h3>
      <p className="text-sm leading-6 card-text sm:text-base">{description}</p>
    </div>
  );
}

function Step({ number, title, description }) {
  return (
    <div className="reveal-card flex gap-3 rounded-[1.5rem] border border-slate-200 card-bg p-4 shadow-soft transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md sm:gap-4 sm:p-5 dark:border-slate-700">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-violet-600 text-sm font-black text-white shadow-lg shadow-blue-500/20 sm:h-12 sm:w-12 sm:text-base">
        {number}
      </div>
      <div className="min-w-0">
        <h3 className="text-base font-bold card-title sm:text-lg">{title}</h3>
        <p className="mt-1 text-sm leading-6 card-text sm:text-base">{description}</p>
      </div>
    </div>
  );
}
