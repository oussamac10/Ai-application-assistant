import Link from "next/link";
import { FileQuestion, Home, FileText, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <main
      className="min-h-[calc(100vh-10rem)] flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#0A0E17] text-slate-100"
      role="main"
    >
      <div className="w-full max-w-lg text-center animate-in fade-in zoom-in-95 duration-150">
        <div className="surface-card rounded-3xl border border-white/10 bg-[#0F1522] p-8 sm:p-10 shadow-xl">
          {/* Status badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-6">
            <FileQuestion className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Error 404</span>
          </div>

          {/* Central Civic Icon */}
          <div className="mx-auto w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-6 shadow-2xs">
            <FileQuestion className="w-8 h-8" aria-hidden="true" />
          </div>

          {/* Heading */}
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-3">
            Document or page not found
          </h1>

          {/* Body Copy */}
          <p className="text-sm sm:text-base text-slate-400 leading-relaxed max-w-md mx-auto mb-8">
            The form, application, or administrative page you were looking for doesn&apos;t exist or may have been moved. Check the web address or choose an option below to continue.
          </p>

          {/* Primary & Secondary Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/"
              className="btn-primary w-full sm:w-auto"
            >
              <Home className="w-4 h-4" aria-hidden="true" />
              <span>Return to home</span>
            </Link>

            <Link
              href="/applications"
              className="btn-secondary w-full sm:w-auto"
            >
              <FileText className="w-4 h-4" aria-hidden="true" />
              <span>My applications</span>
            </Link>
          </div>

          {/* Safe Navigation Hint */}
          <div className="mt-8 pt-6 border-t border-white/[0.08] flex items-center justify-center">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Back to start</span>
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
