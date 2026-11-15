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
import { Plus, FileText, Loader2 } from "lucide-react";

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
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center bg-[#0A0E17] text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-9 w-9 animate-spin motion-reduce:animate-none text-emerald-400" />
          <p className="text-sm font-medium text-slate-400">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100vh-3.5rem)] bg-[#0A0E17] px-4 py-10 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-4xl">
        {/* Dashboard Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {t("title")}
            </h1>
            <p className="mt-1 text-sm text-slate-400">{t("subtitle")}</p>
          </div>

          <Link
            href="/application"
            className="btn-primary px-5 py-2.5 text-sm font-semibold"
          >
            <Plus className="h-4 w-4" />
            <span>{t("startNew")}</span>
          </Link>
        </div>

        <div className="mt-8 space-y-4">
          {loadFailed && (
            <div
              role="alert"
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200"
            >
              {t("empty")}
            </div>
          )}

          {applications.length === 0 && !loadFailed ? (
            <div className="surface-card rounded-2xl border border-white/10 bg-[#0F1522] p-12 text-center space-y-4 text-slate-100">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                <FileText className="h-7 w-7" />
              </div>
              <p className="text-base font-bold text-white">{t("empty")}</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                You haven&apos;t started any applications yet. Begin an assisted session to fill official documents.
              </p>
              <div className="pt-2">
                <Link
                  href="/application"
                  className="btn-primary px-6 py-3 text-sm font-semibold"
                >
                  <Plus className="h-4 w-4" />
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
