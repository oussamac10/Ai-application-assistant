"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Briefcase,
  Building2,
  ExternalLink,
  Landmark,
  Plus,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/features/auth/context/AuthProvider";
import {
  deleteAccount,
  exportAccountData,
  requestEmailVerification,
} from "@/features/auth/services/authClient";
import {
  clearProfileVault,
  deleteProfileVaultEntry,
  listProfileVault,
  ProfileVaultEntry,
  upsertProfileVaultEntry,
} from "@/features/profile-vault/services/vaultClient";
import { OrganizationSettings } from "@/features/portal/components/OrganizationSettings";
import {
  createOrganization,
  getCurrentOrganization,
} from "@/features/portal/services/portalClient";
import { Organization } from "@/features/portal/types";

const VAULT_FIELD_CATALOG: Array<{
  key: string;
  labelKey: string;
  fieldType: string;
  placeholder: string;
  ltr?: boolean;
}> = [
  {
    key: "personal.first_name",
    labelKey: "key_personal_first_name",
    fieldType: "string",
    placeholder: "Max",
  },
  {
    key: "personal.last_name",
    labelKey: "key_personal_last_name",
    fieldType: "string",
    placeholder: "Mustermann",
  },
  {
    key: "person.date_of_birth",
    labelKey: "key_person_date_of_birth",
    fieldType: "date",
    placeholder: "1992-08-14",
    ltr: true,
  },
  {
    key: "person.nationality",
    labelKey: "key_person_nationality",
    fieldType: "country",
    placeholder: "DE",
    ltr: true,
  },
  {
    key: "contact.email",
    labelKey: "key_contact_email",
    fieldType: "email",
    placeholder: "name@example.com",
    ltr: true,
  },
  {
    key: "contact.phone",
    labelKey: "key_contact_phone",
    fieldType: "phone",
    placeholder: "+49 170 1234567",
    ltr: true,
  },
  {
    key: "address.street",
    labelKey: "key_address_street",
    fieldType: "string",
    placeholder: "Musterstraße 12",
  },
  {
    key: "address.postal_code",
    labelKey: "key_address_postal_code",
    fieldType: "string",
    placeholder: "10115",
    ltr: true,
  },
  {
    key: "address.city",
    labelKey: "key_address_city",
    fieldType: "string",
    placeholder: "Berlin",
  },
  {
    key: "address.country",
    labelKey: "key_address_country",
    fieldType: "country",
    placeholder: "DE",
    ltr: true,
  },
  {
    key: "finance.iban",
    labelKey: "key_finance_iban",
    fieldType: "iban",
    placeholder: "DE89 3704 0044 0532 0130 00",
    ltr: true,
  },
];

