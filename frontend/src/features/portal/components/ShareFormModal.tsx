/* eslint-disable @next/next/no-img-element */
"use client";

import React, { useState } from "react";
import {
  Check,
  Code,
  Copy,
  Download,
  ExternalLink,
  FileDown,
  Printer,
  QrCode,
  X,
} from "lucide-react";

interface ShareFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  form: {
    id: string;
    key: string;
    name: string;
    status?: string;
  };
  orgSlug?: string;
}

export function ShareFormModal({
  isOpen,
  onClose,
  form,
  orgSlug,
}: ShareFormModalProps) {
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedEmbed, setCopiedEmbed] = useState(false);

  if (!isOpen) return null;

  // Determine permalink URL
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const formPath = orgSlug ? `/f/${orgSlug}/${form.key}` : `/f/${form.key}`;
  const fullShareUrl = `${origin}${formPath}`;

  const qrPngUrl = `/api/public/forms/${form.key}/qr?format=png`;
  const qrSvgUrl = `/api/public/forms/${form.key}/qr?format=svg`;
  const counterPosterPdfUrl = `/api/public/forms/${form.key}/counter-poster.pdf`;

  const embedSnippet = `<a href="${fullShareUrl}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:8px;padding:8px 16px;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:10px;font-family:sans-serif;font-size:13px;font-weight:600;">
  <span>${form.name}</span>
</a>`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(fullShareUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleCopyEmbed = async () => {
    try {
      await navigator.clipboard.writeText(embedSnippet);
      setCopiedEmbed(true);
      setTimeout(() => setCopiedEmbed(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-7 space-y-6 animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <QrCode className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-bold text-slate-900">
                Share Form & Counter QR Code
              </h3>
              <p className="text-xs text-slate-500 truncate max-w-xs sm:max-w-sm">
                {form.name}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 1. Direct Citizen Link */}
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Direct Permalinks for Citizens:
          </label>
          <div className="flex items-center gap-2 min-w-0">
            <input
              type="text"
              readOnly
              value={fullShareUrl}
              className="min-w-0 flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-mono text-slate-800 focus:outline-none select-all"
            />
            <button
              type="button"
              onClick={handleCopyLink}
              aria-label="Copy Link"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer shrink-0"
            >
              {copiedLink ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy<span className="sr-only"> Link</span></span>
                </>
              )}
            </button>
            <a
              href={fullShareUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
              title="Open Link in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* 2. QR Code Preview & Downloads */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-200">
          <div className="flex flex-col items-center justify-center bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
            <img
              src={qrPngUrl}
              alt={`QR Code for ${form.name}`}
              className="w-36 h-36 object-contain"
            />
            <span className="text-[10px] font-mono text-slate-400 mt-1">
              Scan with Smartphone Camera
            </span>
          </div>

          <div className="flex flex-col justify-center space-y-2.5">
            <div>
              <span className="text-xs font-bold text-slate-900 block">
                High-Resolution QR Codes
              </span>
              <p className="text-[11px] text-slate-500 leading-tight mt-0.5">
                Include in appointment emails, municipal leaflets, or service letters.
              </p>
            </div>

            <div className="flex flex-col gap-2 pt-1">
              <a
                href={qrPngUrl}
                download={`qr-${form.key}.png`}
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-blue-600" />
                <span><span className="sr-only">Download </span>PNG</span>
              </a>
              <a
                href={qrSvgUrl}
                download={`qr-${form.key}.svg`}
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
              >
                <FileDown className="w-3.5 h-3.5 text-indigo-600" />
                <span><span className="sr-only">Download </span>SVG</span>
              </a>
            </div>
          </div>
        </div>

        {/* 3. Printable A4 Counter Stand / Poster (PDF) */}
        <div className="p-4 rounded-2xl border border-emerald-200 bg-emerald-50/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <span className="text-xs font-bold text-emerald-950 flex items-center gap-1.5">
              <Printer className="w-4 h-4 text-emerald-700" />
              Printable Counter Stand (A4)
            </span>
            <p className="text-[11px] text-emerald-800 leading-snug max-w-sm">
              Ready-to-print poster with authority header, QR code, and citizen guidance in 8 languages.
            </p>
          </div>
          <a
            href={counterPosterPdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span><span className="sr-only">Download </span>Poster<span className="sr-only"> PDF</span></span>
          </a>
        </div>

        {/* 4. Embed Snippet */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Code className="w-3.5 h-3.5 text-slate-500" />
              Website Button Snippet (HTML):
            </label>
            <button
              type="button"
              onClick={handleCopyEmbed}
              className="text-[11px] font-semibold text-blue-600 hover:text-blue-800"
            >
              {copiedEmbed ? "Copied!" : "Copy Code"}
            </button>
          </div>
          <pre className="p-3 bg-slate-900 text-slate-200 rounded-xl text-[11px] font-mono overflow-x-auto leading-relaxed max-h-24">
            {embedSnippet}
          </pre>
        </div>

        {/* Modal Footer */}
        <div className="pt-2 border-t border-slate-100 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
