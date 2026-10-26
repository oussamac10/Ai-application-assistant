"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
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

const VAULT_FIELD_CATALOG: Array<{
  key: string;
  labelKey: string;
  fieldType: string;
}> = [
  { key: "personal.first_name", labelKey: "key_personal_first_name", fieldType: "string" },
  { key: "personal.last_name", labelKey: "key_personal_last_name", fieldType: "string" },
  { key: "person.date_of_birth", labelKey: "key_person_date_of_birth", fieldType: "date" },
  { key: "person.nationality", labelKey: "key_person_nationality", fieldType: "country" },
  { key: "contact.email", labelKey: "key_contact_email", fieldType: "email" },
  { key: "contact.phone", labelKey: "key_contact_phone", fieldType: "phone" },
  { key: "address.street", labelKey: "key_address_street", fieldType: "string" },
  { key: "address.postal_code", labelKey: "key_address_postal_code", fieldType: "string" },
  { key: "address.city", labelKey: "key_address_city", fieldType: "string" },
  { key: "address.country", labelKey: "key_address_country", fieldType: "country" },
  { key: "finance.iban", labelKey: "key_finance_iban", fieldType: "iban" },
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
        if (active) setErrorMsg(tAuth("error_generic_auth_failed"));
      })
      .finally(() => {
        if (active) setVaultLoading(false);
      });

    return () => {
      active = false;
    };
  }, [authLoading, user, router, tAuth]);

  const handleRequestVerification = async () => {
    if (verifySubmitting) return;
    setVerifySubmitting(true);
    setErrorMsg(null);
    try {
      await requestEmailVerification();
      setVerifySent(true);
    } catch {
      setErrorMsg(tAuth("error_generic_auth_failed"));
    } finally {
      setVerifySubmitting(false);
    }
  };

  const handleSaveVaultEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entryValue.trim() || savingEntry) return;
    setSavingEntry(true);
    setErrorMsg(null);
    try {
      const def = VAULT_FIELD_CATALOG.find((item) => item.key === selectedKey);
      const fieldType = def?.fieldType ?? "string";
      const activeLang =
        (typeof document !== "undefined" && document.documentElement.lang) ||
        "en";
      const saved = await upsertProfileVaultEntry(
        selectedKey,
        entryValue.trim(),
        fieldType,
        activeLang,
      );
      setVaultEntries((prev) => {
        const filtered = prev.filter((eItem) => eItem.questionKey !== saved.questionKey);
        return [...filtered, saved];
      });
      setEntryValue("");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : tAuth("error_generic_auth_failed"),
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
        err instanceof Error ? err.message : tAuth("error_generic_auth_failed"),
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
        err instanceof Error ? err.message : tAuth("error_generic_auth_failed"),
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
        err instanceof Error ? err.message : tAuth("error_generic_auth_failed"),
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
        err instanceof Error ? err.message : tAuth("error_generic_auth_failed"),
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
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8 space-y-8 text-slate-900">
      <div className="space-y-1 text-start">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
          {tAuth("accountSettings")}
        </h1>
        <p className="text-sm text-slate-600">
          <bdi>{user.email}</bdi>
        </p>
      </div>

      {errorMsg && (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          {errorMsg}
        </div>
      )}

      {/* 1. Email Verification Status */}
      <section className="surface-panel rounded-2xl p-6 space-y-4 text-start">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-900">
              {tAuth("verifyEmailTitle")}
            </h2>
            <p className="text-xs text-slate-600">
              <bdi>{user.email}</bdi>
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            {user.emailVerified ? (
              <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                {tAuth("emailVerifiedBadge")}
              </span>
            ) : (
              <>
                <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                  {tAuth("emailUnverifiedBadge")}
                </span>
                <button
                  type="button"
                  data-testid="request-verify-email-btn"
                  disabled={verifySubmitting}
                  onClick={handleRequestVerification}
                  className="btn-secondary px-3.5 py-1.5 text-xs font-semibold"
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
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-900">
              {tVault("title")}
            </h2>
            <p className="text-xs text-slate-600 leading-relaxed">
              {tVault("subtitle")}
            </p>
          </div>
          {vaultEntries.length > 0 && (
            <button
              type="button"
              onClick={handleClearVault}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 shrink-0"
            >
              {tVault("clearAll")}
            </button>
          )}
        </div>

        {vaultLoading ? (
          <p className="text-xs text-slate-500">{tc("loading")}</p>
        ) : vaultEntries.length === 0 ? (
          <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
            {tVault("empty")}
          </p>
        ) : (
          <div className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white overflow-hidden">
            {vaultEntries.map((entry) => (
              <div
                key={entry.questionKey}
                className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
              >
                <div className="min-w-0">
                  <p className="text-xs font-bold text-slate-700">
                    {labelForVaultKey(entry.questionKey)}
                  </p>
                  <p className="text-sm font-semibold text-slate-900 break-words">
                    <bdi>{entry.value}</bdi>
                  </p>
                </div>
                <button
                  type="button"
                  data-testid={`vault-delete-${entry.questionKey}`}
                  onClick={() => handleDeleteVaultEntry(entry.questionKey)}
                  className="rounded-md px-2.5 py-1 text-xs font-semibold text-rose-600 hover:bg-rose-50 shrink-0"
                >
                  {tVault("deleteEntry")}
                </button>
              </div>
            ))}
          </div>
        )}

        <form
          onSubmit={handleSaveVaultEntry}
          className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-2 border-t border-slate-200"
        >
          <div className="sm:col-span-5 space-y-1">
            <label
              htmlFor="vault-key-select"
              className="block text-xs font-semibold text-slate-700"
            >
              {tVault("fieldLabel")}
            </label>
            <select
              id="vault-key-select"
              data-testid="vault-key-select"
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              className="input-field"
            >
              {VAULT_FIELD_CATALOG.map((item) => (
                <option key={item.key} value={item.key}>
                  {tVault(item.labelKey)}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-5 space-y-1">
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
              required
              className="input-field"
            />
          </div>
          <div className="sm:col-span-2 flex items-end">
            <button
              type="submit"
              data-testid="vault-save-entry-btn"
              disabled={!entryValue.trim() || savingEntry}
              className="btn-primary w-full py-2.5 text-xs font-semibold"
            >
              {tVault("saveEntry")}
            </button>
          </div>
        </form>
      </section>

      {/* 3. GDPR Art. 20 Data Portability & Art. 17 Right to Erasure */}
      <section className="surface-panel rounded-2xl p-6 space-y-5 text-start">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-900">
            {tAuth("gdprTitle")}
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            {tAuth("gdprSubtitle")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            data-testid="gdpr-export-btn"
            disabled={exporting}
            onClick={handleExportData}
            className="btn-secondary px-4 py-2.5 text-xs font-semibold"
          >
            {exporting ? tAuth("exportingMyData") : tAuth("exportMyData")}
          </button>

          {!confirmDeleteOpen && (
            <button
              type="button"
              data-testid="delete-account-open-btn"
              onClick={() => setConfirmDeleteOpen(true)}
              className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
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
            <p className="text-xs text-rose-800 leading-relaxed">
              {tAuth("deleteAccountConfirmBody")}
            </p>
            <div className="flex flex-wrap gap-2.5">
              <button
                type="button"
                data-testid="delete-account-confirm-btn"
                disabled={deleting}
                onClick={handleDeleteAccount}
                className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
              >
                {tAuth("deleteAccountConfirmAction")}
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={() => setConfirmDeleteOpen(false)}
                className="btn-secondary px-4 py-2 text-xs font-medium"
              >
                {tc("back")}
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
