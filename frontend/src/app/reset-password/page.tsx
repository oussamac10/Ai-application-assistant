"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  AuthApiError,
  confirmPasswordReset,
  requestPasswordReset,
} from "@/features/auth/services/authClient";

function ResetPasswordInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const t = useTranslations("auth");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [confirmDone, setConfirmDone] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || submitting) return;
    setSubmitting(true);
    setErrorKey(null);
    try {
      await requestPasswordReset(email.trim());
      setRequestSent(true);
    } catch {
      setErrorKey("error_invalid_email");
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || submitting) return;
    setSubmitting(true);
    setErrorKey(null);
    try {
      await confirmPasswordReset(token, password, passwordConfirmation);
      setConfirmDone(true);
    } catch (err) {
      if (err instanceof AuthApiError && err.errorCode) {
        setErrorKey(`error_${err.errorCode}`);
      } else {
        setErrorKey("error_invalid_or_expired_token");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 py-12 text-slate-900">
      <div className="w-full max-w-md">
        <div className="surface-panel rounded-2xl p-8 sm:p-10 space-y-6 text-start">
          <div className="text-center space-y-1.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {token ? t("resetConfirmTitle") : t("resetRequestTitle")}
            </h1>
            {!token && (
              <p className="text-xs text-slate-600">
                {t("resetRequestSubtitle")}
              </p>
            )}
          </div>

          {errorKey && (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800"
            >
              {t(errorKey)}
            </div>
          )}

          {!token ? (
            requestSent ? (
              <div className="space-y-4">
                <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                  {t("resetRequestSent")}
                </p>
                <Link
                  href="/login"
                  className="btn-secondary inline-flex w-full justify-center py-3 text-sm font-medium"
                >
                  {t("goToLogin")}
                </Link>
              </div>
            ) : (
              <form onSubmit={handleRequestSubmit} className="space-y-5">
                <div className="space-y-1.5">
                  <label
                    htmlFor="reset-email"
                    className="block text-xs font-semibold text-slate-700"
                  >
                    {t("emailLabel")}
                  </label>
                  <input
                    id="reset-email"
                    data-testid="reset-email-input"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input-field"
                  />
                </div>
                <button
                  type="submit"
                  data-testid="reset-request-submit"
                  disabled={submitting}
                  className="btn-primary w-full py-3 text-sm font-semibold"
                >
                  {t("resetRequestButton")}
                </button>
              </form>
            )
          ) : confirmDone ? (
            <div className="space-y-4">
              <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                {t("resetConfirmSuccess")}
              </p>
              <Link
                href="/login"
                className="btn-primary inline-flex w-full justify-center py-3 text-sm font-semibold"
              >
                {t("goToLogin")}
              </Link>
            </div>
          ) : (
            <form onSubmit={handleConfirmSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <label
                  htmlFor="reset-new-password"
                  className="block text-xs font-semibold text-slate-700"
                >
                  {t("passwordLabel")}
                </label>
                <input
                  id="reset-new-password"
                  data-testid="reset-new-password-input"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                />
              </div>
              <div className="space-y-1.5">
                <label
                  htmlFor="reset-confirm-password"
                  className="block text-xs font-semibold text-slate-700"
                >
                  {t("passwordConfirmationLabel")}
                </label>
                <input
                  id="reset-confirm-password"
                  data-testid="reset-confirm-password-input"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={passwordConfirmation}
                  onChange={(e) => setPasswordConfirmation(e.target.value)}
                  className="input-field"
                />
              </div>
              <button
                type="submit"
                data-testid="reset-confirm-submit"
                disabled={submitting}
                className="btn-primary w-full py-3 text-sm font-semibold"
              >
                {t("resetConfirmButton")}
              </button>
            </form>
          )}

          <p className="text-center text-xs text-slate-600">
            <Link
              href="/login"
              className="font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              {t("goToLogin")}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordInner />
    </Suspense>
  );
}
