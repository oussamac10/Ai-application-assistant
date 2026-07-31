"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  getSummary,
  confirmSummary,
  reopenField,
  ApiError,
  Summary,
} from "@/features/form-session/services/apiClient";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  parseRowKey,
  rowHeading,
} from "@/features/form-session/utils/repeatedRows";

export default function SessionSummary() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("summary");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const ts = useTranslations("signature");

  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // fieldKey -> reason code, from the last rejected confirmation.
  const [blockingFields, setBlockingFields] = useState<Map<string, string>>(
    new Map(),
  );

  useEffect(() => {
    // No early credential check: a claimed session has no anonymous token
    // in sessionStorage and resumes via the auth cookie alone (see the
    // matching fix in the guided-session page).
    async function loadSummary() {
      try {
        setLoading(true);
        setErrorMsg(null);
        const data = await getSummary(sessionId);
        setSummary(data);
      } catch (err: any) {
        setErrorMsg(
          te(err.message) || "Failed to load session summary details.",
        );
      } finally {
        setLoading(false);
      }
    }
    loadSummary();
  }, [sessionId, te]);

  const handleEditField = async (fieldId: string) => {
    try {
      setLoading(true);
      setErrorMsg(null);

      // Reopen is navigation, not a submission. Editing used to re-submit the
      // field's existing answer to un-confirm it, which sent an empty string
      // for a question that had none — so skipped and unanswered questions
      // could not be edited at all.
      await reopenField(sessionId, fieldId);

      router.push(`/application/session/${sessionId}`);
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to initiate field edit.");
      setLoading(false);
    }
  };

  const handleConfirmSummary = async () => {
    if (submitting) return;

    try {
      setSubmitting(true);
      setErrorMsg(null);

      // Call confirm-summary endpoint
      await confirmSummary(sessionId);

      // Redirect to export/complete screen
      router.push(`/application/session/${sessionId}/complete`);
    } catch (err: any) {
      // The backend names every blocking question rather than one generic
      // sentence, so mark them all at once instead of sending the user round
      // the loop field by field.
      if (err instanceof ApiError && err.status === 409) {
        const blocking = [
          ...err.missingRequiredFields,
          ...err.invalidAnswerFields,
        ];
        if (blocking.length > 0) {
          setBlockingFields(
            new Map(blocking.map((p) => [p.fieldKey, p.reason])),
          );
          setErrorMsg(t("blockedByFields", { count: blocking.length }));
          setSubmitting(false);
          return;
        }
      }
      setErrorMsg(
        te(err.message) || "Failed to finalize summary confirmation.",
      );
      setSubmitting(false);
    }
  };

  const handleRestart = () => {
    removeSessionToken(sessionId);
    router.push("/application");
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm font-medium text-slate-400">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  /** The three states the summary must tell apart, plus the two it already
   * knew. Derived from `answerState` (what the user did) crossed with
   * requiredness (what the document demanded) — never from one alone, which is
   * how a deliberate skip came to be reported as an invalid value. */
  type RowState =
    | "confirmed"
    | "pendingManualSignature"
    | "skipped"
    | "notAnswered"
    | "missingRequired"
    | "invalid"
    | "pending";

  const rowState = (f: Summary["fields"][number]): RowState => {
    const requiredness =
      f.requiredness ?? (f.required ? "required" : "unknown");
    const state = f.answerState ?? (f.status === "skipped" ? "skipped" : null);

    // A deliberate completion, not an absence: the user chose to sign the
    // printed form, and reporting that as "Skipped" would misdescribe it.
    if (state === "pending_manual_signature") return "pendingManualSignature";
    if (state === "skipped") return "skipped";
    if (state === "invalid") return "invalid";
    if (f.status === "confirmed") return "confirmed";
    // A required question is not finished until it is confirmed — answered but
    // unconfirmed still blocks, and the backend says so too.
    if (requiredness === "required") return "missingRequired";
    if (state === "unreached" || state === "unanswered" || !f.originalAnswer) {
      // A form that said nothing asked for nothing, so nothing is *missing*.
      return "notAnswered";
    }
    return "pending";
  };

  // Optional and unknown questions left unanswered never block. Only an
  // explicitly required question without a confirmed answer does.
  const hasIncompleteFields = summary?.fields.some((f) => {
    const state = rowState(f);
    return state === "missingRequired" || state === "invalid";
  });

  const renderField = (f: Summary["fields"][number]) => {
                      const state = rowState(f);
                      const blocks =
                        state === "missingRequired" ||
                        state === "invalid" ||
                        blockingFields.has(f.fieldKey);
                      const isRequired =
                        (f.requiredness ??
                          (f.required ? "required" : "unknown")) === "required";

                      return (
                        <tr
                          key={f.fieldId}
                          data-testid={`summary-row-${f.fieldKey}`}
                          data-state={state}
                          className={`transition ${
                            blocks ? "bg-rose-950/10" : "hover:bg-slate-900/20"
                          }`}
                        >
                          <td className="px-4 py-4 font-semibold text-slate-200">
                            {f.label}
                            {/* Only a real finding is marked. An unmarked
                                question shows nothing rather than claiming
                                the form said something it did not. */}
                            {isRequired && (
                              <span className="text-indigo-400 ml-1">*</span>
                            )}
                          </td>
                          <td className="px-4 py-4 italic text-slate-400 max-w-xs truncate">
                            {f.originalAnswer || "-"}
                          </td>
                          <td className="px-4 py-4 text-slate-300 font-medium">
                            {f.outputValue || "-"}
                          </td>
                          <td className="px-4 py-4">
                            <span
                              data-testid={`summary-status-${f.fieldKey}`}
                              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                state === "confirmed"
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : blocks
                                    ? "bg-rose-500/10 text-rose-400 animate-pulse"
                                    : "bg-slate-800 text-slate-400"
                              }`}
                            >
                              {state === "pendingManualSignature"
                                ? ts("summaryPending")
                                : state === "skipped"
                                ? t("skipped")
                                : state === "notAnswered"
                                  ? t("notAnswered")
                                  : state === "missingRequired"
                                    ? t("missingRequired")
                                    : state === "invalid"
                                      ? t("invalidAnswer")
                                      : f.status}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-right">
                            {/* Every row is editable, including a skipped or
                                never answered one. */}
                            <button
                              type="button"
                              onClick={() => handleEditField(f.fieldId)}
                              className="text-xs font-bold text-indigo-400 hover:text-indigo-300 transition"
                            >
                              {tc("edit")}
                            </button>
                          </td>
                        </tr>
                      );
  };

  /** The summary in document order, with a heading opening each repeated row.
   *
   * The backend emits repeated table rows as flat indexed fields
   * (`children_1_gender`), because the guided flow asks one question at a time
   * and has no repeated-section UI. On screen that means a child's six details
   * read as six unrelated answers, and "männlich / weiblich" appears twice with
   * nothing saying whose it is. Grouping is presentation only — keys are the
   * contract with export and are never rewritten. */
  type SummaryEntry =
    | { kind: "heading"; id: string; label: string }
    | { kind: "field"; field: Summary["fields"][number] };

  const rowsWithHeadings: SummaryEntry[] = [];
  let openRow: string | null = null;
  for (const field of summary?.fields ?? []) {
    const parts = parseRowKey(field.fieldKey);
    const rowId = parts ? `${parts.section}-${parts.index}` : null;
    if (rowId && rowId !== openRow) {
      rowsWithHeadings.push({
        kind: "heading",
        id: rowId,
        label: rowHeading(parts!.section, parts!.index),
      });
    }
    openRow = rowId;
    rowsWithHeadings.push({ kind: "field", field });
  }

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 text-slate-100 px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-2xl">
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-6 md:p-8 shadow-2xl backdrop-blur-xl">
          {/* Glowing decorator */}
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-indigo-500/10 blur-3xl" />

          <div className="relative z-10 space-y-6">
            <div className="space-y-1 text-center">
              <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent">
                {t("title")}
              </h1>
              <p className="text-sm text-slate-400">{t("subtitle")}</p>
            </div>

            {errorMsg && (
              <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
                {errorMsg}
              </div>
            )}

            {/* Fields table summary */}
            <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/20">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-850 bg-slate-950/60 text-xs font-semibold uppercase tracking-wider text-slate-500">
                      <th className="px-4 py-3">{t("fieldHeader")}</th>
                      <th className="px-4 py-3">{t("originalHeader")}</th>
                      <th className="px-4 py-3">{t("normalizedHeader")}</th>
                      <th className="px-4 py-3">{t("statusHeader")}</th>
                      <th className="px-4 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850">
                    {rowsWithHeadings.map((entry) =>
                      entry.kind === "heading" ? (
                        <tr
                          key={`heading-${entry.id}`}
                          data-testid={`row-heading-${entry.id}`}
                          className="bg-slate-900/40"
                        >
                          <td
                            colSpan={5}
                            className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-300"
                          >
                            {entry.label}
                          </td>
                        </tr>
                      ) : (
                        renderField(entry.field)
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Warning block */}
            <div className="rounded-2xl border border-amber-800 bg-amber-950/20 p-4 text-xs leading-relaxed text-amber-300/90 text-left">
              {t("warning")}
            </div>

            {/* Confirm button / Restart button */}
            <div className="flex flex-col gap-3">
              <button
                type="button"
                disabled={hasIncompleteFields || submitting}
                onClick={handleConfirmSummary}
                className="w-full rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-4 text-base font-bold transition hover:opacity-95 disabled:opacity-40 disabled:pointer-events-none active:scale-[0.99] shadow-lg shadow-indigo-500/20"
              >
                {submitting ? tc("loading") : t("submitSummary")}
              </button>
              <button
                type="button"
                onClick={handleRestart}
                className="w-full rounded-xl bg-slate-850 py-3 text-sm font-bold text-slate-400 hover:text-slate-200 transition active:scale-[0.99]"
              >
                {tc("restart")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
