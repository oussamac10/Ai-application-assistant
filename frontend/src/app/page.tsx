"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth, checkDatabaseHealth } from "@/services/api";

type ConnectionStatus = "loading" | "connected" | "unavailable";

export default function Home() {
  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [dbStatus, setDbStatus] = useState<string>("checking");

  useEffect(() => {
    let active = true;

    async function verifyConnections() {
      const isBackendAlive = await checkBackendHealth();

      if (!active) return;

      if (isBackendAlive) {
        setStatus("connected");
        try {
          const databaseHealth = await checkDatabaseHealth();
          if (active) {
            setDbStatus(databaseHealth.database);
          }
        } catch {
          if (active) {
            setDbStatus("unavailable");
          }
        }
      } else {
        setStatus("unavailable");
        setDbStatus("unavailable");
      }
    }

    verifyConnections();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <div className="w-full max-w-md transform transition-all duration-500 hover:scale-[1.01]">
        {/* Glassmorphism Card */}
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl backdrop-blur-xl">
          {/* Decorative glowing gradient sphere */}
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="relative z-10 flex flex-col items-center text-center">
            {/* Logo placeholder icon */}
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-500 shadow-lg shadow-indigo-500/30">
              <svg
                className="h-7 w-7 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>

            {/* Title */}
            <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
              AI Form Assistant
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Phase 1 Monorepo Foundation
            </p>

            <div className="my-8 w-full border-t border-slate-800" />

            {/* Connection Status Section */}
            <div className="w-full space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Backend Status
                </p>
                <div className="mt-2 flex items-center justify-center gap-3">
                  {status === "loading" && (
                    <>
                      <span className="flex h-3 w-3 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
                      </span>
                      <span className="text-base font-medium text-amber-400">
                        Checking backend connection
                      </span>
                    </>
                  )}
                  {status === "connected" && (
                    <>
                      <span className="flex h-3 w-3 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                      </span>
                      <span className="text-base font-medium text-emerald-400">
                        Backend connected
                      </span>
                    </>
                  )}
                  {status === "unavailable" && (
                    <>
                      <span className="flex h-3 w-3 relative">
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
                      </span>
                      <span className="text-base font-medium text-rose-400">
                        Backend unavailable
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Database Status Section */}
              <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Database Connection
                </p>
                <div className="mt-2 flex items-center justify-center gap-3">
                  {dbStatus === "checking" && (
                    <>
                      <span className="h-2 w-2 rounded-full bg-slate-600 animate-pulse" />
                      <span className="text-sm font-medium text-slate-400">
                        Checking database...
                      </span>
                    </>
                  )}
                  {dbStatus === "connected" && (
                    <>
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      <span className="text-sm font-medium text-emerald-400">
                        Connected
                      </span>
                    </>
                  )}
                  {dbStatus === "unavailable" && (
                    <>
                      <span className="h-2 w-2 rounded-full bg-rose-500" />
                      <span className="text-sm font-medium text-rose-400">
                        Unavailable
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
