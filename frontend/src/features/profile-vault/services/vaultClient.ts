import { z } from "zod";
import { getCsrfToken } from "@/features/auth/services/csrf";
import { getSessionToken } from "@/features/form-session/services/sessionCredentials";

export const ProfileVaultEntrySchema = z.object({
  questionKey: z.string(),
  fieldType: z.string(),
  value: z.string(),
  normalizedValue: z.any().nullable().optional(),
  valueLanguage: z.string(),
  updatedAt: z.string(),
});

export type ProfileVaultEntry = z.infer<typeof ProfileVaultEntrySchema>;

export const SaveSessionToVaultResponseSchema = z.object({
  savedCount: z.number(),
  savedKeys: z.array(z.string()),
});

export type SaveSessionToVaultResponse = z.infer<
  typeof SaveSessionToVaultResponseSchema
>;

export const PrefillSessionFromVaultResponseSchema = z.object({
  prefilledCount: z.number(),
  prefilledFieldKeys: z.array(z.string()),
});

export type PrefillSessionFromVaultResponse = z.infer<
  typeof PrefillSessionFromVaultResponseSchema
>;

export class VaultApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "VaultApiError";
  }
}

async function vaultRequest<T>(
  path: string,
  options: RequestInit = {},
  schema?: z.ZodSchema<T>,
  sessionId?: string,
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
  if (sessionId) {
    const sessionToken = getSessionToken(sessionId);
    if (sessionToken) {
      headers.set("X-Session-Token", sessionToken);
    }
  }

  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = "vault_error";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      // ignore non-JSON error body
    }
    throw new VaultApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();
  return schema ? schema.parse(data) : (data as T);
}

export async function listProfileVault(): Promise<ProfileVaultEntry[]> {
  return vaultRequest(
    "/profile-vault",
    { method: "GET" },
    z.array(ProfileVaultEntrySchema),
  );
}

export async function upsertProfileVaultEntry(
  questionKey: string,
  value: string,
  fieldType: string = "string",
  valueLanguage: string = "en",
): Promise<ProfileVaultEntry> {
  return vaultRequest(
    `/profile-vault/${encodeURIComponent(questionKey)}`,
    {
      method: "PUT",
      body: JSON.stringify({ value, fieldType, valueLanguage }),
    },
    ProfileVaultEntrySchema,
  );
}

export async function deleteProfileVaultEntry(
  questionKey: string,
): Promise<void> {
  await vaultRequest(`/profile-vault/${encodeURIComponent(questionKey)}`, {
    method: "DELETE",
  });
}

export async function clearProfileVault(): Promise<void> {
  await vaultRequest("/profile-vault", { method: "DELETE" });
}

export async function saveSessionToVault(
  sessionId: string,
): Promise<SaveSessionToVaultResponse> {
  return vaultRequest(
    `/form-sessions/${encodeURIComponent(sessionId)}/save-to-vault`,
    { method: "POST" },
    SaveSessionToVaultResponseSchema,
    sessionId,
  );
}

export async function prefillSessionFromVault(
  sessionId: string,
): Promise<PrefillSessionFromVaultResponse> {
  return vaultRequest(
    `/form-sessions/${encodeURIComponent(sessionId)}/prefill-from-vault`,
    { method: "POST" },
    PrefillSessionFromVaultResponseSchema,
    sessionId,
  );
}
