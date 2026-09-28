export function accessHeaders(): Record<string,string> {
  if (typeof window === "undefined") return {};
  const token = sessionStorage.getItem("agent-api-token");
  return token ? {"X-API-Key":token} : {};
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function apiUrl(path: string) {
  const base = API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${base}${normalizedPath}`;
}

async function parseResponse(response: Response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export function responseErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const data = payload as Record<string, unknown>;
  if (typeof data.detail === "string") return data.detail;
  if (typeof data.message === "string") return data.message;
  return null;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      Accept: "application/json",
      ...accessHeaders(),
      ...(options.body
        ? {
            "Content-Type": "application/json",
          }
        : {}),
      ...options.headers,
    },
  });

  const payload = await parseResponse(response);

  if (!response.ok) {
    throw new ApiError(
      responseErrorMessage(payload) || response.statusText || "Request failed",
      response.status,
      payload,
    );
  }

  return payload as T;
}

export function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    const detail = responseErrorMessage(error.payload);
    if (detail) return detail;
    if (error.status === 404) {
      return "Backend route is not available.";
    }

    return `Backend returned ${error.status}.`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Backend request failed.";
}