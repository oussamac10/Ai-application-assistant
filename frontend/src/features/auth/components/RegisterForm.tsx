"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "../context/AuthProvider";
import { AuthApiError } from "../services/authClient";

const KNOWN_ERROR_CODES = new Set(["invalid_email", "password_mismatch", "weak_password"]);

function errorKeyFor(err: unknown): string {
  if (err instanceof AuthApiError && err.errorCode && KNOWN_ERROR_CODES.has(err.errorCode)) {
    return `error_${err.errorCode}`;
  }
  return "error_generic_register_failed";
}

export default function RegisterForm() {
  const t = useTranslations("auth");
  const router = useRouter();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setErrorKey(null);
    try {
      await register(email, password, passwordConfirmation);
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
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {t("registerTitle")}
            </h1>
            <p className="mt-1.5 text-xs text-slate-600">
              Create your account to claim and manage applications
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
              <label htmlFor="register-email" className="block text-xs font-semibold text-slate-700">
                {t("emailLabel")}
              </label>
              <input
                id="register-email"
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
              <label htmlFor="register-password" className="block text-xs font-semibold text-slate-700">
                {t("passwordLabel")}
              </label>
              <input
                id="register-password"
                type="password"
                required
                minLength={10}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                suppressHydrationWarning
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="register-password-confirmation"
                className="block text-xs font-semibold text-slate-700"
              >
                {t("passwordConfirmationLabel")}
              </label>
              <input
                id="register-password-confirmation"
                type="password"
                required
                minLength={10}
                autoComplete="new-password"
                value={passwordConfirmation}
                onChange={(e) => setPasswordConfirmation(e.target.value)}
                className="input-field"
                suppressHydrationWarning
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="btn-primary w-full py-3 text-sm font-semibold"
            >
              {submitting ? t("registerSubmitting") : t("registerButton")}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-slate-600">
            {t("haveAccountPrompt")}{" "}
            <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-800 transition-colors">
              {t("goToLogin")}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
