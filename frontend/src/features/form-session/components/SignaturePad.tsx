"use client";

import React, { useCallback, useRef, useState } from "react";
import { useTranslations } from "next-intl";

/**
 * A signature pad, and an equally prominent way not to use it.
 *
 * Electronic signing is never mandatory. Even when the source PDF marks its
 * signature box required, that says the *printed* document must be signed
 * before it counts — not that it must be signed here. Someone on a desktop with
 * a mouse, or with a motor impairment, or who simply prefers pen on paper, must
 * be able to continue. So "Sign after printing" sits beside the pad rather than
 * hidden behind it, and it is a completion rather than a skip.
 *
 * Input uses Pointer Events only. They cover mouse, touch and stylus in one
 * code path, which is not just less code: separate mouse and touch handlers
 * double-fire on hybrid devices, so a single stylus stroke would be recorded
 * twice.
 *
 * Strokes are kept as vectors. They render crisply at any export size, they are
 * a fraction of the size of a bitmap, and — because the payload can only hold
 * numbers — there is no way for markup or a data URI to travel inside one.
 * Nothing here records pressure, tilt or device identity: none of it improves a
 * rendered signature, and all of it would widen what a leak exposes.
 */

export type Stroke = Array<[number, number]>;

export interface SignatureValue {
  strokes: Stroke[];
  width: number;
  height: number;
}

// Mirrors the backend's limits (app/answers/signatures.py) so the pad refuses
// to build a payload the server would reject.
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
    context.lineWidth = 2.5;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.strokeStyle = "#e2e8f0";
    for (const stroke of allStrokes) {
      if (stroke.length === 0) continue;
      context.beginPath();
      context.moveTo(stroke[0][0], stroke[0][1]);
      for (const [x, y] of stroke.slice(1)) {
        context.lineTo(x, y);
      }
      // A single tap is a dot, not nothing — without this a deliberate mark
      // would vanish.
      if (stroke.length === 1) {
        context.lineTo(stroke[0][0] + 0.1, stroke[0][1] + 0.1);
      }
      context.stroke();
    }
  }, []);

  /** Canvas-space coordinates, clamped to the canvas.
   *
   * The element is responsive, so its rendered size differs from its backing
   * store; scaling here is what keeps a stroke drawn on a phone landing in the
   * same place as one drawn on a desktop. Clamping matters because a pointer
   * capture keeps delivering events after the pointer leaves the element, and
   * the backend rejects any point outside the declared canvas. */
  const pointFrom = (event: React.PointerEvent<HTMLCanvasElement>): [number, number] => {
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
        : { strokes: allStrokes, width: CANVAS_WIDTH, height: CANVAS_HEIGHT },
    );
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (disabled || strokes.length >= MAX_STROKES) return;
    // Capture keeps the stroke alive when the pointer leaves the canvas, so a
    // fast signature is not chopped at the edge.
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
    <div className="space-y-3">
      {pendingManualSignature && !hasSignature ? (
        <div
          data-testid="signature-pending-manual"
          className="rounded-xl border border-amber-800 bg-amber-950/20 p-4 text-sm text-amber-300"
        >
          {t("willSignAfterPrinting")}
        </div>
      ) : null}

      <canvas
        ref={canvasRef}
        data-testid="signature-canvas"
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        role="img"
        aria-label={t("padLabel")}
        // `touch-none` stops the browser scrolling the page instead of
        // delivering the pointer events a signature is made of.
        className="w-full max-w-full touch-none rounded-xl border border-slate-700 bg-slate-950 shadow-inner"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      />

      <p id={`signature-help-${fieldKey}`} className="text-xs text-slate-400">
        {t("instructions")}
      </p>

      {error ? (
        <p className="text-sm text-rose-400" role="alert">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          data-testid="signature-clear"
          disabled={disabled || !hasSignature}
          onClick={handleClear}
          className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm font-bold text-slate-300 transition hover:bg-slate-900 disabled:opacity-40 disabled:pointer-events-none"
        >
          {t("clear")}
        </button>
        <button
          type="button"
          data-testid="signature-undo"
          disabled={disabled || !hasSignature}
          onClick={handleUndo}
          className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm font-bold text-slate-300 transition hover:bg-slate-900 disabled:opacity-40 disabled:pointer-events-none"
        >
          {t("undo")}
        </button>
        {/* Always available, never behind a disclosure: signing on paper is a
            first-class way to complete the form, not a fallback. */}
        <button
          type="button"
          data-testid="signature-sign-after-printing"
          disabled={disabled}
          onClick={onSignAfterPrinting}
          className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm font-bold text-slate-300 transition hover:bg-slate-900 disabled:opacity-40 disabled:pointer-events-none"
        >
          {t("signAfterPrinting")}
        </button>
      </div>
    </div>
  );
}
