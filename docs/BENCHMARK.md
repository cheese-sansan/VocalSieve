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

## Local rc.2 development checkpoint (2026-07-11)

This checkpoint was run from commit `43483e7` in the GPU container on an NVIDIA
GeForce RTX 4060 Laptop GPU, using the `tiny` model, CUDA, and `float16`. It is
development evidence only: the corpus was smaller than the required 50,000 files,
and the larger tier was stopped intentionally before completion.

Only aggregate counts are recorded here. Private paths, manifests, transcripts,
databases, and audio are not published.

| Run | Terminal state | Transcription decisions | Selected | Passed | Rejected | File errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1,000-file baseline | completed | 1,000 | 10 | 860 | 130 | 0 |
| 1,000-file 25% cancel/resume | completed | 1,000 | 10 | 869 | 121 | 0 |
| 3,521-file tier | stopped by operator | 2,662 | - | 2,341 | 321 | 0 |

The baseline and resumed jobs both completed without file errors, but their final
top-10 path sets differed. The automated comparison therefore evaluates
`resume_verified` as false. The stopped larger tier had 859 physics-passed files
remaining when validation was halted.

This run demonstrates that the pipeline can process more than 2,000 short
real-world audio files without a file-level error or process crash. It does not
satisfy the rc.2 release gate: cancel/resume determinism must be resolved, and the
1,000/10,000/50,000 private-corpus tiers must still complete before a release tag
is created.
