# Local API

Run `vocalsieve serve --port 8765`. Native mode binds only to `127.0.0.1` and
prints a random session token. Containers require `VOCALSIEVE_SESSION_TOKEN`.
Remote listening is intentionally unsupported in v0.9.

```powershell
$token = "the-token-printed-by-vocalsieve"
$headers = @{ "X-VocalSieve-Token" = $token }
Invoke-RestMethod http://127.0.0.1:8765/api/v1/doctor -Headers $headers
```

Create a job:

```powershell
$body = @{
  source_dir = "E:\data\raw"
  output_dir = "E:\data\screened"
  model_size = "small"
  device = "auto"
  top_n = 100
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  http://127.0.0.1:8765/api/v1/jobs `
  -Headers $headers -ContentType application/json -Body $body
```

The versioned surface is `/api/v1`: health, doctor, models, job lifecycle,
runtime capacity, results, review, export, and job events. See `openapi.json`
for exact schemas.

Runtime capacity is resource-aware and does not create a queue:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/v1/runtime -Headers $headers
```

The default is two active jobs and one CUDA job. TUI, API, SDK, and CLI processes
using the same SQLite database coordinate through database-backed resource leases.
Conflicting output paths and exhausted capacity return HTTP 409 without leaving a
new pending job.

Review a result after its job completes:

```powershell
$review = @{
  relative_path = "speaker/a.wav"
  decision = "exclude"
  note = "manual listening check"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  http://127.0.0.1:8765/api/v1/jobs/JOB_ID/results/review `
  -Headers $headers -ContentType application/json -Body $review
```

`decision` is `include`, `exclude`, or `automatic`. Automated status is retained;
the review changes only `effective_selected` and is recorded as an audit event.
The earlier `PATCH` form remains available as a deprecated compatibility alias.

Read the schema v2 aggregate report without exporting again:

```powershell
Invoke-RestMethod `
  http://127.0.0.1:8765/api/v1/jobs/JOB_ID/report `
  -Headers $headers
```

The report separates automatic selections, manual includes, manual excludes,
and the final effective selection count. It also records rejection counts,
thresholds, errors, and the effective transcription backend.

Expected API failures use the stable envelope
`{"error":{"code":"...","message":"...","action":"...","retryable":false}}`.

WebSockets use:

```text
ws://127.0.0.1:8765/api/v1/jobs/JOB_ID/events?token=TOKEN&after=EVENT_ID
```

Clients must send `Origin: http://127.0.0.1:5173` or
`Origin: http://localhost:5173`. `after` replays persisted events after the
specified event id. The experimental browser workspace reads its token from
`VITE_VOCALSIEVE_TOKEN`, consumes only generated OpenAPI types, and supports job
creation, cancel/resume, results, reporting, review, and re-export. It remains a
development preview rather than a Windows portable guarantee.