export default function AccountSettingsPage() {
  const router = useRouter();
  const { user, loading: authLoading, refresh } = useAuth();
  const tAuth = useTranslations("auth");
  const tVault = useTranslations("vault");
  const tc = useTranslations("common");

  const [vaultEntries, setVaultEntries] = useState<ProfileVaultEntry[]>([]);
  const [vaultLoading, setVaultLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState(VAULT_FIELD_CATALOG[0].key);
  const [entryValue, setEntryValue] = useState("");
  const [savingEntry, setSavingEntry] = useState(false);

  const [verifySent, setVerifySent] = useState(false);
  const [verifySubmitting, setVerifySubmitting] = useState(false);

  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Organization workspace & division state
  const [org, setOrg] = useState<Organization | null>(null);
  const [orgLoading, setOrgLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"organization" | "personal">("personal");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createType, setCreateType] = useState<"government" | "business">("government");
  const [createName, setCreateName] = useState("");
  const [createWebsite, setCreateWebsite] = useState("");
  const [creatingOrg, setCreatingOrg] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const activeFieldMeta = useMemo(
    () =>
      VAULT_FIELD_CATALOG.find((item) => item.key === selectedKey) ??
      VAULT_FIELD_CATALOG[0],
    [selectedKey],
  );

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }

    let active = true;
    setVaultLoading(true);
    listProfileVault()
      .then((items) => {
        if (active) setVaultEntries(items);
      })
      .catch(() => {
        if (active) setVaultEntries([]);
      })
      .finally(() => {
        if (active) setVaultLoading(false);
      });

    getCurrentOrganization()
      .then((o) => {
        if (active && o) {
          setOrg(o);
          setActiveTab("organization");
        }
      })
      .catch(() => {
        if (active) setOrg(null);
      })
      .finally(() => {
        if (active) setOrgLoading(false);
      });

    return () => {
      active = false;
    };
  }, [authLoading, user, router]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (creatingOrg || !createName.trim()) return;
    setCreatingOrg(true);
    setCreateError(null);
    try {
      const created = await createOrganization({
        name: createName.trim(),
        organization_type: createType,
        official_website_url: createWebsite.trim() || undefined,
      });
      setOrg(created);
      setActiveTab("organization");
      setShowCreateModal(false);
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setCreatingOrg(false);
    }
  };

  const handleRequestVerification = async () => {
    if (verifySubmitting) return;
    setVerifySubmitting(true);
    setErrorMsg(null);
    try {
      await requestEmailVerification();
      setVerifySent(true);
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : tAuth("error_generic_auth_failed"),
      );
    } finally {
      setVerifySubmitting(false);
    }
  };

  const handleSaveVaultEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = entryValue.trim();
    if (!trimmed || savingEntry) return;

    setSavingEntry(true);
    setErrorMsg(null);
    try {
      const valueLang =
        (typeof document !== "undefined" && document.documentElement.lang) ||
        "en";
      const saved = await upsertProfileVaultEntry(
        selectedKey,
        trimmed,
        activeFieldMeta.fieldType,
        valueLang,
      );
      setVaultEntries((prev) => {
        const rest = prev.filter((item) => item.questionKey !== saved.questionKey);
        return [...rest, saved].sort((a, b) =>
          a.questionKey.localeCompare(b.questionKey),
        );
      });
      setEntryValue("");
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : tAuth("error_generic_auth_failed"),
      );
    } finally {
      setSavingEntry(false);
    }
  };

  const handleDeleteVaultEntry = async (questionKey: string) => {
    setErrorMsg(null);
    try {
      await deleteProfileVaultEntry(questionKey);
      setVaultEntries((prev) =>
        prev.filter((item) => item.questionKey !== questionKey),
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : tAuth("error_generic_auth_failed"),
      );
    }
  };

  const handleClearVault = async () => {
    setErrorMsg(null);
    try {
      await clearProfileVault();
      setVaultEntries([]);
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : tAuth("error_generic_auth_failed"),
      );
    }
  };

  const handleExportData = async () => {
    if (exporting) return;
    setExporting(true);
    setExportSuccess(false);
    setErrorMsg(null);
    try {
      const payload = await exportAccountData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = "ai-form-assistant-data-export.json";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(objectUrl);
      setExportSuccess(true);
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : tAuth("error_generic_auth_failed"),
      );
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleting) return;
    setDeleting(true);
    setErrorMsg(null);
    try {
      await deleteAccount();
      try {
        await refresh();
      } catch {
        // ignore post-deletion session refresh error
      }
      router.push("/");
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : tAuth("error_generic_auth_failed"),
      );
      setDeleting(false);
    }
  };

  const labelForVaultKey = (questionKey: string) => {
    const found = VAULT_FIELD_CATALOG.find((item) => item.key === questionKey);
    return found ? tVault(found.labelKey) : questionKey;
  };

  if (authLoading || !user) {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center text-slate-900">
        <p className="text-sm font-medium text-slate-600">{tc("loading")}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10 text-slate-900 sm:px-6 lg:px-8">
      <header className="border-b border-slate-200 pb-5 text-start flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              {org ? org.name : tAuth("accountSettings")}
            </h1>
            {org ? (
              org.organization_type === "government" ? (
                org.is_verified_government ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Verified Official Authority
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/20">
                    <Landmark className="w-3.5 h-3.5 text-indigo-600" />
                    Government Workspace
                  </span>
                )
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-600/20">
                  <Briefcase className="w-3.5 h-3.5 text-blue-600" />
                  Business Workspace
                </span>
              )
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                <UserIcon className="w-3.5 h-3.5 text-slate-600" />
                Citizen Account
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-600">
            <bdi>{user.email}</bdi>
            {org && (
              <span className="ms-2 text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded uppercase">
                Role: {org.role}
              </span>
            )}
          </p>
        </div>

        {org && (
          <div>
            <Link
              href="/portal"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 transition-all"
            >
              <span>Open Form Portal</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}
      </header>

      {/* Tabs Switcher for Organization Accounts */}
      {org && (
        <div className="flex border-b border-slate-200">
          <button
            type="button"
            onClick={() => setActiveTab("organization")}
            className={`inline-flex items-center gap-2 border-b-2 py-3 px-4 text-xs font-bold uppercase tracking-wider transition-colors ${
              activeTab === "organization"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700"
            }`}
          >
            <Building2 className="w-4 h-4" />
            Organization & Verification
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("personal")}
            className={`inline-flex items-center gap-2 border-b-2 py-3 px-4 text-xs font-bold uppercase tracking-wider transition-colors ${
              activeTab === "personal"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700"
            }`}
          >
            <UserIcon className="w-4 h-4" />
            Personal Profile, Vault & GDPR
          </button>
        </div>
      )}

      {errorMsg && (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          {errorMsg}
        </div>
      )}

      {activeTab === "organization" && org ? (
        <OrganizationSettings initialOrg={org} onOrgUpdated={setOrg} />
      ) : (
        <>
          {/* Individual workspace prompt when user does not have an org */}
          {!org && !orgLoading && (
            <section className="rounded-2xl border border-indigo-200 bg-linear-to-r from-indigo-50/80 via-white to-slate-50 p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs">
              <div>
                <div className="flex items-center gap-2">
                  <span className="p-2 rounded-xl bg-indigo-600 text-white">
                    <Landmark className="w-4 h-4" />
                  </span>
                  <h2 className="text-sm font-bold text-slate-900">
                    Are you a Municipality, Government Agency, or Private Firm?
                  </h2>
                </div>
                <p className="mt-1 text-xs text-slate-600 max-w-xl">
                  Create an official organization workspace to publish multilingual citizen forms, generate printable QR counter posters, or manage private client intake cases.
                </p>
              </div>
              <div>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 transition-colors whitespace-nowrap"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Set Up Workspace
                </button>
              </div>
            </section>
          )}

      {/* 1. Email Verification Status */}
      <section className="surface-panel rounded-2xl p-6 space-y-4 text-start">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-900">
              {tAuth("verifyEmailTitle")}
            </h2>
            <p className="text-xs text-slate-600">
              <bdi>{user.email}</bdi>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            {user.emailVerified ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                {tAuth("emailVerifiedBadge")}
              </span>
            ) : (
              <>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  {tAuth("emailUnverifiedBadge")}
                </span>
                <button
                  type="button"
                  data-testid="request-verify-email-btn"
                  disabled={verifySubmitting}
                  onClick={handleRequestVerification}
                  className="btn-secondary h-9 px-3.5 py-0 text-xs font-semibold"
                >
                  {tAuth("sendVerificationEmail")}
                </button>
              </>
            )}
          </div>
        </div>
        {verifySent && (
          <p className="rounded-xl border border-indigo-200 bg-indigo-50/70 px-3.5 py-2.5 text-xs font-medium text-indigo-800">
            {tAuth("verificationEmailSent")}
          </p>
        )}
      </section>

      {/* 2. Encrypted Personal Profile Vault */}
      <section className="surface-panel rounded-2xl p-6 space-y-5 text-start">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">
                {tVault("title")}
              </h2>
              <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-800">
                AES / Fernet
              </span>
            </div>
            <p className="max-w-2xl text-xs leading-relaxed text-slate-600">
              {tVault("subtitle")}
            </p>
          </div>
          {vaultEntries.length > 0 && (
            <button
              type="button"
              onClick={handleClearVault}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-2xs transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
            >
              {tVault("clearAll")}
            </button>
          )}
        </div>

        {vaultLoading ? (
          <p className="text-xs text-slate-500">{tc("loading")}</p>
        ) : vaultEntries.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-4 text-xs leading-relaxed text-slate-600">
            {tVault("empty")}
          </div>
        ) : (
          <div className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
            {vaultEntries.map((entry) => (
              <div
                key={entry.questionKey}
                className="flex items-center justify-between gap-4 px-4 py-3 text-sm transition-colors hover:bg-slate-50/70"
              >
                <div className="min-w-0 space-y-0.5">
                  <p className="text-xs font-semibold text-slate-500">
                    {labelForVaultKey(entry.questionKey)}
                  </p>
                  <p className="break-words text-sm font-semibold text-slate-900">
                    <bdi>{entry.value}</bdi>
                  </p>
                </div>
                <button
                  type="button"
                  data-testid={`vault-delete-${entry.questionKey}`}
                  onClick={() => handleDeleteVaultEntry(entry.questionKey)}
                  className="shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-rose-600 transition-colors hover:bg-rose-50"
                >
                  {tVault("deleteEntry")}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Aligned Control Bar for Adding / Updating a Vault Field */}
        <form
          onSubmit={handleSaveVaultEntry}
          className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-4"
        >
          <div className="grid grid-cols-1 gap-3 md:grid-cols-12 md:items-end">
            <div className="space-y-1.5 md:col-span-4">
              <label
                htmlFor="vault-key-select"
                className="block text-xs font-semibold text-slate-700"
              >
                {tVault("fieldLabel")}
              </label>
              <div className="relative">
                <select
                  id="vault-key-select"
                  data-testid="vault-key-select"
                  value={selectedKey}
                  onChange={(e) => setSelectedKey(e.target.value)}
                  className="input-field h-11 cursor-pointer appearance-none bg-white py-0 pe-10 text-sm font-medium text-slate-900"
                >
                  {VAULT_FIELD_CATALOG.map((item) => (
                    <option key={item.key} value={item.key}>
                      {tVault(item.labelKey)}
                    </option>
                  ))}
                </select>
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-y-0 end-0 flex items-center pe-3.5 text-slate-500"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </span>
              </div>
            </div>

            <div className="space-y-1.5 md:col-span-5">
              <label
                htmlFor="vault-value-input"
                className="block text-xs font-semibold text-slate-700"
              >
                {tVault("valueLabel")}
              </label>
              <input
                id="vault-value-input"
                data-testid="vault-value-input"
                type="text"
                value={entryValue}
                onChange={(e) => setEntryValue(e.target.value)}
                placeholder={activeFieldMeta.placeholder}
                data-ltr={activeFieldMeta.ltr ? "true" : undefined}
                required
                className="input-field h-11 bg-white py-0 text-sm"
              />
            </div>

            <div className="md:col-span-3">
              <button
                type="submit"
                data-testid="vault-save-entry-btn"
                disabled={!entryValue.trim() || savingEntry}
                className="btn-primary h-11 w-full px-4 py-0 text-sm font-semibold"
              >
                {tVault("saveEntry")}
              </button>
            </div>
          </div>
        </form>
      </section>

      {/* 3. GDPR Art. 20 Data Portability & Art. 17 Right to Erasure */}
      <section className="surface-panel rounded-2xl p-6 space-y-5 text-start">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-900">
            {tAuth("gdprTitle")}
          </h2>
          <p className="max-w-2xl text-xs leading-relaxed text-slate-600">
            {tAuth("gdprSubtitle")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            data-testid="gdpr-export-btn"
            disabled={exporting}
            onClick={handleExportData}
            className="btn-secondary h-10 px-4 py-0 text-xs font-semibold"
          >
            {exporting ? tAuth("exportingMyData") : tAuth("exportMyData")}
          </button>

          {!confirmDeleteOpen && (
            <button
              type="button"
              data-testid="delete-account-open-btn"
              onClick={() => setConfirmDeleteOpen(true)}
              className="inline-flex h-10 items-center whitespace-nowrap rounded-xl border border-rose-300 bg-rose-50 px-4 text-xs font-semibold text-rose-700 transition-colors hover:bg-rose-100"
            >
              {tAuth("deleteAccountButton")}
            </button>
          )}
        </div>

        {exportSuccess && (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-xs font-medium text-emerald-800">
            {tAuth("exportSuccess")}
          </p>
        )}

        {confirmDeleteOpen && (
          <div className="rounded-xl border border-rose-300 bg-rose-50/80 p-4 space-y-3">
            <p className="text-sm font-bold text-rose-900">
              {tAuth("deleteAccountConfirmTitle")}
            </p>
            <p className="text-xs leading-relaxed text-rose-800">
              {tAuth("deleteAccountConfirmBody")}
            </p>
            <div className="flex flex-wrap gap-2.5">
              <button
                type="button"
                data-testid="delete-account-confirm-btn"
                disabled={deleting}
                onClick={handleDeleteAccount}
                className="inline-flex h-10 items-center whitespace-nowrap rounded-xl bg-rose-600 px-4 text-xs font-semibold text-white transition-colors hover:bg-rose-700 disabled:opacity-60"
              >
                {tAuth("deleteAccountConfirmAction")}
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={() => setConfirmDeleteOpen(false)}
                className="btn-secondary h-10 px-4 py-0 text-xs font-medium"
              >
                {tc("back")}
              </button>
            </div>
          </div>
        )}
      </section>
      </>
      )}

      {/* Modal to create organization workspace */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs">
          <div className="surface-panel w-full max-w-md rounded-2xl p-6 shadow-xl border border-slate-200 bg-white">
            <h3 className="text-base font-bold text-slate-900">
              Create Organization Workspace
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Choose your organization type to customize your workspace features, badges, and portals.
            </p>

            <form onSubmit={handleCreateWorkspace} className="mt-4 space-y-4">
              {createError && (
                <div className="rounded-lg bg-rose-50 p-3 text-xs text-rose-700 border border-rose-200">
                  {createError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setCreateType("government")}
                  className={`p-3 rounded-xl border text-start transition-all ${
                    createType === "government"
                      ? "border-indigo-600 bg-indigo-50/70 ring-2 ring-indigo-600/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900">
                    <Landmark className="w-4 h-4 text-indigo-600" />
                    Government
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">
                    Bürgeramt, Ausländerbehörde, City
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setCreateType("business")}
                  className={`p-3 rounded-xl border text-start transition-all ${
                    createType === "business"
                      ? "border-indigo-600 bg-indigo-50/70 ring-2 ring-indigo-600/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900">
                    <Briefcase className="w-4 h-4 text-indigo-600" />
                    Business
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">
                    Relocation, law practice, HR
                  </p>
                </button>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  {createType === "government"
                    ? "Authority / Municipality Name"
                    : "Company / Firm Name"}
                  <span className="text-rose-500 ms-1">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder={
                    createType === "government"
                      ? "e.g. Stadt Freiburg"
                      : "e.g. ReloCare Immigration GmbH"
                  }
                  className="input-field"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Official Website <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                  type="url"
                  value={createWebsite}
                  onChange={(e) => setCreateWebsite(e.target.value)}
                  placeholder="https://..."
                  className="input-field"
                />
              </div>

              <div className="mt-5 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary px-3 py-1.5 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingOrg}
                  className="btn-primary px-4 py-1.5 text-xs font-semibold"
                >
                  {creatingOrg ? "Creating..." : "Create Workspace"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
