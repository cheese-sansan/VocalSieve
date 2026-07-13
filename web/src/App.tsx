import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Check,
  CheckCircle2,
  CircleAlert,
  Database,
  Download,
  FileText,
  Play,
  RefreshCw,
  RotateCcw,
  Server,
  Square,
  TerminalSquare,
  Undo2,
  X,
} from "lucide-react";

import {
  api,
  type Check as DiagnosticCheck,
  type ConfigRequest,
  type Event,
  type ExportResult,
  type FileResult,
  type Job,
  type Report,
  type ReviewRequest,
  type RuntimeStatus,
} from "./api/client";

const defaultConfig: ConfigRequest = {
  source_dir: "",
  output_dir: "",
  model_size: "small",
  device: "auto",
  compute_type: "auto",
  language: "auto",
  top_n: 1200,
  min_duration: 0.4,
  min_rms: 0.015,
  min_centroid: 1000,
  no_speech_threshold: 0.45,
  min_text_length: 2,
  max_text_length: 40,
  repeat_char_threshold: 4,
  ideal_text_length: 10,
  physics_workers: 4,
};

function formatNumber(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "-" : value.toFixed(digits);
}

function App() {
  const [online, setOnline] = useState(false);
  const [checks, setChecks] = useState<DiagnosticCheck[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [results, setResults] = useState<FileResult[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [form, setForm] = useState<ConfigRequest>(defaultConfig);
  const [exportResult, setExportResult] = useState<ExportResult | null>(null);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      await api.health();
      const [nextChecks, nextRuntime, nextJobs] = await Promise.all([
        api.doctor(),
        api.runtime(),
        api.jobs(),
      ]);
      setOnline(true);
      setChecks(nextChecks);
      setRuntime(nextRuntime);
      setJobs(nextJobs);
      setError(null);
    } catch (cause) {
      setOnline(false);
      setError(cause instanceof Error ? cause.message : "Connection failed");
    }
  }, []);

  const loadJobDetails = useCallback(async (jobId: string) => {
    try {
      const [nextResults, nextReport] = await Promise.all([api.results(jobId), api.report(jobId)]);
      setResults(nextResults);
      setReport(nextReport);
      setExportResult(null);
      setError(null);
    } catch (cause) {
      setResults([]);
      setReport(null);
      setError(cause instanceof Error ? cause.message : "Could not load job details");
    }
  }, []);

  useEffect(() => void refresh(), [refresh]);
  useEffect(() => {
    if (!jobs.some((job) => ["pending", "running", "cancelling"].includes(job.status))) return;
    const timer = window.setInterval(() => void refresh(), 2500);
    return () => window.clearInterval(timer);
  }, [jobs, refresh]);
  useEffect(() => {
    if (!selectedJob) return;
    setEvents([]);
    void loadJobDetails(selectedJob);
    const socket = api.events(selectedJob);
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as Event;
      setEvents((current) => [...current.slice(-99), event]);
      if (["job_completed", "job_failed", "job_cancelled", "review_changed"].includes(event.type)) {
        void refresh();
        void loadJobDetails(selectedJob);
      }
    };
    return () => socket.close();
  }, [loadJobDetails, refresh, selectedJob]);

  const failedChecks = useMemo(() => checks.filter((check) => !check.ok), [checks]);
  const selected = useMemo(
    () => jobs.find((job) => job.id === selectedJob) ?? null,
    [jobs, selectedJob],
  );

  const updateField = (field: keyof ConfigRequest, value: string) => {
    const numericFields = new Set<keyof ConfigRequest>([
      "top_n",
      "min_duration",
      "min_rms",
      "min_centroid",
      "no_speech_threshold",
      "min_text_length",
      "max_text_length",
      "repeat_char_threshold",
      "ideal_text_length",
      "physics_workers",
    ]);
    setForm((current) => ({
      ...current,
      [field]: numericFields.has(field) ? Number(value) : value,
    }));
  };

  const runAction = async (key: string, action: () => Promise<unknown>, message: string) => {
    setBusyAction(key);
    setActionMessage(null);
    try {
      await action();
      setActionMessage(message);
      await refresh();
      if (selectedJob) await loadJobDetails(selectedJob);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Action failed");
    } finally {
      setBusyAction(null);
    }
  };

  const createJob = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusyAction("create");
    setActionMessage(null);
    try {
      const job = await api.createJob(form);
      setSelectedJob(job.id);
      setActionMessage(`Created job ${job.id.slice(0, 10)}.`);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create job");
    } finally {
      setBusyAction(null);
    }
  };

  const reviewResult = async (result: FileResult, decision: ReviewRequest["decision"]) => {
    if (!selectedJob) return;
    const key = `review:${result.relative_path}`;
    await runAction(
      key,
      () =>
        api.reviewResult(selectedJob, {
          relative_path: result.relative_path,
          decision,
          note: reviewNote || null,
        }),
      `Updated review for ${result.relative_path}.`,
    );
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><TerminalSquare size={20} /> VocalSieve</div>
        <nav aria-label="Primary navigation">
          <button className="nav-item active"><Activity size={17} /> Overview</button>
          <button className="nav-item"><Database size={17} /> Jobs</button>
          <button className="nav-item"><Server size={17} /> Runtime</button>
        </nav>
        <div className={`connection ${online ? "ok" : "failed"}`}>
          <span className="status-dot" />
          {online ? "Local API connected" : "Local API offline"}
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <h1>Experimental web workspace</h1>
            <p>{api.base} · local paths and audio stay on this machine</p>
          </div>
          <button className="icon-button" onClick={() => void refresh()} title="Refresh">
            <RefreshCw size={18} />
          </button>
        </header>

        {error && <div className="error-band"><CircleAlert size={18} /> {error}</div>}
        {actionMessage && <div className="notice-band"><CheckCircle2 size={18} /> {actionMessage}</div>}

        <section className="metrics" aria-label="Runtime status">
          <div><span>Environment</span><strong>{failedChecks.length ? "Attention" : "Ready"}</strong></div>
          <div><span>Recorded jobs</span><strong>{jobs.length}</strong></div>
          <div><span>Active jobs</span><strong>{runtime?.active_jobs ?? 0}/{runtime?.max_active_jobs ?? "-"}</strong></div>
          <div><span>CUDA jobs</span><strong>{runtime?.active_cuda_jobs ?? 0}/{runtime?.max_cuda_jobs ?? "-"}</strong></div>
        </section>

        <section>
          <div className="section-heading"><h2>Create job</h2><span>Screen a local source folder</span></div>
          <form className="job-form" onSubmit={createJob}>
            <label className="wide">Source directory<input required value={form.source_dir} onChange={(event) => updateField("source_dir", event.target.value)} placeholder="E:\\data\\raw" /></label>
            <label className="wide">Output directory<input required value={form.output_dir} onChange={(event) => updateField("output_dir", event.target.value)} placeholder="E:\\data\\screened" /></label>
            <label>Model size<input value={form.model_size} onChange={(event) => updateField("model_size", event.target.value)} /></label>
            <label>Device<select value={form.device} onChange={(event) => updateField("device", event.target.value)}><option>auto</option><option>cpu</option><option>cuda</option></select></label>
            <label>Top N<input type="number" min={1} value={form.top_n} onChange={(event) => updateField("top_n", event.target.value)} /></label>
            <label>Min duration<input type="number" min={0} step={0.1} value={form.min_duration} onChange={(event) => updateField("min_duration", event.target.value)} /></label>
            <label>Min RMS<input type="number" min={0} step={0.001} value={form.min_rms} onChange={(event) => updateField("min_rms", event.target.value)} /></label>
            <label>No speech<input type="number" min={0} max={1} step={0.01} value={form.no_speech_threshold} onChange={(event) => updateField("no_speech_threshold", event.target.value)} /></label>
            <label>Min text<input type="number" min={1} value={form.min_text_length} onChange={(event) => updateField("min_text_length", event.target.value)} /></label>
            <label>Max text<input type="number" min={1} value={form.max_text_length} onChange={(event) => updateField("max_text_length", event.target.value)} /></label>
            <button className="primary wide" disabled={busyAction === "create"} type="submit"><Play size={16} /> {busyAction === "create" ? "Creating..." : "Create and run job"}</button>
          </form>
        </section>

        <section>
          <div className="section-heading"><h2>Environment</h2><span>{checks.length} checks</span></div>
          <div className="check-grid">
            {checks.map((check) => (
              <div className="check-row" key={check.name}>
                {check.ok ? <CheckCircle2 className="success" size={18} /> : <CircleAlert className="danger" size={18} />}
                <strong>{check.name}</strong><span>{check.detail}</span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="section-heading"><h2>Recent jobs</h2><span>Select a row to inspect and control it</span></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>ID</th><th>Status</th><th>Stage</th><th>Source</th><th>Created</th></tr></thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} onClick={() => setSelectedJob(job.id)} className={selectedJob === job.id ? "selected" : ""}>
                    <td className="mono">{job.id.slice(0, 10)}</td><td>{job.status}</td>
                    <td>{job.current_stage ?? "-"}</td><td>{job.config.source_dir}</td>
                    <td>{job.created_at.slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selected && (
            <div className="job-actions">
              <span className="mono">{selected.id}</span>
              <button disabled={selected.status !== "running" || busyAction !== null} onClick={() => void runAction("cancel", () => api.cancelJob(selected.id), "Cancellation requested.")}><Square size={15} /> Cancel</button>
              <button disabled={!(["cancelled", "failed"].includes(selected.status)) || busyAction !== null} onClick={() => void runAction("resume", () => api.resumeJob(selected.id), "Job resumed.")}><RotateCcw size={15} /> Resume</button>
              <button disabled={selected.status !== "completed" || busyAction !== null} onClick={() => void runAction("export", async () => setExportResult(await api.exportJob(selected.id)), "Selected files exported.")}><Download size={15} /> Re-export</button>
              {exportResult && <span>{exportResult.count} files written</span>}
            </div>
          )}
        </section>

        <section>
          <div className="section-heading"><h2>Job report</h2><span>{selected ? selected.id.slice(0, 10) : "No job selected"}</span></div>
          {report ? (
            <>
              <div className="report-grid">
                <div><span>Total scanned</span><strong>{report.total_scanned}</strong></div>
                <div><span>Candidates</span><strong>{report.candidate_count}</strong></div>
                <div><span>Automatic</span><strong>{report.automatic_selected_count}</strong></div>
                <div><span>Selected</span><strong>{report.selected_count}</strong></div>
                <div><span>Manual include</span><strong>{report.manual_include_count}</strong></div>
                <div><span>Manual exclude</span><strong>{report.manual_exclude_count}</strong></div>
                <div><span>Rejected</span><strong>{report.rejected_count}</strong></div>
                <div><span>Errors</span><strong>{report.error_count}</strong></div>
                <div><span>Pass rate</span><strong>{(report.candidate_pass_rate * 100).toFixed(1)}%</strong></div>
                <div><span>Avg duration</span><strong>{formatNumber(report.average_duration)}s</strong></div>
                <div><span>Backend</span><strong>{report.backend.effective_device}/{report.backend.effective_compute_type}</strong></div>
                <div><span>Fallback</span><strong>{report.backend.fallback ? report.backend.fallback_reason ?? "yes" : "no"}</strong></div>
              </div>
              <div className="rejection-list">
                {Object.entries(report.rejection_counts).length ? Object.entries(report.rejection_counts).map(([code, value]) => (
                  <div key={code}><b>{code}</b><span>{value.count} · {value.title}</span></div>
                )) : <p>No rejection codes recorded.</p>}
              </div>
            </>
          ) : <p className="empty-state">Select a job to load its aggregate report.</p>}
        </section>

        <section>
          <div className="section-heading"><h2>Results and review</h2><span>{results.length} rows</span></div>
          <label className="review-note">Review note (optional)<input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} maxLength={500} /></label>
          <div className="table-wrap results-table">
            <table>
              <thead><tr><th>Path</th><th>Status</th><th>Review</th><th>Duration</th><th>Score</th><th>Transcript</th><th>Actions</th></tr></thead>
              <tbody>
                {results.map((result) => (
                  <tr key={result.relative_path}>
                    <td>{result.relative_path}</td><td>{result.status}</td><td>{result.review_decision ?? "automatic"}</td>
                    <td>{formatNumber(result.duration)}</td><td>{formatNumber(result.score, 3)}</td><td>{result.transcription ?? "-"}</td>
                    <td className="review-actions">
                      <button title="Include" disabled={selected?.status !== "completed" || busyAction !== null} onClick={() => void reviewResult(result, "include")}><Check size={14} /></button>
                      <button title="Exclude" disabled={selected?.status !== "completed" || busyAction !== null} onClick={() => void reviewResult(result, "exclude")}><X size={14} /></button>
                      <button title="Automatic" disabled={selected?.status !== "completed" || busyAction !== null} onClick={() => void reviewResult(result, "automatic")}><Undo2 size={14} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!results.length && <p className="empty-state"><FileText size={16} /> No result rows loaded.</p>}
          </div>
        </section>

        <section>
          <div className="section-heading"><h2>Event stream</h2><span>{selectedJob ? selectedJob.slice(0, 10) : "No job selected"}</span></div>
          <div className="event-log">
            {events.length ? events.map((event) => (
              <div key={event.id}><time>{event.timestamp.slice(11, 19)}</time><b>{event.type}</b><span>{event.message}</span></div>
            )) : <p>Select a job to inspect its persisted event stream.</p>}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
