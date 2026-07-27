import { z } from "zod";
import { getCsrfToken } from "@/features/auth/services/csrf";

export const ApplicationSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  formName: z.string(),
  formOrigin: z.string(),
  exportSupported: z.boolean(),
  progressPercentage: z.number(),
  createdAt: z.string(),
  updatedAt: z.string(),
  lastOpenedAt: z.string().nullable().optional(),
});

export type ApplicationSummary = z.infer<typeof ApplicationSummarySchema>;

export const ApplicationDetailSchema = ApplicationSummarySchema.extend({
  sourceLanguage: z.string(),
  userLanguage: z.string(),
  outputLanguage: z.string(),
  currentFieldPosition: z.number(),
  totalRequiredFields: z.number(),
  documentId: z.string().nullable().optional(),
});

export type ApplicationDetail = z.infer<typeof ApplicationDetailSchema>;

export class ApplicationsApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public errorCode: string | null = null
  ) {
    super(message);
    this.name = "ApplicationsApiError";
  }
}

async function applicationsRequest<T>(
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

  const response = await fetch(`/api/applications${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) {
    let detail = "unavailable";
    let errorCode: string | null = null;
    try {
      const data = await response.json();
      detail = data.detail || detail;
      errorCode = data.error_code || null;
    } catch {
      // ignore
    }
    throw new ApplicationsApiError(response.status, detail, errorCode);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();
  return schema ? schema.parse(data) : (data as T);
}

export async function listApplications(): Promise<ApplicationSummary[]> {
  return applicationsRequest(
    "",
    { method: "GET" },
    z.array(ApplicationSummarySchema)
  );
}

export async function getApplication(applicationId: string): Promise<ApplicationDetail> {
  return applicationsRequest(
    `/${applicationId}`,
    { method: "GET" },
    ApplicationDetailSchema
  );
}

export async function renameApplication(
  applicationId: string,
  title: string
): Promise<ApplicationSummary> {
  return applicationsRequest(
    `/${applicationId}`,
    { method: "PATCH", body: JSON.stringify({ title }) },
    ApplicationSummarySchema
  );
}

export async function deleteApplication(applicationId: string): Promise<void> {
  await applicationsRequest(`/${applicationId}`, { method: "DELETE" });
}

export async function claimApplication(
  sessionId: string,
  sessionToken: string,
  documentId?: string | null,
  documentToken?: string | null
): Promise<ApplicationDetail> {
  return applicationsRequest(
    "/claim",
    {
      method: "POST",
      body: JSON.stringify({
        sessionId,
        sessionToken,
        documentId: documentId || undefined,
        documentToken: documentToken || undefined,
      }),
    },
    ApplicationDetailSchema
  );
}
