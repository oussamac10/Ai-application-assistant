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

export default function DocumentUploadForm({ currentLocale }: DocumentUploadFormProps) {
  const router = useRouter();
  const t = useTranslations("documentUpload");

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [privacyAccepted, setPrivacyAccepted] = useState<boolean>(false);
  const [outputLanguage, setOutputLanguage] = useState<string>("en");
  const [stage, setStage] = useState<Stage>("idle");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [pendingDocumentId, setPendingDocumentId] = useState<string | null>(null);
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const [uncertainFieldCount, setUncertainFieldCount] = useState<number>(0);
  const [processingNextStep, setProcessingNextStep] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const debugUiEnabled = isDetectionDebugUiEnabled();

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
      setErrorMsg(t("error_invalid_file_type") || "Only PDF files are supported.");
      return;
    }
    // Max size: 10MB
    if (selectedFile.size > 10485760) {
      setErrorMsg(t("error_file_too_large") || "File exceeds maximum size of 10MB.");
      return;
    }
    setFile(selectedFile);
  };

  const handleRemoveFile = () => {
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

  const runAutomaticProcessing = async (result: DocumentUploadResponse) => {
    const documentId = result.documentId;
    setPendingDocumentId(documentId);

    if (result.analysis?.nextStep === "review_required") {
      setStage("review_required");
      return;
    }

    setProcessingNextStep(result.analysis?.nextStep || null);
    setStage("processing");
    try {
      const prepared = await prepareQuestions(documentId, currentLocale, outputLanguage);

      if (prepared.sessionId && prepared.ownershipToken) {
        setSessionToken(prepared.sessionId, prepared.ownershipToken);
      }

      if (prepared.status === "failed") {
        setStage("error");
        setErrorMsg(resolveUploadErrorMessage(t, prepared.errorCode));
        return;
      }

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
      setStage("error");
      setErrorMsg(resolveUploadErrorMessage(t, err));
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !privacyAccepted || stage === "uploading" || stage === "analyzing") return;

    try {
      setStage("uploading");
      setUploadProgress(0);
      setErrorMsg(null);

      const result = await uploadDocument(
        file,
        currentLocale,
        outputLanguage,
        privacyAccepted,
        (percent) => {
          setUploadProgress(percent);
          if (percent === 100) {
            setStage("analyzing");
          }
        }
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
      return t("processing_detecting") || "Detecting the information requested…";
    }
    return t("processing_preparing") || "Preparing your questions…";
  };

  return (
    <div className="space-y-6">
      {errorMsg && stage !== "review_required" && stage !== "uncertain" && (
        <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
          {errorMsg}
        </div>
      )}

      {stage === "idle" && (
        <form onSubmit={handleUploadSubmit} className="space-y-6">
          {/* File Picker Drag-and-Drop */}
          <div
            className={`relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition cursor-pointer focus-within:ring-2 focus-within:ring-indigo-500/20 ${
              dragActive
                ? "border-indigo-500 bg-indigo-500/10"
                : "border-slate-800 bg-slate-950/20 hover:border-slate-700 hover:bg-slate-950/40"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
            role="button"
            tabIndex={0}
            aria-label={t("drag_and_drop_instructions") || "Drag and drop PDF file here"}
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

            <svg
              className="mx-auto h-12 w-12 text-slate-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>

            {!file ? (
              <>
                <p className="mt-4 text-sm font-semibold text-slate-300">
                  {t("drag_and_drop_instructions") || "Drag and drop your PDF here, or click to browse"}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {t("maximum_size") || "PDF up to 10MB (max 20 pages)"}
                </p>
              </>
            ) : (
              <div className="mt-4 space-y-2">
                <p className="text-sm font-bold text-indigo-400">
                  {t("selected_file") || "Selected File:"}
                </p>
                <p className="text-sm font-medium text-slate-200">{file.name}</p>
                <p className="text-xs text-slate-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <button
                  type="button"
                  className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
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
              {/* Output Language Select */}
              <div className="space-y-2">
                <label htmlFor="upload-output-select" className="block text-sm font-semibold tracking-wide text-slate-300">
                  {t("selectOutputLanguage") || "Select completed form language"}
                </label>
                <select
                  id="upload-output-select"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 cursor-pointer"
                  value={outputLanguage}
                  onChange={(e) => setOutputLanguage(e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="de">Deutsch</option>
                  <option value="fr">Français</option>
                  <option value="ar">العربية</option>
                </select>
              </div>

              {/* Privacy notice box */}
              <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                <h3 className="text-sm font-bold text-slate-200">{t("privacyNoticeTitle") || "Privacy Notice"}</h3>
                <p className="text-xs leading-relaxed text-slate-400">{t("privacyNoticeBody") || "Your uploaded document remains private and temporary. It will be deleted automatically after 24 hours."}</p>
                <label className="flex items-center gap-3 cursor-pointer select-none text-slate-300">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500/20 cursor-pointer"
                    checked={privacyAccepted}
                    onChange={(e) => setPrivacyAccepted(e.target.checked)}
                  />
                  <span className="text-xs font-semibold">{t("acceptPrivacy") || "I consent to the temporary upload of my document."}</span>
                </label>
              </div>

              {/* Submit trigger button */}
              <button
                type="submit"
                disabled={!privacyAccepted}
                className="w-full rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-4 text-base font-bold shadow-lg shadow-indigo-500/20 transition hover:opacity-95 disabled:opacity-40 disabled:pointer-events-none active:scale-[0.99]"
              >
                {t("upload_and_analyze") || "Upload and Analyze"}
              </button>
            </>
          )}
        </form>
      )}

      {/* Uploading progress screen */}
      {stage === "uploading" && (
        <div className="flex flex-col items-center justify-center p-8 space-y-4">
          <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm text-slate-400">
            {t("uploading") || "Uploading..."} ({uploadProgress}%)
          </p>
        </div>
      )}

      {/* Analyzing loader screen — simple message only, no technical detail */}
      {stage === "analyzing" && (
        <div className="flex flex-col items-center justify-center p-8 space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm text-slate-400">
            {t("analyzing") || "Reading the document…"}
          </p>
        </div>
      )}

      {/* Automatic processing screen — covers OCR/detection/question
          generation behind one plain-language message. Normal users never
          see provider names, confidence numbers, or a field-review step. */}
      {stage === "processing" && (
        <div className="flex flex-col items-center justify-center p-8 space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm text-slate-400">{processingMessage()}</p>
          {debugUiEnabled && pendingDocumentId && (
            <a
              className="text-xs text-slate-600 underline hover:text-slate-400"
              href={`/application/document/${pendingDocumentId}/detect-fields`}
            >
              {t("debug_open_review") || "Open technical review (debug)"}
            </a>
          )}
        </div>
      )}

      {/* Uncertainty screen — plain language only, no raw field editor */}
      {stage === "uncertain" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-amber-800/60 bg-amber-950/20 p-6 space-y-3 text-center">
            <h3 className="text-lg font-bold text-amber-200">
              {t("uncertainty_title") || "One section may need confirmation"}
            </h3>
            <p className="text-sm text-amber-300/90 leading-relaxed">
              {t("uncertainty_body") ||
                "We could not confidently read one part of this form. You can continue with the questions we found."}
            </p>
          </div>
          <div className="flex gap-4">
            <button
              type="button"
              className="flex-1 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-sm font-bold text-white hover:opacity-95"
              onClick={() => pendingSessionId && goToSession(pendingSessionId)}
            >
              {t("continue_with_detected") || "Continue"}
            </button>
            {debugUiEnabled && pendingDocumentId && (
              <a
                className="flex-1 flex items-center justify-center rounded-xl bg-slate-800 py-3.5 text-sm font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
                href={`/application/document/${pendingDocumentId}/detect-fields`}
              >
                {t("review_uncertain_section") || "Review uncertain section"}
              </a>
            )}
          </div>
        </div>
      )}

      {/* Could-not-process screen — safe, plain message; document/session
          is preserved for retry, nothing meaningless is generated */}
      {stage === "review_required" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 text-center space-y-3">
            <h3 className="text-lg font-bold text-slate-200">
              {t("could_not_process_title") || "We could not confidently process this form"}
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              {uncertainFieldCount > 0
                ? t("no_usable_questions_body") ||
                  "We found no usable questions in this document. You can try again or upload a different file."
                : t("review_required_body") ||
                  "The analysis signals for this document are inconclusive."}
            </p>
          </div>
          <div className="flex gap-4">
            <button
              type="button"
              className="flex-1 rounded-xl bg-slate-800 py-3.5 text-sm font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
              onClick={handleRemoveFile}
            >
              {t("restart") || "Reset / Try Another"}
            </button>
            {debugUiEnabled && pendingDocumentId && (
              <a
                className="flex-1 flex items-center justify-center rounded-xl bg-slate-800 py-3.5 text-sm font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
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
          <div className="rounded-2xl border border-rose-800 bg-rose-950/20 p-6 text-center space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-950 text-rose-400">
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-rose-200">
              {t("upload_error_title") || "Upload or Analysis Failed"}
            </h3>
            <p className="text-sm text-rose-300">{errorMsg}</p>
          </div>
          <button
            type="button"
            className="w-full rounded-xl bg-slate-800 py-3.5 text-sm font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
            onClick={handleRemoveFile}
          >
            {t("retry") || "Retry Upload"}
          </button>
        </div>
      )}
    </div>
  );
}
