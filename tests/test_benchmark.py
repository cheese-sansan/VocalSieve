import json
import subprocess
import sys
from pathlib import Path

from tests.fixtures.audio_factory import tone


def test_private_benchmark_runs_deterministically_and_verifies_resume(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    tone(source / "a.wav", duration=0.5, frequency=1000, amplitude=0.0)
    tone(source / "b.wav", duration=0.5, frequency=1000, amplitude=0.0)
    output = tmp_path / "benchmark-results"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_corpus.py",
            str(source),
            str(output),
            "--sizes",
            "2",
            "--skip-source-hashes",
            "--verify-resume",
            "--top-n",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    run_root = Path(completed.stdout.strip())
    aggregate = json.loads((run_root / "benchmark-aggregate.json").read_text(encoding="utf-8"))
    assert aggregate["private_corpus"] is True
    assert aggregate["results"][0]["file_count"] == 2
    assert aggregate["results"][0]["resume_verified"] is True
    assert not (run_root / "staging" / "2").exists()
