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
results, export, and job events. See `openapi.json` for exact schemas.

WebSockets use:

```text
ws://127.0.0.1:8765/api/v1/jobs/JOB_ID/events?token=TOKEN&after=EVENT_ID
```

Clients must send `Origin: http://127.0.0.1:5173` or
`Origin: http://localhost:5173`. `after` replays persisted events after the
specified event id. The browser skeleton reads its token from
`VITE_VOCALSIEVE_TOKEN` and never imports Python internals.
