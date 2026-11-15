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
import { AlertCircle, UploadCloud, Loader2 } from "lucide-react";

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
    const lowerName = selectedFile.name.toLowerCase();
    const allowedExt = [".pdf", ".jpg", ".jpeg", ".png", ".webp"].some((ext) =>
      lowerName.endsWith(ext),
    );
    const allowedMime = [
      "application/pdf",
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/webp",
    ].includes(selectedFile.type.toLowerCase());
    if (!allowedExt && !allowedMime) {
      setErrorMsg(
        t("error_invalid_file_type") ||
          "Only PDF, JPG, PNG, and WebP files are supported.",
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
            className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

      {stage === "idle" && (
        <form onSubmit={handleUploadSubmit} className="space-y-6">
          {/* File Picker Drag-and-Drop */}
          <div
            className={`relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-150 cursor-pointer focus-within:ring-2 focus-within:ring-emerald-500/20 focus-within:border-emerald-500 ${
              dragActive
                ? "border-emerald-500 bg-emerald-500/15 ring-2 ring-emerald-500/20"
                : "border-white/15 bg-[#0A0E17] hover:border-emerald-500/50 hover:bg-[#151D2E]/80"
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
              accept=".pdf,application/pdf,.jpg,.jpeg,image/jpeg,.png,image/png,.webp,image/webp"
              onChange={handleFileChange}
            />

            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-2xs">
              <UploadCloud className="h-6 w-6" aria-hidden="true" />
            </div>

            {!file ? (
              <>
                <p className="mt-4 text-sm font-semibold text-white">
                  {t("drag_and_drop_instructions") ||
                    "Drag and drop any official PDF form here, or click to browse"}
                </p>
                <p className="mt-1.5 text-xs text-slate-400">
                  {t("maximum_size") || "PDF, JPG, or PNG • Official forms or clear photos (up to 10 MB)"}
                </p>
              </>
            ) : (
              <div className="mt-4 w-full max-w-full min-w-0 px-2 space-y-2">
                <p className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                  {t("selected_file") || "Selected File:"}
                </p>
                <p className="text-sm font-semibold text-white break-all">
                  {file.name}
                </p>
                <p className="text-xs text-slate-400 tabular-nums">
                  {file.size < 1024 * 1024
                    ? `${Math.max(0.1, file.size / 1024).toFixed(1)} KB`
                    : `${(file.size / 1024 / 1024).toFixed(2)} MB`}
                </p>
                <button
                  type="button"
                  className="mt-1 inline-flex items-center justify-center rounded-lg border border-white/15 bg-[#151D2E] px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors hover:border-white/25 hover:bg-[#1E293B] hover:text-white"
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
              <div className="space-y-3 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.07] p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-300">
                  {t("privacyNoticeTitle") || "Privacy Notice"}
                </h3>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t("privacyNoticeBody") ||
                    "Your uploaded document remains private and temporary. It will be deleted automatically after 24 hours."}
                </p>
                <label className="flex items-center gap-3 cursor-pointer select-none text-slate-100 pt-1">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-white/20 bg-[#0A0E17] text-emerald-500 accent-emerald-500 focus:ring-emerald-500/30 cursor-pointer"
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
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/10 bg-[#0A0E17] p-8 space-y-4">
          <div className="w-full bg-[#151D2E] border border-white/[0.08] h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-300 shadow-[0_0_12px_rgba(16,185,129,0.5)]"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm font-semibold text-slate-200 tabular-nums">
            {t("uploading") || "Uploading..."} ({uploadProgress}%)
          </p>
        </div>
      )}

      {/* Analyzing & Automatic processing screens with Scan Beam */}
      {(stage === "analyzing" || stage === "processing") && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-[#0A0E17] p-6 sm:p-8 space-y-5 text-start shadow-2xl relative overflow-hidden">
          {/* Top Status Header */}
          <div className="w-full flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse motion-reduce:animate-none" />
              <span className="text-xs font-bold text-emerald-400">
                Reading Your Form
              </span>
            </div>
            <span className="text-[11px] text-slate-400 hidden sm:inline-block">
              Preparing Guided Questions
            </span>
          </div>

          {/* Simulated Document Preview Canvas with Sweeping Laser Beam & Pulsating Boxes */}
          <div className="relative mx-auto w-full max-w-sm aspect-[1/1.25] bg-[#0F1522] border border-white/10 rounded-xl overflow-hidden shadow-inner p-4 select-none">
            {/* Subtle background dot grid */}
            <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:12px_12px] opacity-40 pointer-events-none" />

            {/* Document Header Skeleton */}
            <div className="space-y-1.5 mb-4 relative z-10">
              <div className="h-2 w-24 bg-slate-700/60 rounded" />
              <div className="h-1.5 w-40 bg-slate-800/60 rounded" />
            </div>

            {/* Pulsating Detected Boxes */}
            <div className="absolute top-[18%] inset-x-4 h-[12%] rounded border border-emerald-500/80 bg-emerald-500/10 animate-pulse motion-reduce:animate-none flex items-center justify-between px-2.5 z-10 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <span className="text-[10px] font-bold text-emerald-300">
                Full Name
              </span>
              <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30 font-semibold">
                Text
              </span>
            </div>

            <div className="absolute top-[35%] start-4 w-[43%] h-[11%] rounded border border-emerald-500/80 bg-emerald-500/10 animate-pulse motion-reduce:animate-none flex items-center justify-between px-2 z-10 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <span className="text-[10px] font-bold text-emerald-300 truncate">
                Date of Birth
              </span>
              <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1 py-0.5 rounded border border-emerald-500/30 shrink-0 font-semibold">
                Date
              </span>
            </div>

            <div className="absolute top-[35%] end-4 w-[43%] h-[11%] rounded border border-emerald-500/80 bg-emerald-500/10 animate-pulse motion-reduce:animate-none flex items-center justify-between px-2 z-10 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <span className="text-[10px] font-bold text-emerald-300 truncate">
                Nationality
              </span>
              <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1 py-0.5 rounded border border-emerald-500/30 shrink-0 font-semibold">
                Country
              </span>
            </div>

            <div className="absolute top-[52%] inset-x-4 h-[12%] rounded border border-emerald-500/80 bg-emerald-500/10 animate-pulse motion-reduce:animate-none flex items-center justify-between px-2.5 z-10 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <span className="text-[10px] font-bold text-emerald-300">
                Home Address
              </span>
              <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30 font-semibold">
                Address
              </span>
            </div>

            <div className="absolute bottom-4 inset-x-4 h-[18%] rounded border border-emerald-500/80 bg-emerald-500/10 animate-pulse motion-reduce:animate-none flex items-center justify-between px-2.5 z-10 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-emerald-300">
                  Signature
                </span>
              </div>
              <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30 font-semibold">
                Sign
              </span>
            </div>

            {/* Animated Emerald Scan Beam sweeping down */}
            <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_16px_#10B981,0_0_8px_#34D399] animate-laser-scan motion-reduce:animate-none pointer-events-none z-20" />
          </div>

          {/* Progress message and spinner */}
          <div className="w-full flex flex-col items-center justify-center text-center space-y-2 pt-1">
            <div className="flex items-center gap-2.5">
              <Loader2 className="h-4 w-4 animate-spin text-emerald-400 shrink-0" />
              <p className="text-sm font-semibold text-white tracking-tight">
                {stage === "analyzing"
                  ? t("analyzing") || "Reading your form..."
                  : processingMessage()}
              </p>
            </div>
            {debugUiEnabled && pendingDocumentId && (
              <a
                className="text-xs text-emerald-400 hover:text-emerald-300 underline mt-1"
                href={`/application/document/${pendingDocumentId}/detect-fields`}
              >
                {t("debug_open_review") || "Review detected questions"}
              </a>
            )}
          </div>

          {/* Simple Status Strip */}
          <div className="w-full flex items-center justify-between text-[11px] text-slate-400 border-t border-white/[0.08] pt-3">
            <span>Checking pages</span>
            <span>Private &amp; encrypted</span>
            <span className="text-emerald-400 font-medium">Almost ready</span>
          </div>
        </div>
      )}

      {/* Uncertainty screen */}
      {stage === "uncertain" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-6 space-y-2.5 text-center">
            <h3 className="text-base font-bold text-amber-200">
              {t("uncertainty_title") || "One section may need confirmation"}
            </h3>
            <p className="text-sm text-amber-200/90 leading-relaxed">
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
          <div className="rounded-xl border border-white/10 bg-[#0A0E17] p-6 text-center space-y-2.5">
            <h3 className="text-base font-bold text-white">
              {t("could_not_process_title") ||
                "We could not confidently process this form"}
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
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
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-center space-y-3">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full border border-rose-500/30 bg-[#0F1522] text-rose-400 shadow-2xs">
              <AlertCircle className="h-5 w-5" />
            </div>
            <h3 className="text-base font-bold text-rose-200">
              {t("upload_error_title") || "Upload or Analysis Failed"}
            </h3>
            <p className="text-sm text-rose-200/90">{errorMsg}</p>
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
