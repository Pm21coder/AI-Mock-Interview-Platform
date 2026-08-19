'use client';

export default function Loading() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 h-16 animate-pulse rounded-2xl bg-white/70 shadow-soft dark:bg-slate-900/70" />

        <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10">
          <div className="space-y-5">
            <div className="h-5 w-36 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
            <div className="h-16 w-full animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
            <div className="h-6 w-4/5 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" />
            <div className="flex gap-3 pt-2">
              <div className="h-12 w-44 animate-pulse rounded-2xl bg-gradient-to-r from-blue-200 to-indigo-200 dark:from-blue-900 dark:to-indigo-900" />
              <div className="h-12 w-36 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-24 animate-pulse rounded-2xl bg-white/80 shadow-soft dark:bg-slate-900/80" />
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-white/80 p-4 shadow-soft dark:border-slate-800 dark:bg-slate-900/80">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex gap-2">
                <div className="h-3 w-3 animate-pulse rounded-full bg-rose-300" />
                <div className="h-3 w-3 animate-pulse rounded-full bg-amber-300" />
                <div className="h-3 w-3 animate-pulse rounded-full bg-emerald-300" />
              </div>
              <div className="h-6 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
            </div>
            <div className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
              <div className="h-52 animate-pulse rounded-[1.5rem] bg-slate-200 dark:bg-slate-800" />
              <div className="space-y-4">
                <div className="h-24 animate-pulse rounded-[1.25rem] bg-slate-200 dark:bg-slate-800" />
                <div className="h-24 animate-pulse rounded-[1.25rem] bg-slate-200 dark:bg-slate-800" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
