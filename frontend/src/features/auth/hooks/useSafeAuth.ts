import { useAuth } from "../context/AuthProvider";

/**
 * Reads AuthContext via `useAuth()`, returning `null` when rendered outside an
 * `<AuthProvider>` (such as isolated component tests) while still respecting
 * partial `vi.mock("@/features/auth/context/AuthProvider")` overrides that
 * only stub `useAuth`.
 */
export function useSafeAuth() {
  try {
    return useAuth();
  } catch {
    return null;
  }
}
