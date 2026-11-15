"use client";
/* eslint-disable @next/next/no-img-element */

import React from "react";
import { ChevronLeft, ChevronRight, Loader2, Map as MapIcon } from "lucide-react";
import { CurrentField } from "../services/apiClient";

interface SessionContextSidebarProps {
  currentField: CurrentField | null;
  completed: number;
  total: number;
  progressPercent: number;
  pagePreviewUrls: Record<number, string>;
  previewPage?: number;
  onChangePreviewPage?: (page: number) => void;
  zoomedPreviewOpen: boolean;
  onOpenZoom: () => void;
  onCloseZoom: () => void;
}

export function SessionContextSidebar({
  currentField,
  completed,
  total,
  progressPercent,
  pagePreviewUrls,
  previewPage,
  onChangePreviewPage,
  zoomedPreviewOpen,
  onOpenZoom,
  onCloseZoom,
}: SessionContextSidebarProps) {
  const fieldPage = currentField?.pageNumber ?? 1;
  const activePage = previewPage ?? fieldPage;
  const totalPages = currentField?.sourceDocumentPageCount ?? 1;
  const canNavigatePages = totalPages > 1 && Boolean(onChangePreviewPage);
  const showHighlightOnActivePage = activePage === fieldPage;
  return (
    <>
      <aside className="hidden lg:flex lg:col-span-4 flex-col gap-4 sticky top-20">
        {/* Form Info Card */}
        <div className="surface-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
              Assisted Session
            </span>
            <span className="text-xs font-mono text-slate-500 tabular-nums">
              Step 2 of 4
            </span>
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <svg
                className="h-4 w-4 text-indigo-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.75}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Official Form Flow
            </h3>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Fill in your answers sequentially. Each response is standardized
              and verified for the official document.
            </p>
          </div>

          <div className="border-t border-slate-200 pt-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-600">
              <span>Questions Completed</span>
              <span className="font-bold text-slate-900 tabular-nums">
                {completed} of {total}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden border border-slate-200">
              <div
                className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Live Document Field Location Preview Card */}
        {currentField && (
          <div
            data-testid="document-location-preview"
            className="surface-card rounded-2xl p-5 space-y-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 flex items-center gap-1.5 min-w-0">
                <MapIcon className="h-3.5 w-3.5 text-indigo-600 shrink-0" />
                <span className="truncate">Document Placement</span>
              </span>
              <div className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 p-0.5 shrink-0">
                {canNavigatePages && (
                  <button
                    type="button"
                    aria-label="Previous PDF page"
                    disabled={activePage <= 1}
                    onClick={() => onChangePreviewPage?.(Math.max(1, activePage - 1))}
                    className="rounded-md p-1 text-slate-600 hover:bg-white hover:text-slate-900 disabled:opacity-35 cursor-pointer transition-colors"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </button>
                )}
                <span className="px-1.5 text-[11px] font-mono font-semibold text-slate-700 tabular-nums whitespace-nowrap">
                  {totalPages > 1 ? `${activePage} / ${totalPages}` : `Page ${activePage}`}
                </span>
                {canNavigatePages && (
                  <button
                    type="button"
                    aria-label="Next PDF page"
                    disabled={activePage >= totalPages}
                    onClick={() =>
                      onChangePreviewPage?.(Math.min(totalPages, activePage + 1))
                    }
                    className="rounded-md p-1 text-slate-600 hover:bg-white hover:text-slate-900 disabled:opacity-35 cursor-pointer transition-colors"
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>

            {(() => {
              const previewUrl = pagePreviewUrls[activePage];
              const pageW = currentField.pageWidthPt || 595;
              const pageH = currentField.pageHeightPt || 842;
              const box = currentField.inputBoundingBox;

              const topPct = box
                ? Math.min(Math.max((box.y / pageH) * 100, 1), 96)
                : Math.min(
                    Math.max(18 + (completed / Math.max(total, 1)) * 64, 18),
                    82,
                  );
              const leftPct = box
                ? Math.min(Math.max((box.x / pageW) * 100, 1), 96)
                : 10;
              const widthPct = box
                ? Math.min(Math.max((box.width / pageW) * 100, 2), 99 - leftPct)
                : 80;
              const heightPct = box
                ? Math.min(Math.max((box.height / pageH) * 100, 1.4), 30)
                : 5;

              if (previewUrl) {
                return (
                  <div className="space-y-2">
                    <button
                      type="button"
                      data-testid="enlarge-pdf-preview"
                      onClick={onOpenZoom}
                      className="group relative mx-auto block w-full overflow-hidden rounded-xl border border-slate-300 bg-white shadow-xs transition-all hover:border-indigo-500 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      title="Click to enlarge official PDF page"
                    >
                      <img
                        src={previewUrl}
                        alt={`Official PDF page ${activePage}`}
                        className="block w-full h-auto select-none"
                      />
                      {showHighlightOnActivePage && (
                        <div
                          data-testid="pdf-field-highlight-box"
                          style={{
                            top: `${topPct}%`,
                            left: `${leftPct}%`,
                            width: `${widthPct}%`,
                            height: `${heightPct}%`,
                          }}
                          className="pointer-events-none absolute rounded-[2px] border-2 border-indigo-600 bg-indigo-500/25 shadow-[0_0_0_2px_rgba(79,70,229,0.25)] transition-all duration-300"
                        />
                      )}
                      <span className="absolute bottom-2 end-2 rounded-md bg-slate-900/75 px-2 py-0.5 text-[10px] font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100">
                        Click to enlarge
                      </span>
                    </button>
                  </div>
                );
              }

              return (
                <div className="relative mx-auto h-36 w-28 rounded-lg border border-slate-300 bg-white shadow-2xs overflow-hidden p-2">
                  <div className="h-2 w-12 rounded-[2px] bg-slate-300 mb-2" />
                  <div className="space-y-1.5">
                    <div className="h-1 w-full rounded-[2px] bg-slate-100" />
                    <div className="h-1 w-5/6 rounded-[2px] bg-slate-100" />
                    <div className="h-1 w-full rounded-[2px] bg-slate-100" />
                    <div className="h-1 w-4/5 rounded-[2px] bg-slate-100" />
                    <div className="h-1 w-full rounded-[2px] bg-slate-100" />
                    <div className="h-1 w-3/4 rounded-[2px] bg-slate-100" />
                  </div>
                  <div
                    style={{
                      top: `${topPct}%`,
                      left: `${leftPct}%`,
                      width: `${widthPct}%`,
                    }}
                    className="absolute h-4 rounded-[2px] border-2 border-indigo-600 bg-indigo-500/20 flex items-center px-1 transition-all duration-300"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 shrink-0" />
                  </div>
                </div>
              );
            })()}

            <p className="text-[11px] text-slate-600 leading-snug text-center break-words">
              {currentField.sourceDocumentFilename ? (
                <>
                  Mapped to{" "}
                  <span className="font-semibold text-slate-800 break-all">
                    {currentField.sourceDocumentFilename}
                  </span>
                </>
              ) : (
                <>
                  Active field{" "}
                  <span className="font-mono font-semibold text-slate-800">
                    #{completed + 1}
                  </span>{" "}
                  on official PDF template
                </>
              )}
            </p>
          </div>
        )}

        {/* Multilingual Normalization Guidance Card */}
        <div className="surface-card rounded-2xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-indigo-600">
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.75}
                d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
              />
            </svg>
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
              Multilingual Normalization
            </h4>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Answer in your own language. Your original wording is preserved
            while canonical dates, currencies, and choices are formatted for the
            target form.
          </p>
        </div>

        {/* Privacy Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 flex items-center gap-3 shadow-2xs">
          <div className="h-8 w-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.75}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <div className="text-xs text-slate-600 leading-snug">
            <span className="font-semibold text-slate-900 block">
              Zero-Retention Guarantee
            </span>
            Your session is temporary and protected by ownership credentials.
          </div>
        </div>
      </aside>

      {/* Full-Resolution PDF Page Zoom Modal */}
      {zoomedPreviewOpen && currentField && (
          <div
            data-testid="pdf-preview-modal"
            onClick={onCloseZoom}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4 backdrop-blur-sm"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
            >
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-3.5">
                <div className="space-y-0.5 text-start min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">
                    Official Document Placement • Page {activePage}
                    {totalPages > 1 ? ` of ${totalPages}` : ""}
                  </p>
                  <p className="text-sm font-bold text-slate-900 truncate">
                    {currentField.label}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {canNavigatePages && (
                    <div className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5">
                      <button
                        type="button"
                        aria-label="Previous page"
                        disabled={activePage <= 1}
                        onClick={() => onChangePreviewPage?.(Math.max(1, activePage - 1))}
                        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-white disabled:opacity-40 cursor-pointer"
                      >
                        <ChevronLeft className="h-3.5 w-3.5" />
                        Prev
                      </button>
                      <span className="px-2 text-xs font-mono font-semibold text-slate-700 tabular-nums">
                        {activePage} / {totalPages}
                      </span>
                      <button
                        type="button"
                        aria-label="Next page"
                        disabled={activePage >= totalPages}
                        onClick={() =>
                          onChangePreviewPage?.(Math.min(totalPages, activePage + 1))
                        }
                        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-white disabled:opacity-40 cursor-pointer"
                      >
                        Next
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                  {!showHighlightOnActivePage && onChangePreviewPage && (
                    <button
                      type="button"
                      onClick={() => onChangePreviewPage(fieldPage)}
                      className="rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 cursor-pointer"
                    >
                      Go to field (p. {fieldPage})
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={onCloseZoom}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
              <div className="overflow-y-auto p-4 sm:p-6 bg-slate-100/70">
                {(() => {
                  const previewUrl = pagePreviewUrls[activePage];
                  if (!previewUrl) {
                    return (
                      <div className="flex flex-col items-center justify-center py-20 text-slate-500 gap-2">
                        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                        <span className="text-xs font-medium">
                          Loading page {activePage} preview...
                        </span>
                      </div>
                    );
                  }
                  const pageW = currentField.pageWidthPt || 595;
                  const pageH = currentField.pageHeightPt || 842;
                  const box = currentField.inputBoundingBox;
                  const topPct = box
                    ? Math.min(Math.max((box.y / pageH) * 100, 1), 96)
                    : 20;
                  const leftPct = box
                    ? Math.min(Math.max((box.x / pageW) * 100, 1), 96)
                    : 10;
                  const widthPct = box
                    ? Math.min(
                        Math.max((box.width / pageW) * 100, 2),
                        99 - leftPct,
                      )
                    : 80;
                  const heightPct = box
                    ? Math.min(Math.max((box.height / pageH) * 100, 1.4), 30)
                    : 5;

                  return (
                    <div className="relative mx-auto w-fit h-fit rounded-lg border border-slate-300 bg-white shadow-md">
                      <img
                        src={previewUrl}
                        alt={`Official PDF page ${activePage} enlarged`}
                        className="block max-w-full h-auto rounded-lg select-none"
                      />
                      {showHighlightOnActivePage && (
                        <div
                          style={{
                            top: `${topPct}%`,
                            left: `${leftPct}%`,
                            width: `${widthPct}%`,
                            height: `${heightPct}%`,
                          }}
                          className="pointer-events-none absolute rounded-[2px] border-2 border-indigo-600 bg-indigo-500/25 shadow-[0_0_0_4px_rgba(79,70,229,0.28)]"
                        />
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        )}
    </>
  );
}
