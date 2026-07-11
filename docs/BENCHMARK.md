# Private corpus benchmark

The v1.0 release gate uses deterministic subsets of a private real-world corpus.
Relative paths are ordered by SHA256 before selecting 1,000, 10,000, and 50,000
files, so repeated runs use the same inputs without publishing corpus contents.

```powershell
uv run python scripts/benchmark_corpus.py `
  "E:\private-corpus" "E:\benchmark-results" `
  --sizes 1000 10000 50000 --device cuda --compute-type float16 `
  --verify-resume
```

The run directory contains private manifests and must not be committed or uploaded
as a public artifact. Only `benchmark-aggregate.json`, the aggregate CSV, hardware
details, configuration, and a written summary may be published. These outputs do
not contain paths, transcripts, or audio.

The release run must complete without a process-level crash, leave source hashes
unchanged, convert corrupt inputs into per-file errors, and pass the 25% cancel and
resume comparison on the smallest tier. The first v1.0 run establishes the
performance baseline; later releases may add regression thresholds against it.
