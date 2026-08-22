'use client'

import React, { useState, useRef, useEffect } from 'react'

// FeatureCards: responsive, accessible, PC + mobile friendly
// - responsive grid (1 / 2 / 3 cols)
// - preview: object-contain on small screens (shows full panel), object-cover on lg (immersive)
// - click to open modal (high-res AVIF/WebP preferred) with focus trap and ESC to close

const FEATURES = [
  {
    id: 'smart-questions',
    title: 'Smart question generation',
    description: 'Receive role-specific prompts tuned to your experience, target company, and interview level.',
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
]

export default function FeatureCards() {
  const [open, setOpen] = useState(false)
  const [openBase, setOpenBase] = useState(null)
  const modalRef = useRef(null)
  const lastActive = useRef(null)

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false)
      if (e.key === 'Tab' && open && modalRef.current) {
        // basic focus trap: keep focus inside modalRef
        const focusable = modalRef.current.querySelectorAll('a,button,input,textarea,select,[tabindex]')
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault(); last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault(); first.focus();
        }
      }
    }
    if (open) document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  useEffect(() => {
    if (open) {
      lastActive.current = document.activeElement
      setTimeout(() => { if (modalRef.current) modalRef.current.focus() }, 0)
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
      if (lastActive.current) lastActive.current.focus()
    }
  }, [open])

  function openImage(base) {
    setOpenBase(base)
    setOpen(true)
  }

  function makeSrcSet(base, ext) {
    return `${base}-480.${ext} 480w, ${base}-768.${ext} 768w, ${base}-1024.${ext} 1024w, ${base}-1400.${ext} 1400w`
  }

  return (
    <section className="py-8 sm:py-10 lg:py-16">
      <div className="mb-6 text-center sm:mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">Why people choose us</p>
        <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl dark:text-slate-100">Practice smarter, not harder.</h2>
      </div>

      <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <article key={f.id} className="reveal-card feature-card group rounded-2xl border border-slate-200 card-bg p-4 shadow-sm dark:border-slate-700">
            <div className="mb-4">
              <button
                type="button"
                onClick={() => openImage(f.base)}
                className="block w-full rounded-lg overflow-hidden focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={`Open ${f.title} image`}
              >
                <div className="w-full block overflow-hidden rounded-lg" style={{ width: '100%', aspectRatio: '4 / 3' }}>
                  <picture className="w-full h-full block">
                    <source srcSet={makeSrcSet(f.base, 'avif')} type="image/avif" sizes="(max-width: 640px) 480px, (max-width: 1024px) 768px, 1024px" />
                    <source srcSet={makeSrcSet(f.base, 'webp')} type="image/webp" sizes="(max-width: 640px) 480px, (max-width: 1024px) 768px, 1024px" />
                    <img src={`${f.base}-1024.webp`} alt={f.title} className="w-full h-full object-contain lg:object-cover object-center" />
                  </picture>
                </div>
              </button>
            </div>

            <h3 className="mb-2 text-xl font-bold card-title">{f.title}</h3>
            <p className="text-sm leading-6 card-text sm:text-base">{f.description}</p>
          </article>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" role="dialog" aria-modal="true" onClick={() => setOpen(false)}>
          <div className="max-w-[95vw] max-h-[95vh] p-4" onClick={(e) => e.stopPropagation()}>
            <div ref={modalRef} tabIndex={-1} className="outline-none">
              <button onClick={() => setOpen(false)} className="mb-2 rounded bg-white/10 px-3 py-1 text-sm text-white">Close</button>
              <picture>
                <source srcSet={`${openBase}-1400.avif`} type="image/avif" />
                <source srcSet={`${openBase}-1400.webp`} type="image/webp" />
                <img src={`${openBase}-1400.png`} alt="Full panel" className="max-h-[85vh] w-auto max-w-full object-contain rounded-lg shadow-lg" />
              </picture>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
