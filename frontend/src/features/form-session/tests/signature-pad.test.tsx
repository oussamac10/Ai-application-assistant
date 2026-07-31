import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { SignaturePad } from "../components/SignaturePad";

/**
 * The signature pad, and the equally prominent way not to use it.
 *
 * Electronic signing is never mandatory — even when the source PDF marks its
 * signature box required, that says the *printed* form must be signed, not that
 * it must be signed here. So "Sign after printing" sits beside the pad rather
 * than behind a disclosure, and is always enabled.
 *
 * Input is Pointer Events only: they cover mouse, touch and stylus in one path,
 * and separate mouse/touch handlers double-fire on hybrid devices, recording a
 * single stylus stroke twice.
 */

const translators = new Map<string, (key: string) => string>();
vi.mock("next-intl", () => ({
  useTranslations: (namespace = "") => {
    if (!translators.has(namespace)) {
      translators.set(namespace, (key: string) => key);
    }
    return translators.get(namespace)!;
  },
}));

// jsdom has no canvas backend; the component only needs the calls to succeed.
beforeEach(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
  })) as unknown as typeof HTMLCanvasElement.prototype.getContext;

  // jsdom lays nothing out, so every rect is zero-sized and the component's
  // canvas-space scaling would divide by zero. Patched on Element so the
  // lookup cannot miss it.
  Element.prototype.getBoundingClientRect = vi.fn(() => ({
    left: 0,
    top: 0,
    width: 600,
    height: 200,
    right: 600,
    bottom: 200,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  })) as unknown as typeof Element.prototype.getBoundingClientRect;
});

function renderPad(overrides: Partial<React.ComponentProps<typeof SignaturePad>> = {}) {
  const onChange = vi.fn();
  const onSignAfterPrinting = vi.fn();
  render(
    <SignaturePad
      fieldKey="signature"
      value={null}
      onChange={onChange}
      onSignAfterPrinting={onSignAfterPrinting}
      {...overrides}
    />,
  );
  return { onChange, onSignAfterPrinting };
}

/** Dispatches a pointer event carrying real coordinates.
 *
 * `fireEvent.pointerDown` builds a jsdom PointerEvent, which drops `clientX`
 * and `clientY` — every captured point came back NaN. A MouseEvent with the
 * pointer type name carries them properly, and React's synthetic pointer
 * handlers are attached by event name, so they still fire. */
function pointer(canvas: HTMLElement, type: string, x: number, y: number) {
  const event = new MouseEvent(type, {
    clientX: x,
    clientY: y,
    bubbles: true,
    cancelable: true,
  });
  Object.defineProperty(event, "pointerId", { value: 1 });
  fireEvent(canvas, event);
}

function draw(canvas: HTMLElement, points: Array<[number, number]>) {
  pointer(canvas, "pointerdown", points[0][0], points[0][1]);
  for (const [x, y] of points.slice(1)) {
    pointer(canvas, "pointermove", x, y);
  }
  const last = points[points.length - 1];
  pointer(canvas, "pointerup", last[0], last[1]);
}

describe("SignaturePad", () => {
  it("renders a canvas rather than a text input", () => {
    renderPad();

    expect(screen.getByTestId("signature-canvas")).toBeTruthy();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("records a stroke from pointer input", () => {
    const { onChange } = renderPad();

    draw(screen.getByTestId("signature-canvas"), [
      [10, 10],
      [50, 40],
      [90, 20],
    ]);

    expect(onChange).toHaveBeenCalled();
    const value = onChange.mock.calls.at(-1)![0];
    expect(value.strokes).toHaveLength(1);
    expect(value.strokes[0]).toHaveLength(3);
    // Stroke order is preserved — it is what makes the rendered signature look
    // like the one that was drawn.
    expect(value.strokes[0][0]).toEqual([10, 10]);
    expect(value.strokes[0][2]).toEqual([90, 20]);
    expect(value.width).toBe(600);
    expect(value.height).toBe(200);
  });

  it("keeps separate strokes separate", () => {
    const { onChange } = renderPad();
    const canvas = screen.getByTestId("signature-canvas");

    draw(canvas, [[10, 10], [20, 20]]);
    draw(canvas, [[60, 10], [70, 20]]);

    expect(onChange.mock.calls.at(-1)![0].strokes).toHaveLength(2);
  });

  it("clamps a stroke that leaves the canvas", () => {
    // Pointer capture keeps delivering events after the pointer leaves, and
    // the backend rejects any point outside the declared canvas.
    const { onChange } = renderPad();

    draw(screen.getByTestId("signature-canvas"), [
      [10, 10],
      [9999, -50],
    ]);

    const points = onChange.mock.calls.at(-1)![0].strokes[0];
    for (const [x, y] of points) {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(600);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(200);
    }
  });

  it("clears every stroke", () => {
    const { onChange } = renderPad();
    draw(screen.getByTestId("signature-canvas"), [[10, 10], [20, 20]]);

    fireEvent.click(screen.getByTestId("signature-clear"));

    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("undoes the last stroke only", () => {
    const { onChange } = renderPad();
    const canvas = screen.getByTestId("signature-canvas");
    draw(canvas, [[10, 10], [20, 20]]);
    draw(canvas, [[60, 10], [70, 20]]);

    fireEvent.click(screen.getByTestId("signature-undo"));

    expect(onChange.mock.calls.at(-1)![0].strokes).toHaveLength(1);
  });

  it("disables Clear and Undo until something is drawn", () => {
    renderPad();

    expect((screen.getByTestId("signature-clear") as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect((screen.getByTestId("signature-undo") as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("always offers Sign after printing, enabled", () => {
    // The product rule: electronic signing is never mandatory, so this is
    // never gated on anything.
    const { onSignAfterPrinting } = renderPad();

    const button = screen.getByTestId("signature-sign-after-printing");
    expect((button as HTMLButtonElement).disabled).toBe(false);

    fireEvent.click(button);
    expect(onSignAfterPrinting).toHaveBeenCalledTimes(1);
  });

  it("shows the manual-signing state when one was recorded", () => {
    renderPad({ pendingManualSignature: true });

    expect(screen.getByTestId("signature-pending-manual")).toBeTruthy();
  });

  it("hides the manual-signing note once a signature is drawn", () => {
    renderPad({ pendingManualSignature: true });

    draw(screen.getByTestId("signature-canvas"), [[10, 10], [20, 20]]);

    expect(screen.queryByTestId("signature-pending-manual")).toBeNull();
  });

  it("ignores a pointer-up that never drew anything", () => {
    const { onChange } = renderPad();

    pointer(screen.getByTestId("signature-canvas"), "pointerup", 0, 0);

    expect(onChange).not.toHaveBeenCalled();
  });

  it("exposes an accessible label and instructions", () => {
    renderPad();

    expect(screen.getByRole("img")).toBeTruthy();
    expect(screen.getByText("instructions")).toBeTruthy();
  });

  it("never renders the captured coordinates as text", () => {
    // Signature data is biometric. It must not leak into the DOM as debug
    // output.
    renderPad();
    draw(screen.getByTestId("signature-canvas"), [[123, 45]]);

    expect(document.body.textContent).not.toContain("123");
  });
});
