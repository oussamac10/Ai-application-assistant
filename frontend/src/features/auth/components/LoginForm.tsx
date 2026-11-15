"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "../context/AuthProvider";
import { AuthApiError } from "../services/authClient";
import { Lock, AlertCircle } from "lucide-react";

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
  const searchParams = useSearchParams();
  const redirectParam = searchParams?.get("redirect");
  const redirectUrl = redirectParam && redirectParam.startsWith("/") ? redirectParam : "/applications";

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
      router.push(redirectUrl);
    } catch (err) {
      setErrorKey(errorKeyFor(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center bg-[#0A0E17] px-4 py-12 text-slate-100">
      <div className="w-full max-w-md">
        <div className="surface-panel rounded-2xl border border-white/10 bg-[#0F1522] p-8 sm:p-10 text-slate-100">
          <div className="text-center">
            <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
              <Lock className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              {t("loginTitle")}
            </h1>
            <p className="mt-1.5 text-xs text-slate-400">
              Access your saved form sessions and exported documents
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            {errorKey && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm text-rose-200"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                <span>{t(errorKey)}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-200">
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
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="block text-xs font-semibold text-slate-200">
                  {t("passwordLabel")}
                </label>
                <Link
                  href="/reset-password"
                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors motion-reduce:transition-none"
                >
                  {t("forgotPasswordLink")}
                </Link>
              </div>
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

          <p className="mt-6 text-center text-xs text-slate-400">
            {t("noAccountPrompt")}{" "}
            <Link
              href={redirectParam ? `/register?redirect=${encodeURIComponent(redirectParam)}` : "/register"}
              className="font-semibold text-emerald-400 hover:text-emerald-300 transition-colors motion-reduce:transition-none"
            >
              {t("goToRegister")}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
