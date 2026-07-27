"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ApplicationSummary } from "../services/applicationsClient";

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

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg backdrop-blur-xl">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                autoFocus
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={handleSaveTitle}
                disabled={busy}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
              >
                {t("renameSave")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setTitleDraft(application.title);
                  setEditing(false);
                }}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300"
              >
                {t("cancel")}
              </button>
            </div>
          ) : (
            <h2 className="truncate text-base font-bold text-slate-100">{application.title}</h2>
          )}
          <p className="mt-1 text-xs text-slate-400">
            {application.formName} &middot; {t(`status_${application.status}`)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {t("updatedLabel")}: {new Date(application.updatedAt).toLocaleString()}
          </p>
          {!application.exportSupported && (
            <p className="mt-1 text-xs text-amber-400">{t("exportUnsupported")}</p>
          )}
        </div>
        <div className="h-2 w-16 shrink-0 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
            style={{ width: `${application.progressPercentage}%` }}
          />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleResume}
          className="rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-500 px-3 py-1.5 text-xs font-bold text-white shadow shadow-indigo-500/20 transition hover:opacity-95"
        >
          {t("resume")}
        </button>
        {!editing && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:border-slate-500"
          >
            {t("rename")}
          </button>
        )}
        <button
          type="button"
          onClick={handleDelete}
          disabled={busy}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-rose-300 transition hover:border-rose-700 disabled:opacity-40"
        >
          {t("delete")}
        </button>
      </div>
    </div>
  );
}
