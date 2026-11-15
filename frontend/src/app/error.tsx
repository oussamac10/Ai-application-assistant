"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RotateCcw, Home, ShieldAlert } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log unexpected errors for client-side auditing without leaking PII
    if (process.env.NODE_ENV !== "production") {
      // eslint-disable-next-line no-console
      console.error("App Router Error Boundary caught error:", error);
    }
  }, [error]);

  return (
    <main
      className="min-h-[calc(100vh-10rem)] flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#0A0E17] text-slate-100"
      role="alert"
      aria-live="assertive"
    >
      <div className="w-full max-w-lg text-center animate-in fade-in zoom-in-95 duration-150">
        <div className="surface-card rounded-3xl border border-white/10 bg-[#0F1522] p-8 sm:p-10 shadow-xl">
          {/* Status Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 mb-6">
            <ShieldAlert className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Service Alert</span>
          </div>

          {/* Central Civic Icon */}
          <div className="mx-auto w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-6 shadow-2xs">
            <AlertTriangle className="w-8 h-8" aria-hidden="true" />
          </div>

          {/* Heading */}
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-3">
            An unexpected error occurred
          </h1>

          {/* Body Copy */}
          <p className="text-sm sm:text-base text-slate-400 leading-relaxed max-w-md mx-auto mb-6">
            We encountered an unexpected issue while rendering this page. Any saved form answers or session progress are safely preserved.
          </p>

          {/* Correlation / Digest identifier if present */}
          {error.digest && (
            <div className="mb-6 inline-flex items-center gap-2 px-3 py-1.5 bg-[#0A0E17] border border-white/10 rounded-xl text-xs font-mono text-slate-300">
              <span className="font-semibold text-slate-200">Reference:</span>
              <span>{error.digest}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => reset()}
              className="btn-primary w-full sm:w-auto"
            >
              <RotateCcw className="w-4 h-4" aria-hidden="true" />
              <span>Try again</span>
            </button>

            <Link
              href="/"
              className="btn-secondary w-full sm:w-auto"
            >
              <Home className="w-4 h-4" aria-hidden="true" />
              <span>Return to home</span>
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
