import { z } from "zod";
import { getCsrfToken } from "./csrf";

export const UserSchema = z.object({
  id: z.string(),
  email: z.string(),
  createdAt: z.string(),
  lastLoginAt: z.string().nullable().optional(),
});

export type AuthUser = z.infer<typeof UserSchema>;

export class AuthApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public errorCode: string | null = null
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

async function authRequest<T>(
  path: string,
  options: RequestInit = {},
  schema?: z.ZodSchema<T>
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (options.method && options.method !== "GET") {
    const csrf = getCsrfToken();
    if (csrf) {
      headers.set("X-CSRF-Token", csrf);
    }
  }

  const response = await fetch(`/api/auth${path}`, {
    ...options,
    headers,
    // Explicit "include" (rather than the default/"same-origin") so the
    // HttpOnly auth cookie and CSRF cookie are always sent, regardless of
    // how this client is hosted relative to the API in the future.
    credentials: "include",
  });

  if (!response.ok) {
    let detail = "unauthorized";
    let errorCode: string | null = null;
    try {
      const data = await response.json();
      detail = data.detail || detail;
      errorCode = data.error_code || null;
    } catch {
      // ignore
    }
    throw new AuthApiError(response.status, detail, errorCode);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();
  return schema ? schema.parse(data) : (data as T);
}

export async function register(
  email: string,
  password: string,
  passwordConfirmation: string
): Promise<AuthUser> {
  return authRequest(
    "/register",
    {
      method: "POST",
      body: JSON.stringify({ email, password, passwordConfirmation }),
    },
    UserSchema
  );
}

export async function login(email: string, password: string): Promise<AuthUser> {
  return authRequest(
    "/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    UserSchema
  );
}

export async function logout(): Promise<void> {
  await authRequest("/logout", { method: "POST" });
}

// A 401 here is the normal logged-out state, not an application error — it
// resolves to `null` rather than rejecting. Any other failure (500, network
// error, malformed response) still rejects and must be handled as a real
// error by the caller.
//
// Concurrent callers (e.g. React Strict Mode's dev-only double effect
// invocation) share one in-flight request instead of firing two: the
// promise is cached until it settles, then cleared, so a later, genuinely
// separate call (e.g. AuthProvider.refresh() after login/logout) always
// starts a fresh request rather than replaying a stale result.
let inFlightGetCurrentUser: Promise<AuthUser | null> | null = null;

export async function getCurrentUser(): Promise<AuthUser | null> {
  if (inFlightGetCurrentUser) {
    return inFlightGetCurrentUser;
  }

  inFlightGetCurrentUser = (async () => {
    try {
      return await authRequest("/me", { method: "GET" }, UserSchema);
    } catch (err) {
      if (err instanceof AuthApiError && err.status === 401) {
        return null;
      }
      throw err;
    } finally {
      inFlightGetCurrentUser = null;
    }
  })();

  return inFlightGetCurrentUser;
}
