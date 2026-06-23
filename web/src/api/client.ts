import type { components } from "./schema";

export type Job = components["schemas"]["JobResponse"];
export type Check = components["schemas"]["CheckResponse"];
export type ConfigRequest = components["schemas"]["ConfigRequest"];
export type Event = components["schemas"]["EventResponse"];
export type ExportResult = components["schemas"]["ExportResponse"];
export type FileResult = components["schemas"]["FileResultResponse"];
export type Report = components["schemas"]["ReportResponse"];

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";
const SESSION_TOKEN = import.meta.env.VITE_VOCALSIEVE_TOKEN ?? "";

async function request<T>(
  path: string,
  options: { method?: "GET" | "POST"; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = { "X-VocalSieve-Token": SESSION_TOKEN };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}${detail ? `: ${detail}` : ""}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  base: API_BASE,
  health: () => request<components["schemas"]["HealthResponse"]>("/api/v1/health"),
  doctor: () => request<Check[]>("/api/v1/doctor"),
  jobs: () => request<Job[]>("/api/v1/jobs"),
  createJob: (config: ConfigRequest) =>
    request<Job>("/api/v1/jobs", { method: "POST", body: config }),
  exportJob: (jobId: string) =>
    request<ExportResult>(`/api/v1/jobs/${encodeURIComponent(jobId)}/export`, { method: "POST" }),
  report: (jobId: string) => request<Report>(`/api/v1/jobs/${encodeURIComponent(jobId)}/report`),
  results: (jobId: string) =>
    request<FileResult[]>(`/api/v1/jobs/${encodeURIComponent(jobId)}/results`),
  events(jobId: string, after = 0): WebSocket {
    const url = new URL(
      `${API_BASE.replace(/^http/, "ws")}/api/v1/jobs/${encodeURIComponent(jobId)}/events`,
    );
    url.searchParams.set("token", SESSION_TOKEN);
    if (after > 0) url.searchParams.set("after", String(after));
    return new WebSocket(url);
  },
};
