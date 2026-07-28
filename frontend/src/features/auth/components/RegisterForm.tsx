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
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 py-12 text-slate-100">
      <div className="w-full max-w-md">
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl backdrop-blur-xl">
          <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-center text-3xl font-extrabold tracking-tight text-transparent">
            {t("registerTitle")}
          </h1>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {errorKey && (
              <div
                role="alert"
                className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300"
              >
                {t(errorKey)}
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="register-email" className="block text-sm font-semibold text-slate-300">
                {t("emailLabel")}
              </label>
              <input
                id="register-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                // See LoginForm.tsx — password-manager extensions inject
                // attributes onto credential inputs after server render.
                suppressHydrationWarning
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="register-password" className="block text-sm font-semibold text-slate-300">
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
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                suppressHydrationWarning
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="register-password-confirmation"
                className="block text-sm font-semibold text-slate-300"
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
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                suppressHydrationWarning
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-base font-bold shadow-lg shadow-indigo-500/20 transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-40"
            >
              {submitting ? t("registerSubmitting") : t("registerButton")}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            {t("haveAccountPrompt")}{" "}
            <Link href="/login" className="font-semibold text-indigo-400 hover:text-indigo-300">
              {t("goToLogin")}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
