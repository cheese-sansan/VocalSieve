import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  CheckCircle2,
  CircleAlert,
  Database,
  RefreshCw,
  Server,
  TerminalSquare,
} from "lucide-react";

import { api, type Check, type Event, type Job } from "./api/client";

function App() {
  const [online, setOnline] = useState(false);
  const [checks, setChecks] = useState<Check[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      await api.health();
      const [nextChecks, nextJobs] = await Promise.all([api.doctor(), api.jobs()]);
      setOnline(true);
      setChecks(nextChecks);
      setJobs(nextJobs);
      setError(null);
    } catch (cause) {
      setOnline(false);
      setError(cause instanceof Error ? cause.message : "Connection failed");
    }
  }, []);

  useEffect(() => void refresh(), [refresh]);
  useEffect(() => {
    if (!selectedJob) return;
    setEvents([]);
    const socket = api.events(selectedJob);
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as Event;
      setEvents((current) => [...current.slice(-99), event]);
    };
    return () => socket.close();
  }, [selectedJob]);

  const failedChecks = useMemo(() => checks.filter((check) => !check.ok), [checks]);

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
            <h1>Runtime overview</h1>
            <p>{api.base}</p>
          </div>
          <button className="icon-button" onClick={refresh} title="Refresh">
            <RefreshCw size={18} />
          </button>
        </header>

        {error && <div className="error-band"><CircleAlert size={18} /> {error}</div>}

        <section className="metrics" aria-label="Runtime status">
          <div><span>Environment</span><strong>{failedChecks.length ? "Attention" : "Ready"}</strong></div>
          <div><span>Recorded jobs</span><strong>{jobs.length}</strong></div>
          <div><span>Active jobs</span><strong>{jobs.filter((job) => job.status === "running").length}</strong></div>
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
          <div className="section-heading"><h2>Recent jobs</h2><span>Select a row to stream events</span></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>ID</th><th>Status</th><th>Stage</th><th>Source</th><th>Created</th></tr></thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} onClick={() => setSelectedJob(job.id)} className={selectedJob === job.id ? "selected" : ""}>
                    <td className="mono">{job.id.slice(0, 10)}</td><td>{job.status}</td>
                    <td>{job.current_stage ?? "-"}</td><td>{String(job.config.source_dir ?? "-")}</td>
                    <td>{job.created_at.slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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

