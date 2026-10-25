"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

export type Stroke = Array<[number, number]>;

export interface SignatureValue {
  strokes: Stroke[];
  width: number;
  height: number;
}

const MAX_STROKES = 200;
const MAX_POINTS_PER_STROKE = 2000;

const CANVAS_WIDTH = 600;
const CANVAS_HEIGHT = 200;

interface SignaturePadProps {
  fieldKey: string;
  value: SignatureValue | null;
  onChange: (value: SignatureValue | null) => void;
  onSignAfterPrinting: () => void;
  pendingManualSignature?: boolean;
  disabled?: boolean;
  error?: string;
}

export function SignaturePad({
  fieldKey,
  value,
  onChange,
  onSignAfterPrinting,
  pendingManualSignature = false,
  disabled = false,
  error,
}: SignaturePadProps) {
  const t = useTranslations("signature");
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>(value?.strokes ?? []);
  const drawingRef = useRef<Stroke | null>(null);

  const redraw = useCallback((allStrokes: Stroke[]) => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.lineWidth = 2.75;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.strokeStyle = "#1e293b";
    for (const stroke of allStrokes) {
      if (stroke.length === 0) continue;
      context.beginPath();
      context.moveTo(stroke[0][0], stroke[0][1]);
      for (const [x, y] of stroke.slice(1)) {
        context.lineTo(x, y);
      }
      if (stroke.length === 1) {
        context.lineTo(stroke[0][0] + 0.1, stroke[0][1] + 0.1);
      }
      context.stroke();
    }
  }, []);

  useEffect(() => {
    const nextStrokes = value?.strokes ?? [];
    setStrokes(nextStrokes);
    redraw(nextStrokes);
  }, [value, redraw]);

  const pointFrom = (
    event: React.PointerEvent<HTMLCanvasElement>
  ): [number, number] => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * canvas.height;
    return [
      Math.min(Math.max(x, 0), canvas.width),
      Math.min(Math.max(y, 0), canvas.height),
    ];
  };

  const commit = (allStrokes: Stroke[]) => {
    setStrokes(allStrokes);
    redraw(allStrokes);
    onChange(
      allStrokes.length === 0
        ? null
        : { strokes: allStrokes, width: CANVAS_WIDTH, height: CANVAS_HEIGHT }
    );
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (disabled || strokes.length >= MAX_STROKES) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    drawingRef.current = [pointFrom(event)];
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const current = drawingRef.current;
    if (!current || current.length >= MAX_POINTS_PER_STROKE) return;
    current.push(pointFrom(event));
    redraw([...strokes, current]);
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const current = drawingRef.current;
    drawingRef.current = null;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    if (!current || current.length === 0) return;
    commit([...strokes, current]);
  };

  const handleClear = () => commit([]);
  const handleUndo = () => commit(strokes.slice(0, -1));

  const hasSignature = strokes.length > 0;

  return (
    <div className="space-y-3.5">
      {pendingManualSignature && !hasSignature ? (
        <div
          data-testid="signature-pending-manual"
          className="rounded-xl border border-amber-300 bg-amber-50 p-3.5 text-sm text-amber-900 flex items-center gap-3"
        >
          <svg
            className="h-4 w-4 text-amber-600 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
            />
          </svg>
          <span>{t("willSignAfterPrinting")}</span>
        </div>
      ) : null}

      <div className="relative rounded-xl border border-slate-300 bg-slate-50 p-1.5 shadow-inner">
        <canvas
          ref={canvasRef}
          data-testid="signature-canvas"
          width={CANVAS_WIDTH}
          height={CANVAS_HEIGHT}
          role="img"
          aria-label={t("padLabel")}
          className="w-full max-w-full touch-none rounded-lg bg-white border border-slate-200 cursor-crosshair"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        />

        <div className="pointer-events-none absolute bottom-5 inset-x-6 flex items-center gap-2 opacity-60">
          <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">
            ✕
          </span>
          <div className="flex-1 border-b border-dashed border-slate-300" />
        </div>
      </div>

      <p id={`signature-help-${fieldKey}`} className="text-xs text-slate-500">
        {t("instructions")}
      </p>

      {error ? (
        <p
          className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-800 flex items-center gap-2"
          role="alert"
        >
          <svg
            className="h-4 w-4 shrink-0 text-rose-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{error}</span>
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2 pt-1">
        <button
          type="button"
          data-testid="signature-clear"
          disabled={disabled || !hasSignature}
          onClick={handleClear}
          className="btn-secondary px-3.5 py-2 text-xs"
        >
          {t("clear")}
        </button>
        <button
          type="button"
          data-testid="signature-undo"
          disabled={disabled || !hasSignature}
          onClick={handleUndo}
          className="btn-secondary px-3.5 py-2 text-xs"
        >
          {t("undo")}
        </button>
        <button
          type="button"
          data-testid="signature-sign-after-printing"
          disabled={disabled}
          onClick={onSignAfterPrinting}
          className="btn-secondary px-3.5 py-2 text-xs"
        >
          {t("signAfterPrinting")}
        </button>
      </div>
    </div>
  );
}
