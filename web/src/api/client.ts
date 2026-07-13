import type { components } from "./schema";

export type Job = components["schemas"]["JobResponse"];
export type Check = components["schemas"]["CheckResponse"];
export type ConfigRequest = components["schemas"]["ConfigRequest"];
export type Event = components["schemas"]["EventResponse"];
export type ExportResult = components["schemas"]["ExportResponse"];
export type FileResult = components["schemas"]["FileResultResponse"];
export type Report = components["schemas"]["ReportResponse"];
export type ReviewRequest = components["schemas"]["ReviewRequest"];
export type RuntimeStatus = components["schemas"]["RuntimeStatusResponse"];

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";
const SESSION_TOKEN = import.meta.env.VITE_VOCALSIEVE_TOKEN ?? "";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "X-VocalSieve-Token": SESSION_TOKEN };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const payload = (await response.json().catch(() => null)) as
    | { error?: { message?: string; action?: string } }
    | null;
  if (!response.ok) {
    const message = payload?.error?.message ?? response.statusText;
    const action = payload?.error?.action;
    throw new Error(`${response.status} ${message}${action ? ` ${action}` : ""}`);
  }
  return payload as T;
}

const jobPath = (jobId: string) => `/api/v1/jobs/${encodeURIComponent(jobId)}`;

export const api = {
  base: API_BASE,
  health: () => request<components["schemas"]["HealthResponse"]>("/api/v1/health"),
  doctor: () => request<Check[]>("/api/v1/doctor"),
  runtime: () => request<RuntimeStatus>("/api/v1/runtime"),
  jobs: () => request<Job[]>("/api/v1/jobs"),
  job: (jobId: string) => request<Job>(jobPath(jobId)),
  createJob: (config: ConfigRequest) =>
    request<Job>("/api/v1/jobs", { method: "POST", body: config }),
  cancelJob: (jobId: string) =>
    request<Job>(`${jobPath(jobId)}/cancel`, { method: "POST" }),
  resumeJob: (jobId: string) =>
    request<Job>(`${jobPath(jobId)}/resume`, { method: "POST" }),
  exportJob: (jobId: string) =>
    request<ExportResult>(`${jobPath(jobId)}/export`, { method: "POST" }),
  report: (jobId: string) => request<Report>(`${jobPath(jobId)}/report`),
  results: (jobId: string) => request<FileResult[]>(`${jobPath(jobId)}/results`),
  reviewResult: (jobId: string, review: ReviewRequest) =>
    request<FileResult>(`${jobPath(jobId)}/results/review`, {
      method: "POST",
      body: review,
    }),
  events(jobId: string, after = 0): WebSocket {
    const url = new URL(`${API_BASE.replace(/^http/, "ws")}${jobPath(jobId)}/events`);
    url.searchParams.set("token", SESSION_TOKEN);
    if (after > 0) url.searchParams.set("after", String(after));
    return new WebSocket(url);
  },
};
