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

  // Deliberately does not depend on `t` (the next-intl translator): this
  // avoids re-fetching every time the surrounding component re-renders,
  // which would otherwise silently undo an in-flight rename/delete by
  // reloading the pre-mutation list from the server.
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
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm font-medium text-slate-400">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 py-16 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-2xl">
        <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
          {t("title")}
        </h1>
        <p className="mt-2 text-sm text-slate-400">{t("subtitle")}</p>

        <div className="mt-8 space-y-4">
          {loadFailed && (
            <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
              {t("empty")}
            </div>
          )}

          {applications.length === 0 && !loadFailed ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center">
              <p className="text-sm text-slate-400">{t("empty")}</p>
              <Link
                href="/application"
                className="mt-4 inline-block rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition hover:opacity-95"
              >
                {t("startNew")}
              </Link>
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
