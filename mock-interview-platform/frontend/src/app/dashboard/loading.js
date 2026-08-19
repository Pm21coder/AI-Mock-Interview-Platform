export default function DashboardLoading() {
  return (
    <div className="dashboard-shell min-h-screen">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 h-12 w-52 animate-pulse rounded-full bg-white/60 shadow-soft dark:bg-slate-900/70" />
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="h-40 animate-pulse rounded-[1.75rem] bg-white/60 shadow-soft dark:bg-slate-900/70" />
          ))}
        </div>
        <div className="mt-8 h-72 animate-pulse rounded-[1.75rem] bg-white/60 shadow-soft dark:bg-slate-900/70" />
      </div>
    </div>
  );
}
