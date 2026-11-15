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
      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
      : application.status === "ready_for_export"
      ? "bg-sky-500/10 text-sky-300 border-sky-500/30"
      : application.status === "awaiting_final_confirmation"
      ? "bg-amber-500/10 text-amber-200 border-amber-500/30"
      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";

  return (
    <div className="surface-card rounded-2xl border border-white/10 bg-[#0F1522] p-5 sm:p-6 text-slate-100 transition-colors duration-150 motion-reduce:transition-none hover:border-emerald-500/30">
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
              <h2 className="text-base font-bold text-white tracking-tight">{application.title}</h2>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusColor}`}>
                {t(`status_${application.status}`)}
              </span>
            </div>
          )}
          <p className="mt-1 text-xs font-medium text-slate-300">
            {application.formName}
          </p>
          <p className="mt-1 text-xs text-slate-400 tabular-nums">
            {t("updatedLabel")}: {new Date(application.updatedAt).toLocaleString()}
          </p>
          {!application.exportSupported && (
            <p className="mt-1.5 text-xs text-amber-200 flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
              <span>{t("exportUnsupported")}</span>
            </p>
          )}
        </div>

        {/* Progress indicator */}
        <div className="flex items-center gap-2.5 self-start sm:self-center">
          <div className="h-1.5 w-24 sm:w-28 overflow-hidden rounded-full bg-[#0A0E17] border border-white/10">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-300 motion-reduce:transition-none"
              style={{ width: `${application.progressPercentage}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-slate-200 w-9 text-end tabular-nums">
            {application.progressPercentage}%
          </span>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 pt-3.5 border-t border-white/[0.08]">
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
          className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-300 transition-colors motion-reduce:transition-none hover:bg-rose-500/20 hover:text-rose-200 disabled:opacity-40 cursor-pointer"
        >
          {t("delete")}
        </button>
      </div>
    </div>
  );
}
