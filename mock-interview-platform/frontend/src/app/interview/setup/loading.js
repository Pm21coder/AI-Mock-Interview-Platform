export default function InterviewSetupLoading() {
  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10 dark:bg-slate-950">
      <div className="mx-auto max-w-5xl space-y-6 rounded-[2rem] border border-slate-200 bg-white/80 p-6 shadow-soft dark:border-slate-800 dark:bg-slate-900/80">
        <div className="h-8 w-52 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
        <div className="h-4 w-80 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
        <div className="grid gap-5 md:grid-cols-2">
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="h-28 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
        <div className="h-14 w-full animate-pulse rounded-2xl bg-gradient-to-r from-blue-200 to-indigo-200 dark:from-blue-900 dark:to-indigo-900" />
      </div>
    </div>
  );
}
