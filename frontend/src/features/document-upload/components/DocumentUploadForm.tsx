"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { uploadDocument, createSessionFromDocument } from "../services/apiClient";
import { setDocumentToken } from "../services/documentCredentials";
import { setSessionToken } from "../../form-session/services/sessionCredentials";
import { DocumentUploadResponse } from "../types";
import { ApiError } from "../../form-session/services/apiClient";

interface DocumentUploadFormProps {
  currentLocale: string;
}

export default function DocumentUploadForm({ currentLocale }: DocumentUploadFormProps) {
  const router = useRouter();
  const t = useTranslations("documentUpload");
  const tc = useTranslations("common");

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [privacyAccepted, setPrivacyAccepted] = useState<boolean>(false);
  const [outputLanguage, setOutputLanguage] = useState<string>("en");
  const [stage, setStage] = useState<"idle" | "uploading" | "analyzing" | "success" | "error">("idle");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<DocumentUploadResponse | null>(null);
  const [sessionCreating, setSessionCreating] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setAnalysisResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !privacyAccepted || stage === "uploading" || stage === "analyzing") return;

    try {
      setStage("uploading");
      setUploadProgress(0);
      setErrorMsg(null);

      // Perform streaming upload tracking progress
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

      // Store document credentials securely
      if (result.ownershipToken) {
        setDocumentToken(result.documentId, result.ownershipToken);
      }

      setAnalysisResult(result);
      setStage("success");
    } catch (err: any) {
      setStage("error");
      if (err instanceof ApiError) {
        // Map backend custom error code to localized message
        const key = `error_${err.detail}`; // using detail containing code
        let msg = t(key);
        // Fallback checks
        if (!msg || msg === key) {
          msg = t(`error_${err.message}`) || err.detail || "Upload validation failed.";
        }
        setErrorMsg(msg);
      } else {
        setErrorMsg(err.message || "An unexpected error occurred during upload.");
      }
    }
  };

  const handleStartSession = async () => {
    if (!analysisResult || sessionCreating) return;
    const documentId = analysisResult.documentId;

    try {
      setSessionCreating(true);
      setErrorMsg(null);

      const sessionResult = await createSessionFromDocument(
        documentId,
        currentLocale,
        outputLanguage
      );

      // Store session ownership token
      setSessionToken(sessionResult.sessionId, sessionResult.ownershipToken);

      // Redirect to session guided flow
      router.push(`/application/session/${sessionResult.sessionId}`);
    } catch (err: any) {
      setSessionCreating(false);
      setErrorMsg(err.detail || err.message || "Failed to create guided session.");
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-6">
      {errorMsg && (
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

      {/* Analyzing loader screen */}
      {stage === "analyzing" && (
        <div className="flex flex-col items-center justify-center p-8 space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm text-slate-400">
            {t("analyzing") || "Analyzing PDF structure..."}
          </p>
        </div>
      )}

      {/* Successful analysis results screen */}
      {stage === "success" && analysisResult?.analysis && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 space-y-4">
            <h2 className="text-xl font-bold text-slate-200">
              {t("analysis_complete") || "Document Analysis Complete"}
            </h2>

            {/* Structure characteristics checklist */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2 text-slate-300">
                <span className="font-semibold text-slate-400">{t("pages_count") || "Pages:"}</span>
                <span>{analysisResult.analysis.pageCount}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <span className="font-semibold text-slate-400">{t("document_type") || "Type:"}</span>
                <span>
                  {analysisResult.analysis.documentType === "fillable_pdf"
                    ? t("fillable_pdf") || "Fillable PDF"
                    : analysisResult.analysis.documentType === "digital_pdf"
                    ? t("digital_pdf") || "Digital PDF"
                    : analysisResult.analysis.documentType === "scanned_pdf"
                    ? t("scanned_pdf") || "Scanned PDF"
                    : analysisResult.analysis.documentType === "hybrid_pdf"
                    ? t("hybrid_pdf") || "Hybrid PDF"
                    : t("unknown_pdf") || "Unknown PDF"}
                </span>
              </div>
            </div>

            {/* Detail results indicators */}
            <div className="space-y-2 pt-2 border-t border-slate-900 text-xs text-slate-400">
              <div className="flex items-center justify-between">
                <span>{t("has_native_text") || "Contains Native Text:"}</span>
                <span className={analysisResult.analysis.hasNativeText ? "text-emerald-400 font-bold" : "text-slate-600"}>
                  {analysisResult.analysis.hasNativeText ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>{t("has_acroform") || "Contains Interactive Form Fields:"}</span>
                <span className={analysisResult.analysis.hasAcroForm ? "text-emerald-400 font-bold" : "text-slate-600"}>
                  {analysisResult.analysis.hasAcroForm ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>{t("has_images") || "Contains Embedded Images:"}</span>
                <span className={analysisResult.analysis.hasEmbeddedImages ? "text-indigo-400 font-bold" : "text-slate-600"}>
                  {analysisResult.analysis.hasEmbeddedImages ? "YES" : "NO"}
                </span>
              </div>
            </div>

            {/* Match output & Next step instruction card */}
            <div className="rounded-xl bg-slate-900 p-4 space-y-3">
              {analysisResult.analysis.nextStep === "supported_template" && (
                <>
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{t("template_matched") || "Supported Template Recognized"}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {t("template_matched_body") || "We have a pre-mapped translation system for this document. You can complete it in your native language."}
                  </p>
                </>
              )}

              {analysisResult.analysis.nextStep === "ocr_required" && (
                <>
                  <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>{t("ocr_required_title") || "OCR Recognition Needed"}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {t("ocr_required_body") || "This form appears to be scanned or image-based. We can extract its text using local OCR."}
                  </p>
                </>
              )}

              {analysisResult.analysis.nextStep === "dynamic_field_detection" && (
                <>
                  <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{t("dynamic_detection_title") || "Dynamic Field Detection Needed (Phase 11)"}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {t("dynamic_detection_body") || "This is a digital document but does not match any predefined templates. Dynamic field extraction will be supported in Phase 11."}
                  </p>
                </>
              )}

              {analysisResult.analysis.nextStep === "review_required" && (
                <>
                  <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{t("review_required_title") || "Manual Review Required"}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {t("review_required_body") || "The analysis signals for this document are inconclusive. Manual support review is required."}
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Action triggers */}
          <div className="flex gap-4">
            <button
              type="button"
              className="flex-1 rounded-xl bg-slate-800 py-3.5 text-sm font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
              onClick={handleRemoveFile}
            >
              {t("restart") || "Reset / Try Another"}
            </button>

            {analysisResult.analysis.nextStep === "supported_template" && (
              <button
                type="button"
                disabled={sessionCreating}
                className="flex-1 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-sm font-bold text-white hover:opacity-95 disabled:opacity-40 disabled:pointer-events-none"
                onClick={handleStartSession}
              >
                {sessionCreating ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                    <span>{tc("loading")}</span>
                  </div>
                ) : (
                  <span>{t("start_completion") || "Start Guided Form"}</span>
                )}
              </button>
            )}

            {analysisResult.analysis.nextStep === "ocr_required" && (
              <button
                type="button"
                className="flex-1 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-sm font-bold text-white hover:opacity-95"
                onClick={() =>
                  router.push(`/application/document/${analysisResult.documentId}/ocr`)
                }
              >
                {t("start_ocr") || "Start OCR"}
              </button>
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
