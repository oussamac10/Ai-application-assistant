"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { uploadDocument } from "../services/apiClient";
import { setDocumentToken } from "../services/documentCredentials";
import { setSessionToken } from "../../form-session/services/sessionCredentials";
import { prepareQuestions } from "../../field-detection/services/apiClient";
import { isDetectionDebugUiEnabled } from "../../field-detection/debugMode";
import { DocumentUploadResponse } from "../types";
import { resolveUploadErrorMessage } from "../utils/resolveUploadErrorMessage";

interface DocumentUploadFormProps {
  currentLocale: string;
}

// "processing" covers reading/OCR/detecting/preparing-questions in one
// simple step for the normal user — see docs/phases/phase-13-... for the
// message-per-nextStep mapping.
type Stage =
  | "idle"
  | "uploading"
  | "analyzing"
  | "processing"
  | "uncertain"
  | "review_required"
  | "error";

export default function DocumentUploadForm({
  currentLocale,
}: DocumentUploadFormProps) {
  const router = useRouter();
  const t = useTranslations("documentUpload");

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [privacyAccepted, setPrivacyAccepted] = useState<boolean>(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [pendingDocumentId, setPendingDocumentId] = useState<string | null>(
    null,
  );
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const [uncertainFieldCount, setUncertainFieldCount] = useState<number>(0);
  const [processingNextStep, setProcessingNextStep] = useState<string | null>(
    null,
  );

  const fileInputRef = useRef<HTMLInputElement>(null);
  const debugUiEnabled = isDetectionDebugUiEnabled();

  const runIdRef = useRef(0);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (selectedFile: File) => {
    setErrorMsg(null);
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setErrorMsg(
        t("error_invalid_file_type") || "Only PDF files are supported.",
      );
      return;
    }
    // Max size: 10MB
    if (selectedFile.size > 10485760) {
      setErrorMsg(
        t("error_file_too_large") || "File exceeds maximum size of 10MB.",
      );
      return;
    }
    setFile(selectedFile);
  };

  const handleRemoveFile = () => {
    runIdRef.current += 1;
    setFile(null);
    setStage("idle");
    setUploadProgress(0);
    setErrorMsg(null);
    setPendingDocumentId(null);
    setPendingSessionId(null);
    setUncertainFieldCount(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const goToSession = (sessionId: string) => {
    router.push(`/application/session/${sessionId}`);
  };

  const prepareWithRetry = async (documentId: string) => {
    const maxAttempts = 3;
    for (let attempt = 1; ; attempt += 1) {
      try {
        return await prepareQuestions(documentId, currentLocale);
      } catch (err: any) {
        const status = typeof err?.status === "number" ? err.status : 0;
        const isTransport = status === 0 || status === 502 || status === 504;
        const isBareGatewayError =
          status === 500 && !err?.detail && !err?.errorCode;
        const retryable = isTransport || isBareGatewayError;
        if (!retryable || attempt >= maxAttempts) {
          throw err;
        }
        await new Promise((resolve) => setTimeout(resolve, 2000 * attempt));
      }
    }
  };

  const runAutomaticProcessing = async (result: DocumentUploadResponse) => {
    const documentId = result.documentId;
    const runId = ++runIdRef.current;
    const isCurrent = () => runIdRef.current === runId;

    setPendingDocumentId(documentId);

    if (result.analysis?.nextStep === "review_required") {
      setStage("review_required");
      return;
    }

    setProcessingNextStep(result.analysis?.nextStep || null);
    setStage("processing");
    setErrorMsg(null);

    try {
      const prepared = await prepareWithRetry(documentId);
      if (!isCurrent()) return;

      if (prepared.sessionId && prepared.ownershipToken) {
        setSessionToken(prepared.sessionId, prepared.ownershipToken);
      }

      if (prepared.status === "failed") {
        setStage("error");
        setErrorMsg(resolveUploadErrorMessage(t, prepared.errorCode));
        return;
      }

      setErrorMsg(null);

      if (prepared.status === "needs_clarification" || !prepared.sessionId) {
        setUncertainFieldCount(prepared.uncertainty?.uncertainFieldCount || 0);
        setStage("review_required");
        return;
      }

      if (prepared.uncertainty?.hasUncertainFields) {
        setPendingSessionId(prepared.sessionId);
        setUncertainFieldCount(prepared.uncertainty.uncertainFieldCount);
        setStage("uncertain");
        return;
      }

      goToSession(prepared.sessionId);
    } catch (err: any) {
      if (!isCurrent()) return;
      setStage("error");
      setErrorMsg(resolveUploadErrorMessage(t, err));
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !file ||
      !privacyAccepted ||
      stage === "uploading" ||
      stage === "analyzing"
    )
      return;

    try {
      setStage("uploading");
      setUploadProgress(0);
      setErrorMsg(null);

      const result = await uploadDocument(
        file,
        currentLocale,
        undefined,
        privacyAccepted,
        (percent) => {
          setUploadProgress(percent);
          if (percent === 100) {
            setStage("analyzing");
          }
        },
      );

      if (result.ownershipToken) {
        setDocumentToken(result.documentId, result.ownershipToken);
      }

      await runAutomaticProcessing(result);
    } catch (err: any) {
      setStage("error");
      setErrorMsg(resolveUploadErrorMessage(t, err));
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const processingMessage = () => {
    if (stage !== "processing") return "";
    if (processingNextStep === "ocr_required") {
      return t("processing_reading") || "Reading the document…";
    }
    if (processingNextStep === "dynamic_field_detection") {
      return (
        t("processing_detecting") || "Detecting the information requested…"
      );
    }
    return t("processing_preparing") || "Preparing your questions…";
  };

  return (
    <div className="space-y-6">
      {errorMsg &&
        !["review_required", "uncertain", "error"].includes(stage) && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          >
            <svg className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{errorMsg}</span>
          </div>
        )}

      {stage === "idle" && (
        <form onSubmit={handleUploadSubmit} className="space-y-6">
          {/* File Picker Drag-and-Drop */}
          <div
            className={`relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-150 cursor-pointer focus-within:ring-2 focus-within:ring-indigo-500/30 ${
              dragActive
                ? "border-indigo-600 bg-indigo-50/70"
                : "border-slate-300 bg-slate-50/60 hover:border-indigo-400 hover:bg-indigo-50/30"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
            role="button"
            tabIndex={0}
            aria-label={
              t("drag_and_drop_instructions") || "Drag and drop PDF file here"
            }
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                triggerFileInput();
              }
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
            />

            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-indigo-200 bg-white text-indigo-600 shadow-2xs">
              <svg
                className="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.75}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>

            {!file ? (
              <>
                <p className="mt-4 text-sm font-semibold text-slate-900">
                  {t("drag_and_drop_instructions") ||
                    "Drag and drop any official PDF form here, or click to browse"}
                </p>
                <p className="mt-1.5 text-xs text-slate-500">
                  {t("maximum_size") || "PDF up to 10MB (max 20 pages) • AcroForm, Digital Text & Scanned PDFs"}
                </p>
              </>
            ) : (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">
                  {t("selected_file") || "Selected File:"}
                </p>
                <p className="text-sm font-semibold text-slate-900">
                  {file.name}
                </p>
                <p className="text-xs text-slate-500 tabular-nums">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <button
                  type="button"
                  className="mt-1 inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile();
                  }}
                >
                  {t("remove_file") || "Remove"}
                </button>
              </div>
            )}
          </div>

          {/* Form Language and Options */}
          {file && (
            <>
              {/* Privacy notice box */}
              <div className="space-y-3 rounded-xl border border-indigo-200/80 bg-indigo-50/50 p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-950">
                  {t("privacyNoticeTitle") || "Privacy Notice"}
                </h3>
                <p className="text-xs leading-relaxed text-slate-700">
                  {t("privacyNoticeBody") ||
                    "Your uploaded document remains private and temporary. It will be deleted automatically after 24 hours."}
                </p>
                <label className="flex items-center gap-3 cursor-pointer select-none text-slate-900 pt-1">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 bg-white text-indigo-600 focus:ring-indigo-500/30 cursor-pointer"
                    checked={privacyAccepted}
                    onChange={(e) => setPrivacyAccepted(e.target.checked)}
                  />
                  <span className="text-xs font-semibold">
                    {t("acceptPrivacy") ||
                      "I consent to the temporary upload of my document."}
                  </span>
                </label>
              </div>

              {/* Submit trigger button */}
              <button
                type="submit"
                disabled={!privacyAccepted}
                className="btn-primary w-full py-3.5 text-sm font-semibold"
              >
                {t("upload_and_analyze") || "Upload and Analyze"}
              </button>
            </>
          )}
        </form>
      )}

      {/* Uploading progress screen */}
      {stage === "uploading" && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-8 space-y-4">
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm font-semibold text-slate-700 tabular-nums">
            {t("uploading") || "Uploading..."} ({uploadProgress}%)
          </p>
        </div>
      )}

      {/* Analyzing loader screen */}
      {stage === "analyzing" && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-8 space-y-4">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <p className="text-sm font-semibold text-slate-700">
            {t("analyzing") || "Reading the document…"}
          </p>
        </div>
      )}

      {/* Automatic processing screen */}
      {stage === "processing" && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-8 space-y-4">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <p className="text-sm font-semibold text-slate-700">{processingMessage()}</p>
          {debugUiEnabled && pendingDocumentId && (
            <a
              className="text-xs text-slate-500 underline hover:text-slate-800"
              href={`/application/document/${pendingDocumentId}/detect-fields`}
            >
              {t("debug_open_review") || "Open technical review (debug)"}
            </a>
          )}
        </div>
      )}

      {/* Uncertainty screen */}
      {stage === "uncertain" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-6 space-y-2.5 text-center">
            <h3 className="text-base font-bold text-amber-900">
              {t("uncertainty_title") || "One section may need confirmation"}
            </h3>
            <p className="text-sm text-amber-800 leading-relaxed">
              {t("uncertainty_body") ||
                "We could not confidently read one part of this form. You can continue with the questions we found."}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              className="btn-primary flex-1 py-3 text-sm font-semibold"
              onClick={() => pendingSessionId && goToSession(pendingSessionId)}
            >
              {t("continue_with_detected") || "Continue"}
            </button>
            {debugUiEnabled && pendingDocumentId && (
              <a
                className="btn-secondary flex-1 py-3 text-sm font-medium"
                href={`/application/document/${pendingDocumentId}/detect-fields`}
              >
                {t("review_uncertain_section") || "Review uncertain section"}
              </a>
            )}
          </div>
        </div>
      )}

      {/* Could-not-process screen */}
      {stage === "review_required" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center space-y-2.5">
            <h3 className="text-base font-bold text-slate-900">
              {t("could_not_process_title") ||
                "We could not confidently process this form"}
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              {uncertainFieldCount > 0
                ? t("no_usable_questions_body") ||
                  "We found no usable questions in this document. You can try again or upload a different file."
                : t("review_required_body") ||
                  "The analysis signals for this document are inconclusive."}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              className="btn-secondary flex-1 py-3 text-sm font-medium"
              onClick={handleRemoveFile}
            >
              {t("restart") || "Reset / Try Another"}
            </button>
            {debugUiEnabled && pendingDocumentId && (
              <a
                className="btn-secondary flex-1 py-3 text-sm font-medium"
                href={`/application/document/${pendingDocumentId}/detect-fields`}
              >
                {t("debug_open_review") || "Open technical review (debug)"}
              </a>
            )}
          </div>
        </div>
      )}

      {/* Error state display screen */}
      {stage === "error" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center space-y-3">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full border border-rose-200 bg-white text-rose-600 shadow-2xs">
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h3 className="text-base font-bold text-rose-900">
              {t("upload_error_title") || "Upload or Analysis Failed"}
            </h3>
            <p className="text-sm text-rose-800">{errorMsg}</p>
          </div>
          <button
            type="button"
            className="btn-secondary w-full py-3 text-sm font-medium"
            onClick={handleRemoveFile}
          >
            {t("retry") || "Retry Upload"}
          </button>
        </div>
      )}
    </div>
  );
}
