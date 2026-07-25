"use client";

import React from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";

export default function SessionComplete() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("complete");

  const handleStartNew = () => {
    removeSessionToken(sessionId);
    router.push("/application");
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 text-slate-100">
      <div className="w-full max-w-md">
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-8 text-center shadow-2xl backdrop-blur-xl animate-fade-in">
          {/* Glowing decorator background */}
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative z-10 flex flex-col items-center">
            {/* Green Success Checkmark */}
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-500 shadow-lg shadow-emerald-500/30">
              <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
              {t("title")}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              {t("subtitle")}
            </p>

            <div className="my-6 w-full border-t border-slate-800" />

            <p className="text-sm leading-relaxed text-slate-300 text-left">
              {t("body")}
            </p>

            <button
              onClick={handleStartNew}
              className="mt-8 w-full rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-4 text-base font-bold shadow-lg shadow-indigo-500/20 transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 active:scale-[0.99]"
            >
              {t("startNew")}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
