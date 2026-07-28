/**
 * Gate for the Phase 11 technical field-review screen. Normal users never
 * see it (Phase 13); it stays reachable for admin/development/debug use
 * via an explicit build-time flag, or a `?debug=1` query param that only
 * works outside production.
 */
export function isDetectionDebugUiEnabled(): boolean {
  if (process.env.NEXT_PUBLIC_ENABLE_DETECTION_DEBUG_UI === "true") {
    return true;
  }
  if (process.env.NODE_ENV !== "production" && typeof window !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    return params.get("debug") === "1";
  }
  return false;
}
