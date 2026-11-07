"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Briefcase, Landmark, User, UserPlus, AlertCircle } from "lucide-react";
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
  const searchParams = useSearchParams();
  const redirectParam = searchParams?.get("redirect");
  const redirectUrl = redirectParam && redirectParam.startsWith("/") ? redirectParam : null;

  const { register } = useAuth();

  const [accountType, setAccountType] = useState<"individual" | "government" | "business">("individual");
  const [organizationName, setOrganizationName] = useState("");
  const [officialWebsiteUrl, setOfficialWebsiteUrl] = useState("");
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
      await register(email, password, passwordConfirmation, {
        accountType,
        organizationName: organizationName.trim() || undefined,
        officialWebsiteUrl: officialWebsiteUrl.trim() || undefined,
      });
      if (redirectUrl) {
        router.push(redirectUrl);
      } else if (accountType === "individual") {
        router.push("/applications");
      } else {
        router.push("/portal");
      }
    } catch (err) {
      setErrorKey(errorKeyFor(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 py-12 text-slate-900">
      <div className="w-full max-w-xl">
        <div className="surface-panel rounded-2xl p-8 sm:p-10 shadow-xs border border-slate-200/80 bg-white">
          <div className="text-center">
            <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
              <UserPlus className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {t("registerTitle")}
            </h1>
            <p className="mt-1.5 text-xs text-slate-600">
              Create your account to complete forms or publish verified multilingual services
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            {errorKey && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                <span>{t(errorKey)}</span>
              </div>
            )}

            {/* Account Type Selector */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Select Account Type
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <button
                  type="button"
                  onClick={() => setAccountType("individual")}
                  className={`flex flex-col items-start p-3 rounded-xl border text-start transition-all ${
                    accountType === "individual"
                      ? "border-indigo-600 bg-indigo-50/70 ring-2 ring-indigo-600/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900">
                    <User className={`w-4 h-4 ${accountType === "individual" ? "text-indigo-600" : "text-slate-500"}`} />
                    Citizen
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500 leading-tight">
                    Individual citizen. Complete forms for free.
                  </p>
                  <span className="mt-2 text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                    100% Free
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setAccountType("government")}
                  className={`flex flex-col items-start p-3 rounded-xl border text-start transition-all ${
                    accountType === "government"
                      ? "border-indigo-600 bg-indigo-50/70 ring-2 ring-indigo-600/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900">
                    <Landmark className={`w-4 h-4 ${accountType === "government" ? "text-indigo-600" : "text-slate-500"}`} />
                    Government
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500 leading-tight">
                    Bürgeramt, Ausländerbehörde, Universities.
                  </p>
                  <span className="mt-2 text-[10px] font-semibold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                    Official Portal
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setAccountType("business")}
                  className={`flex flex-col items-start p-3 rounded-xl border text-start transition-all ${
                    accountType === "business"
                      ? "border-indigo-600 bg-indigo-50/70 ring-2 ring-indigo-600/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900">
                    <Briefcase className={`w-4 h-4 ${accountType === "business" ? "text-indigo-600" : "text-slate-500"}`} />
                    Business
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500 leading-tight">
                    Relocation firms, law practices, HR teams.
                  </p>
                  <span className="mt-2 text-[10px] font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                    Client Pipeline
                  </span>
                </button>
              </div>
            </div>

            {/* Organization Specific Fields */}
            {accountType !== "individual" && (
              <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 space-y-4">
                <div className="space-y-1.5">
                  <label htmlFor="organization-name" className="block text-xs font-semibold text-slate-700">
                    {accountType === "government" ? "Authority / Municipality Name" : "Company / Firm Name"}
                    <span className="text-rose-500 ms-1">*</span>
                  </label>
                  <input
                    id="organization-name"
                    type="text"
                    required
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder={
                      accountType === "government"
                        ? "e.g. Stadtverwaltung Freiburg"
                        : "e.g. ReloCare Immigration GmbH"
                    }
                    className="input-field bg-white"
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="official-website" className="block text-xs font-semibold text-slate-700">
                    {accountType === "government" ? "Official Website" : "Company Website"}
                    <span className="text-slate-400 font-normal ms-1">(optional)</span>
                  </label>
                  <input
                    id="official-website"
                    type="url"
                    value={officialWebsiteUrl}
                    onChange={(e) => setOfficialWebsiteUrl(e.target.value)}
                    placeholder="https://..."
                    className="input-field bg-white"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="register-email" className="block text-xs font-semibold text-slate-700">
                {accountType === "government"
                  ? "Official Authority Email"
                  : accountType === "business"
                  ? "Business Email"
                  : t("emailLabel")}
              </label>
              <input
                id="register-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={
                  accountType === "government"
                    ? "name@rathaus.freiburg.de"
                    : accountType === "business"
                    ? "partner@relocare.de"
                    : "name@example.com"
                }
                className="input-field"
                suppressHydrationWarning
              />
              {accountType === "government" && (
                <p className="text-[11px] text-slate-500">
                  Using an official municipal or institutional email expedites official verification.
                </p>
              )}
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
              {submitting
                ? t("registerSubmitting")
                : accountType === "government"
                ? "Register Official Government Account"
                : accountType === "business"
                ? "Register Business Account"
                : t("registerButton")}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-slate-600">
            {t("haveAccountPrompt")}{" "}
            <Link
              href={redirectParam ? `/login?redirect=${encodeURIComponent(redirectParam)}` : "/login"}
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
