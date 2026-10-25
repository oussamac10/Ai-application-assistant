"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "../context/AuthProvider";
import { AuthApiError } from "../services/authClient";

function errorKeyFor(err: unknown): string {
  if (err instanceof AuthApiError) {
    if (err.errorCode) return `error_${err.errorCode}`;
    if (err.status === 401) return "error_generic_login_failed";
  }
  return "error_generic_login_failed";
}

export default function LoginForm() {
  const t = useTranslations("auth");
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setErrorKey(null);
    try {
      await login(email, password);
      router.push("/applications");
    } catch (err) {
      setErrorKey(errorKeyFor(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 py-12 text-slate-900">
      <div className="w-full max-w-md">
        <div className="surface-panel rounded-2xl p-8 sm:p-10">
          <div className="text-center">
            <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {t("loginTitle")}
            </h1>
            <p className="mt-1.5 text-xs text-slate-600">
              Access your saved form sessions and exported documents
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            {errorKey && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800"
              >
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>{t(errorKey)}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-700">
                {t("emailLabel")}
              </label>
              <input
                id="login-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                suppressHydrationWarning
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="login-password" className="block text-xs font-semibold text-slate-700">
                {t("passwordLabel")}
              </label>
              <input
                id="login-password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                suppressHydrationWarning
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="btn-primary w-full py-3 text-sm font-semibold"
            >
              {submitting ? t("loginSubmitting") : t("loginButton")}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-slate-600">
            {t("noAccountPrompt")}{" "}
            <Link href="/register" className="font-semibold text-indigo-600 hover:text-indigo-800 transition-colors">
              {t("goToRegister")}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
