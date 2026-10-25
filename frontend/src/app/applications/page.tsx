"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/features/auth/context/AuthProvider";
import {
  ApplicationSummary,
  deleteApplication,
  listApplications,
  renameApplication,
} from "@/features/applications/services/applicationsClient";
import ApplicationCard from "@/features/applications/components/ApplicationCard";

export default function MyApplicationsPage() {
  const t = useTranslations("applications");
  const tc = useTranslations("common");
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  const loadApplications = useCallback(async () => {
    try {
      setLoadFailed(false);
      const data = await listApplications();
      setApplications(data);
    } catch {
      setLoadFailed(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    loadApplications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user]);

  const handleRename = async (id: string, title: string) => {
    const updated = await renameApplication(id, title);
    setApplications((prev) => prev.map((a) => (a.id === id ? updated : a)));
  };

  const handleDelete = async (id: string) => {
    await deleteApplication(id);
    setApplications((prev) => prev.filter((a) => a.id !== id));
  };

  if (authLoading || loading) {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center text-slate-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <p className="text-sm font-medium text-slate-600">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100vh-3.5rem)] px-4 py-10 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-4xl">
        {/* Dashboard Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-0.5 text-xs font-semibold text-indigo-700 mb-2">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
              User Dashboard
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              {t("title")}
            </h1>
            <p className="mt-1 text-sm text-slate-600">{t("subtitle")}</p>
          </div>

          <Link
            href="/application"
            className="btn-primary px-5 py-2.5 text-sm font-semibold"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>{t("startNew")}</span>
          </Link>
        </div>

        <div className="mt-8 space-y-4">
          {loadFailed && (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
            >
              {t("empty")}
            </div>
          )}

          {applications.length === 0 && !loadFailed ? (
            <div className="surface-card rounded-2xl p-12 text-center space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600">
                <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-base font-bold text-slate-900">{t("empty")}</p>
              <p className="text-xs text-slate-600 max-w-sm mx-auto leading-relaxed">
                You haven&apos;t started any applications yet. Begin an assisted session to fill official documents.
              </p>
              <div className="pt-2">
                <Link
                  href="/application"
                  className="btn-primary px-6 py-3 text-sm font-semibold"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span>{t("startNew")}</span>
                </Link>
              </div>
            </div>
          ) : (
            applications.map((app) => (
              <ApplicationCard
                key={app.id}
                application={app}
                onRename={handleRename}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </div>
    </main>
  );
}
