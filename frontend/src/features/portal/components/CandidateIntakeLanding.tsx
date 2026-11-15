"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  AlertCircle,
  Check,
  ClipboardCheck,
  Globe,
  KeyRound,
  Landmark,
  Loader2,
  Lock,
  Mail,
  MapPin,
  Phone,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  inspectCandidateInvite,
  sendCandidateInviteOtp,
  verifyCandidateInviteOtp,
} from "../services/portalClient";
import { CandidateIntakeInfo, CandidateInviteInspectInfo } from "../types";
import {
  applyBrandThemeToDocument,
  getContrastTextColor,
  hydratePersistedBrandTheme,
} from "../utils/theme";

interface CandidateIntakeLandingProps {
  token: string;
}

function resolveSafeHexColor(color?: string | null): string | null {
  if (!color) return null;
  const trimmed = color.trim();
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(trimmed) ? trimmed : null;
}

function resolveSafeHttpUrl(url?: string | null): string | null {
  if (!url) return null;
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return null;
}

export function CandidateIntakeLanding({ token }: CandidateIntakeLandingProps) {
  const t = useTranslations("portal");
  const router = useRouter();
  const { setLocale } = useLanguage();
  const setLocaleRef = useRef(setLocale);
  setLocaleRef.current = setLocale;

  const [inspectInfo, setInspectInfo] =
    useState<CandidateInviteInspectInfo | null>(null);
  const [unlockedIntake, setUnlockedIntake] =
    useState<CandidateIntakeInfo | null>(null);
  const [selectedLang, setSelectedLang] = useState("en");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Step 2-factor email OTP verification state
  const [otpSent, setOtpSent] = useState(false);
  const [maskedEmail, setMaskedEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [sendingOtp, setSendingOtp] = useState(false);
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [otpInfoMsg, setOtpInfoMsg] = useState<string | null>(null);

  // Pre-form supporting document preparation state
  const [checkedDocs, setCheckedDocs] = useState<Record<number, boolean>>({});
  const [logoLoadError, setLogoLoadError] = useState(false);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setLogoLoadError(false);

    inspectCandidateInvite(token)
      .then((data) => {
        if (cancelled) return;
        setInspectInfo(data);
        setMaskedEmail(data.masked_email);
        if (data.user_language) {
          setSelectedLang(data.user_language);
          setLocaleRef.current(data.user_language);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Invalid or expired candidate invite link."
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const orgThemeConfig =
    unlockedIntake?.organization?.ui_theme_config ??
    inspectInfo?.organization?.ui_theme_config;

  useEffect(() => {
    if (!orgThemeConfig) return;
    applyBrandThemeToDocument(orgThemeConfig, { persist: false });
    return () => {
      hydratePersistedBrandTheme();
    };
  }, [orgThemeConfig]);

  const handleSendOtp = async () => {
    if (sendingOtp) return;
    setSendingOtp(true);
    setOtpError(null);
    setOtpInfoMsg(null);
    try {
      const res = await sendCandidateInviteOtp(token);
      setOtpSent(true);
      setMaskedEmail(res.masked_email);
      const minutes = Math.max(1, Math.round((res.expires_in_seconds || 600) / 60));
      setOtpInfoMsg(
        `Verification code sent. It expires in ${minutes} minutes.`
      );
    } catch (err) {
      setOtpError(
        err instanceof Error
          ? err.message
          : "Failed to send verification code. Please try again."
      );
    } finally {
      setSendingOtp(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = otpCode.replace(/\D/g, "").slice(0, 6);
    if (cleaned.length !== 6) {
      setOtpError("Please enter the 6-digit verification code sent to your email.");
      return;
    }
    if (verifyingOtp) return;

    setVerifyingOtp(true);
    setOtpError(null);
    try {
      const unlocked = await verifyCandidateInviteOtp(token, cleaned);
      setUnlockedIntake(unlocked);
      if (unlocked.user_language) {
        setSelectedLang(unlocked.user_language);
        setLocale(unlocked.user_language);
      }
    } catch (err) {
      setOtpError(
        err instanceof Error
          ? err.message
          : "Invalid or expired verification code. Please try again."
      );
    } finally {
      setVerifyingOtp(false);
    }
  };

  const handleSelectLanguage = (langCode: string) => {
    setSelectedLang(langCode);
    setLocale(langCode);
  };

  const handleStartSession = () => {
    if (!unlockedIntake) return;
    setStarting(true);
    setLocale(selectedLang);
    setSessionToken(unlockedIntake.session_id, unlockedIntake.session_token);
    router.push(`/application/session/${unlockedIntake.session_id}`);
  };

  const toggleDocChecked = (idx: number) => {
    setCheckedDocs((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-4">
        <Loader2 className="w-9 h-9 text-emerald-400 animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-400">
          Verifying secure candidate link...
        </p>
      </div>
    );
  }

  if (error || !inspectInfo) {
    return (
      <div className="min-h-[60vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-4 text-center">
        <div className="max-w-md mx-auto flex flex-col items-center rounded-3xl border border-white/10 bg-[#0F1522] p-8 shadow-2xl">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center mb-4">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h1 className="text-lg font-bold text-white mb-2">
            Invite Link Expired or Invalid
          </h1>
          <p className="text-xs text-slate-400 leading-relaxed mb-6">
            {error ||
              "This invite link is no longer valid or has been revoked. Please contact your relocation case manager to issue a fresh link."}
          </p>
          <button
            type="button"
            onClick={() => router.push("/")}
            className="rounded-xl bg-emerald-500 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-xs hover:bg-emerald-400 transition-colors cursor-pointer"
          >
            Return to Homepage
          </button>
        </div>
      </div>
    );
  }

  const org = unlockedIntake?.organization || inspectInfo.organization;
  const requiredDocs =
    unlockedIntake?.required_documents ?? inspectInfo.required_documents ?? [];
  const primaryAccent = resolveSafeHexColor(org?.ui_theme_config?.primary_color);
  const safeWebsiteUrl = resolveSafeHttpUrl(org?.official_website_url);
  const welcomeCopy =
    org?.ui_theme_config?.citizen_welcome_text?.trim() ||
    org?.description?.trim() ||
    null;

  return (
    <div className="min-h-[75vh] bg-[#0A0E17] text-slate-100 py-10 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl">
        <div
          className="rounded-3xl border border-white/10 bg-[#0F1522] p-6 sm:p-10 shadow-2xl overflow-hidden"
          style={
            primaryAccent
              ? { borderTopWidth: "4px", borderTopColor: primaryAccent }
              : undefined
          }
        >
          {/* White-Label Agency / Authority Header (2.3) */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/[0.08]">
            <div className="flex items-center gap-3.5 min-w-0">
              <div className="h-12 w-12 shrink-0 rounded-2xl border border-white/10 bg-[#0A0E17] p-1.5 flex items-center justify-center overflow-hidden">
                {org.has_logo && !logoLoadError ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={`/api/organizations/${org.id}/logo`}
                    alt={`${org.name} logo`}
                    onError={() => setLogoLoadError(true)}
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <Landmark className="w-6 h-6 text-emerald-400" />
                )}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-bold text-white truncate">
                    {org.name}
                  </span>
                  {org.is_verified_government && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">
                      <ShieldCheck className="w-3 h-3 shrink-0" />
                      Verified Authority
                    </span>
                  )}
                </div>
                {welcomeCopy && (
                  <p className="mt-1 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {welcomeCopy}
                  </p>
                )}
              </div>
            </div>

            <div
              className="inline-flex items-center gap-2 self-start sm:self-center shrink-0 rounded-full px-3 py-1 text-[11px] font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              style={
                primaryAccent
                  ? {
                      backgroundColor: primaryAccent,
                      color: getContrastTextColor(primaryAccent),
                      borderColor: primaryAccent,
                    }
                  : undefined
              }
            >
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              Official Application Form
            </div>
          </div>

          {/* Candidate Greeting */}
          <div className="mt-6 text-center">
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              {t("candidateWelcome")}
            </h1>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Hello,{" "}
              <strong className="text-white">{inspectInfo.candidate_name}</strong>
              ! {t("candidateSubtitle")}
            </p>
          </div>

          {/* Assigned Form Card */}
          <div className="mt-7 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1">
              {t("assignedForm")}
            </div>
            <div className="text-base font-bold text-white">
              {inspectInfo.form_title}
            </div>
            {inspectInfo.form_description && (
              <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">
                {inspectInfo.form_description}
              </p>
            )}
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-300">
              <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>
                Prepared by{" "}
                <strong className="text-white">{org.name}</strong> so you can
                answer questions in your own language.
              </span>
            </div>
          </div>

          {/* Pre-Form Required Supporting Documents Checklist (2.2) */}
          {requiredDocs.length > 0 && (
            <div
              data-testid="invite-required-documents"
              className="mt-6 rounded-2xl border border-white/10 bg-[#0A0E17] p-5"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <ClipboardCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <h2 className="text-sm font-bold text-white">
                  Documents to Prepare Before Starting
                </h2>
              </div>
              <p className="text-xs text-slate-400 mb-3.5 leading-relaxed">
                Keep these supporting documents ready before entering your answers:
              </p>
              <ul className="space-y-2">
                {requiredDocs.map((docName, idx) => {
                  const isChecked = Boolean(checkedDocs[idx]);
                  return (
                    <li key={`${idx}-${docName}`}>
                      <label
                        className={`flex items-start gap-3 rounded-xl border p-3 text-xs transition-colors cursor-pointer ${
                          isChecked
                            ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                            : "border-white/10 bg-[#0F1522] text-slate-200 hover:border-white/20"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleDocChecked(idx)}
                          className="mt-0.5 h-4 w-4 rounded border-white/20 bg-[#0A0E17] text-emerald-500 accent-emerald-500 shrink-0 cursor-pointer"
                        />
                        <span
                          className={`leading-relaxed ${
                            isChecked ? "line-through opacity-80" : ""
                          }`}
                        >
                          {docName}
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* 2-Step Email OTP Verification Gate (2.1) */}
          {!unlockedIntake ? (
            <div className="mt-6 rounded-2xl border border-white/10 bg-[#0A0E17] p-5 sm:p-6">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">
                    Verify Your Email to Unlock This Form
                  </h2>
                  <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                    To protect your personal information, we send a single-use
                    6-digit code to{" "}
                    <bdi className="font-mono font-semibold text-slate-200">
                      {maskedEmail}
                    </bdi>
                    .
                  </p>
                </div>
              </div>

              {otpInfoMsg && (
                <div
                  role="status"
                  className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2.5 text-xs text-emerald-300 flex items-center gap-2"
                >
                  <Mail className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{otpInfoMsg}</span>
                </div>
              )}

              {otpError && (
                <div
                  role="alert"
                  className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-200 flex items-center gap-2"
                >
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{otpError}</span>
                </div>
              )}

              {!otpSent ? (
                <div className="mt-5">
                  <button
                    type="button"
                    data-testid="send-invite-otp-btn"
                    onClick={handleSendOtp}
                    disabled={sendingOtp}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500 py-3.5 px-5 text-sm font-bold text-slate-950 shadow-[0_0_24px_-4px_rgb(var(--brand-500-rgb)/0.4)] hover:bg-emerald-400 disabled:opacity-50 transition-all cursor-pointer"
                  >
                    {sendingOtp ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Sending Verification Code...</span>
                      </>
                    ) : (
                      <>
                        <Mail className="w-4 h-4" />
                        <span>Send 6-Digit Verification Code</span>
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <form onSubmit={handleVerifyOtp} className="mt-5 space-y-4">
                  <div>
                    <label
                      htmlFor="invite-otp-input"
                      className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5"
                    >
                      6-Digit Email Verification Code
                    </label>
                    <input
                      id="invite-otp-input"
                      data-testid="invite-otp-input"
                      type="text"
                      dir="ltr"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) =>
                        setOtpCode(
                          e.target.value.replace(/\D/g, "").slice(0, 6)
                        )
                      }
                      placeholder="000000"
                      className="w-full rounded-xl border border-white/15 bg-[#0F1522] px-4 py-3 text-center text-lg font-mono font-bold tracking-[0.4em] text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    />
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2.5">
                    <button
                      type="submit"
                      data-testid="verify-invite-otp-btn"
                      disabled={verifyingOtp || otpCode.length !== 6}
                      className="flex-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500 py-3.5 px-5 text-sm font-bold text-slate-950 shadow-[0_0_24px_-4px_rgb(var(--brand-500-rgb)/0.4)] hover:bg-emerald-400 disabled:opacity-50 transition-all cursor-pointer"
                    >
                      {verifyingOtp ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Verifying Code...</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          <span>Verify &amp; Unlock Form</span>
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={sendingOtp}
                      className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-slate-700 bg-[#0F1522] px-4 py-3 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50 transition-colors cursor-pointer"
                    >
                      {sendingOtp ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <RefreshCw className="w-3.5 h-3.5" />
                      )}
                      <span>Resend Code</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          ) : (
            <>
              <div className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-300 flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>
                  Email verified. Choose your assistance language and start your
                  session below.
                </span>
              </div>

              <div className="mt-6">
                <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-2">
                  {t("selectLangPrompt")}
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {UNIVERSAL_LANGUAGES.map((lang) => {
                    const active = selectedLang === lang.code;
                    return (
                      <button
                        key={lang.code}
                        type="button"
                        onClick={() => handleSelectLanguage(lang.code)}
                        className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all cursor-pointer ${
                          active
                            ? "border-emerald-500 bg-emerald-500/15 text-emerald-300 font-bold ring-2 ring-emerald-500/30"
                            : "border-white/10 bg-[#0A0E17] hover:bg-[#151D2E] hover:border-white/20 text-slate-200"
                        }`}
                      >
                        <span className="text-sm font-semibold">
                          {lang.nativeName}
                        </span>
                        <span
                          className={`text-[10px] ${
                            active ? "text-emerald-300/80" : "text-slate-400"
                          }`}
                        >
                          {lang.englishName}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-white/[0.08] flex flex-col items-center gap-3">
                <button
                  type="button"
                  onClick={handleStartSession}
                  disabled={starting}
                  className="w-full rounded-2xl bg-emerald-500 py-3.5 text-sm font-bold text-slate-950 shadow-[0_0_24px_-4px_rgb(var(--brand-500-rgb)/0.4)] hover:bg-emerald-400 active:scale-[0.99] disabled:opacity-50 transition-all text-center cursor-pointer"
                >
                  {starting ? t("starting") : t("startAssistedSession")}
                </button>
                <p className="text-[11px] text-slate-400 text-center flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                  <span>{t("securePrivateNotice")}</span>
                </p>
              </div>
            </>
          )}

          {/* White-Label Agency Coordinator Contact Footer (2.3) */}
          {(org.office_address ||
            org.contact_email ||
            org.contact_phone ||
            safeWebsiteUrl) && (
            <div className="mt-8 pt-5 border-t border-white/[0.08]">
              <div className="text-xs font-semibold text-slate-500 mb-2.5">
                Contact Helpdesk — {org.name}
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-400">
                {org.office_address && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                    <span>{org.office_address}</span>
                  </span>
                )}
                {org.contact_email && (
                  <span className="inline-flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                    <bdi>{org.contact_email}</bdi>
                  </span>
                )}
                {org.contact_phone && (
                  <span className="inline-flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                    <bdi>{org.contact_phone}</bdi>
                  </span>
                )}
                {safeWebsiteUrl && (
                  <a
                    href={safeWebsiteUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-emerald-400 hover:underline"
                  >
                    <Globe className="w-3.5 h-3.5 shrink-0" />
                    <bdi>{safeWebsiteUrl.replace(/^https?:\/\//i, "")}</bdi>
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
