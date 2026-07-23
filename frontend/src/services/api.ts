export interface HealthResponse {
  status: string;
}

export interface DatabaseHealthResponse {
  status: string;
  database: string;
}

/**
 * Checks the general health of the backend API.
 * Returns true if connected, false otherwise.
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      return false;
    }
    const data: HealthResponse = await response.json();
    return data.status === "ok";
  } catch (error) {
    return false;
  }
}

/**
 * Checks the database connectivity health of the backend API.
 */
export async function checkDatabaseHealth(): Promise<DatabaseHealthResponse> {
  const response = await fetch("/api/health/database");
  if (!response.ok) {
    try {
      const errData = await response.json();
      return {
        status: errData.status || "error",
        database: errData.database || "unavailable",
      };
    } catch {
      throw new Error("Database health check failed with non-OK status");
    }
  }
  return response.json();
}
