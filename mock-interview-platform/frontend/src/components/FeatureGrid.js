'use client';

import React, { useState, useEffect, useRef } from 'react';

// FeatureGrid: responsive 3-column grid of feature cards with accessible modal viewer
// Uses local public images. Expects images are available under /images with responsive variants.

const FEATURES = [
  {
    id: 'smart-questions',
    title: 'Smart question generation',
    description: 'Receive role-specific prompts tuned to your experience, target company, and interview level.',
    // base name without extension
    base: '/images/feature-user-1',
  },
  {
    id: 'vision-insights',
    title: 'Computer vision insights',
    description: 'Analyze eye contact, posture, energy, and speaking rhythm for a more realistic practice session.',
    base: '/images/feature-user-2',
  },
  {
    id: 'ai-coaching',
    title: 'AI-powered coaching',
    description: 'Turn your responses into actionable feedback with clearer suggestions and stronger answers.',
    base: '/images/feature-user-3',
  },
];

export default function FeatureGrid() {
  const [open, setOpen] = useState(false);
  const [openSrc, setOpenSrc] = useState(null);
  const modalRef = useRef(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false);
    }
    if (open) document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  useEffect(() => {
    if (open && modalRef.current) modalRef.current.focus();
  }, [open]);

  function openImage(base) {
    // prefer avif/webp large variant if available, fallback to png
    const candidate = base + '-1400.avif';
    setOpenSrc(candidate);
    setOpen(true);
  }

  return (
    <section className="py-8 sm:py-10 lg:py-16">
      <div className="mb-6 text-center sm:mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">Why people choose us</p>
        <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl dark:text-slate-100">Practice smarter, not harder.</h2>
      </div>

      <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <article key={f.id} className="reveal-card feature-card group rounded-[1.75rem] border border-slate-200 card-bg p-5 shadow-soft sm:p-6 dark:border-slate-700">
            <div className="mb-4">
              <button
                type="button"
                onClick={() => openImage(f.base)}
                className="block w-full rounded-lg overflow-hidden focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={`Open ${f.title} image`}
              >
                <picture className="w-full block overflow-hidden rounded-lg" style={{ aspectRatio: '3 / 4', display: 'block' }}>
                  <source srcSet={`${f.base}-480.avif 480w, ${f.base}-768.avif 768w, ${f.base}-1024.avif 1024w, ${f.base}-1400.avif 1400w`} type="image/avif" sizes="(max-width: 640px) 480px, (max-width: 1024px) 768px, 1024px" />
                  <source srcSet={`${f.base}-480.webp 480w, ${f.base}-768.webp 768w, ${f.base}-1024.webp 1024w, ${f.base}-1400.webp 1400w`} type="image/webp" sizes="(max-width: 640px) 480px, (max-width: 1024px) 768px, 1024px" />
                  <img src={`${f.base}-1024.webp`} alt={f.title} className="w-full h-full object-contain object-center" />
                </picture>
              </button>
            </div>

            <h3 className="mb-2 text-xl font-bold card-title">{f.title}</h3>
            <p className="text-sm leading-6 card-text sm:text-base">{f.description}</p>
          </article>
        ))}
      </div>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          role="dialog"
          aria-modal="true"
          onClick={() => setOpen(false)}
        >
          <div className="max-w-[95vw] max-h-[95vh] p-4" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setOpen(false)}
              className="mb-2 rounded bg-white/10 px-3 py-1 text-sm text-white"
              ref={modalRef}
            >
              Close
            </button>
            <picture>
              <source srcSet={`${openSrc}`} type="image/avif" />
              <source srcSet={openSrc.replace('.avif', '.webp')} type="image/webp" />
              <img src={openSrc.replace('.avif', '.png')} alt="Full panel" className="max-h-[85vh] w-auto max-w-full object-contain rounded-lg shadow-lg" />
            </picture>
          </div>
        </div>
      )}
    </section>
  );
}
