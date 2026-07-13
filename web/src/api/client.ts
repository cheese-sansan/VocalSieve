import type { components } from "./schema";

export type Job = components["schemas"]["JobResponse"];
export type Check = components["schemas"]["CheckResponse"];
export type Event = {
  id: number;
  job_id: string;
  type: string;
  stage: string | null;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";
const SESSION_TOKEN = import.meta.env.VITE_VOCALSIEVE_TOKEN ?? "";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "X-VocalSieve-Token": SESSION_TOKEN },
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export const api = {
  base: API_BASE,
  health: () => request<components["schemas"]["HealthResponse"]>("/api/v1/health"),
  doctor: () => request<Check[]>("/api/v1/doctor"),
  jobs: () => request<Job[]>("/api/v1/jobs"),
  events(jobId: string): WebSocket {
    const url = new URL(`${API_BASE.replace(/^http/, "ws")}/api/v1/jobs/${jobId}/events`);
    url.searchParams.set("token", SESSION_TOKEN);
    return new WebSocket(url);
  },
};
