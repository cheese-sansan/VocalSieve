import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from vocalsieve.api import create_app
from vocalsieve.domain import FileStatus, JobStatus, PipelineConfig, RuntimePolicy, ScannedFile


def _payload(source: Path, output: Path) -> dict:
    return {
        "source_dir": str(source),
        "output_dir": str(output),
        "model_size": "tiny",
        "device": "cpu",
        "compute_type": "int8",
        "top_n": 10,
    }


def test_api_requires_token_for_writes_and_exposes_openapi(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    app = create_app(tmp_path / "state.db", session_token="test-token")
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["api_version"] == "v1"
        assert client.get("/api/v1/models").status_code == 401
        assert (
            client.get("/api/v1/models", headers={"X-VocalSieve-Token": "test-token"}).status_code
            == 200
        )
        runtime = client.get("/api/v1/runtime", headers={"X-VocalSieve-Token": "test-token"}).json()
        assert runtime["max_active_jobs"] == 2
        assert (
            client.post("/api/v1/jobs", json=_payload(source, tmp_path / "out")).status_code == 401
        )
        unauthorized = client.get("/api/v1/runtime")
        assert unauthorized.json()["error"]["code"] == "invalid_session_token"
        schema = client.get("/openapi.json").json()
        assert "/api/v1/jobs" in schema["paths"]
        assert schema["paths"]["/api/v1/jobs/{job_id}/results/review"]["patch"]["deprecated"]
        assert "post" in schema["paths"]["/api/v1/jobs/{job_id}/results/review"]
        assert "ReportResponse" in schema["components"]["schemas"]
        assert "EventResponse" in schema["components"]["schemas"]


def test_api_runs_empty_job_and_replays_events(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    app = create_app(tmp_path / "state.db", session_token="test-token")
    headers = {"X-VocalSieve-Token": "test-token"}
    with TestClient(app) as client:
        response = client.post("/api/v1/jobs", json=_payload(source, output), headers=headers)
        assert response.status_code == 202
        job_id = response.json()["id"]

        job: dict = {}
        for _ in range(100):
            job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
            if job["status"] == "completed":
                break
        assert job["status"] == "completed"
        assert client.get(f"/api/v1/jobs/{job_id}/results", headers=headers).json() == []
        report = client.get(f"/api/v1/jobs/{job_id}/report", headers=headers).json()
        assert report["schema_version"] == 2
        assert report["automatic_selected_count"] == 0
        assert report["manual_include_count"] == 0
        assert report["manual_exclude_count"] == 0
        exported = client.post(f"/api/v1/jobs/{job_id}/export", headers=headers)
        assert exported.json()["count"] == 0

        event_types = []
        try:
            with client.websocket_connect(
                f"/api/v1/jobs/{job_id}/events?token=test-token",
                headers={"origin": "http://127.0.0.1:5173"},
            ) as socket:
                while True:
                    event_types.append(socket.receive_json()["type"])
        except WebSocketDisconnect:
            pass
        assert event_types[0] == "job_started"
        assert event_types[-1] == "job_completed"

        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(
                f"/api/v1/jobs/{job_id}/events?token=wrong",
                headers={"origin": "http://127.0.0.1:5173"},
            ),
        ):
            pass

        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(
                f"/api/v1/jobs/{job_id}/events?token=test-token",
                headers={"origin": "https://example.com"},
            ),
        ):
            pass


def test_api_cors_allows_only_local_gui_origin(tmp_path: Path):
    app = create_app(tmp_path / "state.db", session_token="test-token")
    with TestClient(app) as client:
        allowed = client.options(
            "/api/v1/jobs",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        denied = client.options(
            "/api/v1/jobs",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
        assert "access-control-allow-origin" not in denied.headers


def test_api_maps_validation_not_found_and_state_errors(tmp_path: Path):
    app = create_app(tmp_path / "state.db", session_token="test-token")
    headers = {"X-VocalSieve-Token": "test-token"}
    with TestClient(app) as client:
        assert client.get("/api/v1/doctor", headers=headers).status_code == 200
        assert client.get("/api/v1/jobs", headers=headers).json() == []
        invalid = client.post(
            "/api/v1/jobs",
            json=_payload(tmp_path / "missing", tmp_path / "out"),
            headers=headers,
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "invalid_request"
        malformed = client.post(
            "/api/v1/jobs",
            json={"source_dir": str(tmp_path)},
            headers=headers,
        )
        assert malformed.status_code == 422
        assert malformed.json()["error"]["code"] == "invalid_request"
        assert client.get("/api/v1/jobs/missing", headers=headers).status_code == 404
        assert client.get("/api/v1/jobs/missing/results", headers=headers).status_code == 404
        assert client.get("/api/v1/jobs/missing/report", headers=headers).status_code == 404
        assert client.post("/api/v1/jobs/missing/export", headers=headers).status_code == 404
        assert client.post("/api/v1/jobs/missing/resume", headers=headers).status_code == 404
        assert client.post("/api/v1/jobs/missing/cancel", headers=headers).status_code == 404

        source = tmp_path / "source"
        source.mkdir()
        response = client.post(
            "/api/v1/jobs", json=_payload(source, tmp_path / "out"), headers=headers
        )
        job_id = response.json()["id"]
        for _ in range(100):
            job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
            if job["status"] == "completed":
                break
        assert client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers).status_code == 409


def test_api_rejects_a_second_active_job(tmp_path: Path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    app = create_app(
        tmp_path / "state.db",
        session_token="test-token",
        runtime_policy=RuntimePolicy(max_active_jobs=1, max_cuda_jobs=1),
    )
    release = threading.Event()
    monkeypatch.setattr(app.state.service, "run_reserved_job", lambda *_: release.wait(5))
    headers = {"X-VocalSieve-Token": "test-token"}
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/jobs", json=_payload(source, tmp_path / "one"), headers=headers
        )
        assert first.status_code == 202
        second = client.post(
            "/api/v1/jobs", json=_payload(source, tmp_path / "two"), headers=headers
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "capacity_exceeded"
        release.set()


def test_api_reviews_completed_result(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    audio = source / "a.wav"
    audio.write_bytes(b"audio")
    app = create_app(tmp_path / "state.db", session_token="test-token")
    service = app.state.service
    job = service.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    stat = audio.stat()
    service.database.upsert_scanned_file(
        job.id,
        ScannedFile("a.wav", audio, stat.st_size, stat.st_mtime_ns),
        job.config.cache_key,
    )
    service.database.update_file(job.id, "a.wav", status=FileStatus.SELECTED)
    service.database.set_job_state(job.id, JobStatus.COMPLETED)
    headers = {"X-VocalSieve-Token": "test-token"}
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/jobs/{job.id}/results/review",
            json={"relative_path": "a.wav", "decision": "exclude", "note": "reviewed"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["effective_selected"] is False
        assert response.json()["review_decision"] == "exclude"
        legacy = client.patch(
            f"/api/v1/jobs/{job.id}/results/review",
            json={"relative_path": "a.wav", "decision": "automatic"},
            headers=headers,
        )
        assert legacy.status_code == 200
        assert legacy.json()["effective_selected"] is True
        assert legacy.json()["review_decision"] is None

        report = client.get(f"/api/v1/jobs/{job.id}/report", headers=headers).json()
        assert report["selected_count"] == 1
        assert report["automatic_selected_count"] == 1
        assert report["manual_include_count"] == 0
        assert report["manual_exclude_count"] == 0
