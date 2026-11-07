"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ApplicationSummary } from "../services/applicationsClient";
import { AlertCircle, ArrowRight } from "lucide-react";

interface Props {
  application: ApplicationSummary;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

function resumePath(app: ApplicationSummary): string {
  if (app.status === "completed" || app.status === "ready_for_export") {
    return `/application/session/${app.id}/complete`;
  }
  if (app.status === "awaiting_final_confirmation") {
    return `/application/session/${app.id}/summary`;
  }
  return `/application/session/${app.id}`;
}

export default function ApplicationCard({ application, onRename, onDelete }: Props) {
  const t = useTranslations("applications");
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [titleDraft, setTitleDraft] = useState(application.title);
  const [busy, setBusy] = useState(false);

  const handleResume = () => {
    router.push(resumePath(application));
  };

  const handleSaveTitle = async () => {
    if (!titleDraft.trim() || busy) return;
    setBusy(true);
    try {
      await onRename(application.id, titleDraft.trim());
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (busy) return;
    if (!window.confirm(`${t("deleteConfirmTitle")} ${t("deleteConfirmBody")}`)) {
      return;
    }
    setBusy(true);
    try {
      await onDelete(application.id);
    } finally {
      setBusy(false);
    }
  };

  const statusColor =
    application.status === "completed"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : application.status === "ready_for_export"
      ? "bg-sky-50 text-sky-700 border-sky-200"
      : application.status === "awaiting_final_confirmation"
      ? "bg-amber-50 text-amber-800 border-amber-200"
      : "bg-indigo-50 text-indigo-700 border-indigo-200";

  return (
    <div className="surface-card rounded-2xl p-5 sm:p-6 transition-colors duration-150 hover:border-slate-300">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                autoFocus
                className="input-field py-2 text-sm"
              />
              <button
                type="button"
                onClick={handleSaveTitle}
                disabled={busy}
                className="btn-primary px-3.5 py-2 text-xs font-semibold"
              >
                {t("renameSave")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setTitleDraft(application.title);
                  setEditing(false);
                }}
                className="btn-secondary px-3.5 py-2 text-xs font-medium"
              >
                {t("cancel")}
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-base font-bold text-slate-900 tracking-tight">{application.title}</h2>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusColor}`}>
                {t(`status_${application.status}`)}
              </span>
            </div>
          )}
          <p className="mt-1 text-xs font-medium text-slate-700">
            {application.formName}
          </p>
          <p className="mt-1 text-xs text-slate-500 tabular-nums">
            {t("updatedLabel")}: {new Date(application.updatedAt).toLocaleString()}
          </p>
          {!application.exportSupported && (
            <p className="mt-1.5 text-xs text-amber-800 flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
              <span>{t("exportUnsupported")}</span>
            </p>
          )}
        </div>

        {/* Progress indicator */}
        <div className="flex items-center gap-2.5 self-start sm:self-center">
          <div className="h-1.5 w-24 sm:w-28 overflow-hidden rounded-full bg-slate-100 border border-slate-200">
            <div
              className="h-full rounded-full bg-indigo-600 transition-all duration-300"
              style={{ width: `${application.progressPercentage}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-slate-700 w-9 text-end tabular-nums">
            {application.progressPercentage}%
          </span>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 pt-3.5 border-t border-slate-200">
        <button
          type="button"
          onClick={handleResume}
          className="btn-primary px-4 py-2 text-xs font-semibold"
        >
          <span>{t("resume")}</span>
          <ArrowRight className="h-3.5 w-3.5 rtl:rotate-180" />
        </button>
        {!editing && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="btn-secondary px-3.5 py-2 text-xs font-medium"
          >
            {t("rename")}
          </button>
        )}
        <button
          type="button"
          onClick={handleDelete}
          disabled={busy}
          className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs font-semibold text-rose-700 transition-colors hover:bg-rose-100 disabled:opacity-40"
        >
          {t("delete")}
        </button>
      </div>
    </div>
  );
}
