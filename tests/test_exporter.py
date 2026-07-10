import json
from pathlib import Path

from vocalsieve.domain import PipelineConfig
from vocalsieve.exporter import build_report_summary, export_selected


def test_summary_counts_candidates_rejections_errors_and_fallback(tmp_path: Path):
    config = PipelineConfig(str(tmp_path), str(tmp_path / "out"), top_n=1)
    rows = [
        {"status": "selected", "duration": 1.0},
        {"status": "transcription_passed", "duration": 3.0},
        {"status": "physics_rejected", "reject_code": "energy_too_low", "duration": 2.0},
        {"status": "error", "reject_code": "physics_error"},
    ]
    events = [
        {
            "data": {
                "backend_fallback": True,
                "effective_device": "cpu",
                "effective_compute_type": "int8",
                "reason_code": "cudnn_unavailable",
            }
        }
    ]
    summary = build_report_summary("job-1", config, rows, events)
    assert summary["candidate_count"] == 2
    assert summary["selected_count"] == 1
    assert summary["automatic_selected_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["error_count"] == 1
    assert summary["candidate_pass_rate"] == 0.5
    assert summary["average_duration"] == 2.0
    assert summary["rejection_counts"]["energy_too_low"]["config_field"] == "min_rms"
    assert summary["backend"] == {
        "requested_device": "auto",
        "effective_device": "cpu",
        "effective_compute_type": "int8",
        "fallback": True,
        "fallback_reason": "cudnn_unavailable",
    }


def test_export_keeps_row_json_and_adds_summary(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.wav").write_bytes(b"audio")
    output = tmp_path / "out"
    config = PipelineConfig(str(source), str(output))
    rows = [{"relative_path": "a.wav", "status": "selected"}]
    export_selected(source, output, rows, rows, job_id="job-1", config=config)
    assert isinstance(json.loads((output / "vocalsieve-report.json").read_text()), list)
    assert json.loads((output / "vocalsieve-summary.json").read_text())["selected_count"] == 1


def test_empty_summary_has_zero_rate(tmp_path: Path):
    config = PipelineConfig(str(tmp_path), str(tmp_path / "out"))
    summary = build_report_summary("empty", config, [])
    assert summary["candidate_pass_rate"] == 0.0
    assert summary["average_duration"] is None


def test_export_reconciles_only_previously_managed_files(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.wav").write_bytes(b"a")
    (source / "b.wav").write_bytes(b"b")
    output = tmp_path / "out"
    final = output / "final_selected"
    final.mkdir(parents=True)
    stale = final / "a.wav"
    stale.write_bytes(b"old")
    unknown = final / "keep.txt"
    unknown.write_text("user")
    rows = [
        {
            "relative_path": "a.wav",
            "status": "selected",
            "review_decision": "exclude",
            "effective_selected": False,
            "exported_path": str(stale),
        },
        {
            "relative_path": "b.wav",
            "status": "transcription_passed",
            "review_decision": "include",
            "effective_selected": True,
        },
    ]
    export_selected(source, output, [rows[1]], rows)
    assert not stale.exists()
    assert (final / "b.wav").read_bytes() == b"b"
    assert unknown.read_text() == "user"
