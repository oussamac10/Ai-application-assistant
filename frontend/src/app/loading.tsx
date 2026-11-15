export default function Loading() {
  return (
    <div className="relative min-h-[calc(100vh-10rem)] w-full bg-[#0A0E17] text-slate-100" role="status" aria-busy="true">
      {/* Top Indeterminate Progress Bar */}
      <div
        className="fixed top-0 left-0 right-0 z-50 h-1 bg-emerald-950/60 overflow-hidden"
        aria-hidden="true"
      >
        <div className="h-full w-full bg-gradient-to-r from-transparent via-emerald-500 to-transparent animate-shimmer" />
      </div>

      <span className="sr-only">Loading page content...</span>

      {/* Surface Skeleton Container */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8 animate-fade-in">
        {/* Header Breadcrumb & Title Skeleton */}
        <div className="space-y-3">
          <div className="h-4 w-28 bg-slate-800/80 rounded-full animate-pulse" />
          <div className="h-8 w-64 sm:w-80 bg-slate-800 rounded-xl animate-pulse" />
          <div className="h-4 w-96 max-w-full bg-slate-800/50 rounded-lg animate-pulse" />
        </div>

        {/* Content Surface Grid Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content Skeleton Panel */}
          <div className="lg:col-span-2 surface-card rounded-3xl p-6 sm:p-8 space-y-5 border border-white/10 bg-[#0F1522] shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="h-6 w-44 bg-slate-800 rounded-lg animate-pulse" />
              <div className="h-5 w-20 bg-slate-800/70 rounded-full animate-pulse" />
            </div>

            <div className="space-y-4 pt-2">
              <div className="h-12 w-full bg-slate-800/60 rounded-xl animate-pulse" />
              <div className="h-12 w-full bg-slate-800/60 rounded-xl animate-pulse" />
              <div className="h-28 w-full bg-slate-900/80 rounded-2xl animate-pulse" />
            </div>

            <div className="pt-4 flex items-center justify-end gap-3">
              <div className="h-10 w-24 bg-slate-800/70 rounded-xl animate-pulse" />
              <div className="h-10 w-32 bg-emerald-500/20 border border-emerald-500/30 rounded-xl animate-pulse" />
            </div>
          </div>

          {/* Sidebar / Auxiliary Card Skeleton */}
          <div className="surface-card rounded-3xl p-6 space-y-5 border border-white/10 bg-[#0F1522] shadow-xs">
            <div className="h-5 w-32 bg-slate-800 rounded-lg animate-pulse" />
            <div className="h-24 w-full bg-[#0A0E17] rounded-2xl border border-dashed border-white/10 animate-pulse" />
            <div className="space-y-2 pt-2">
              <div className="h-3.5 w-full bg-slate-800/60 rounded-md animate-pulse" />
              <div className="h-3.5 w-5/6 bg-slate-800/60 rounded-md animate-pulse" />
              <div className="h-3.5 w-4/6 bg-slate-800/60 rounded-md animate-pulse" />
            </div>
            <div className="pt-2">
              <div className="h-10 w-full bg-slate-800/70 rounded-xl animate-pulse" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
