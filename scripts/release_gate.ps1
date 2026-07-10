[CmdletBinding()]
param(
    [switch]$SkipWeb,
    [switch]$SkipDocker,
    [switch]$BuildPortable,
    [string]$CorpusPath,
    [string]$CorpusOutput = (Join-Path $env:TEMP "vocalsieve-release-corpus-output"),
    [int[]]$BenchmarkSizes = @(1000, 10000, 50000)
)

$ErrorActionPreference = "Stop"

function Assert-NativeSuccess {
    param([Parameter(Mandatory)][string]$Label)

    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (git status --porcelain) { throw "Git working tree is not clean" }
    if (git log --all --format= --name-only -- ffmpeg.exe) {
        throw "ffmpeg.exe is still present in Git history"
    }
    $placeholders = git grep -n -I -E "OWNER|<repository-url>|TODO|FIXME" -- . ":(exclude)uv.lock" ":(exclude)scripts/release_gate.ps1"
    if ($LASTEXITCODE -eq 0 -and $placeholders) { throw "Release placeholders found:`n$placeholders" }

    .\.venv\Scripts\uv.exe sync --all-extras --locked
    Assert-NativeSuccess "uv sync"
    .\.venv\Scripts\pre-commit.exe run --all-files
    Assert-NativeSuccess "pre-commit"
    .\.venv\Scripts\python.exe scripts/check_versions.py
    Assert-NativeSuccess "version check"
    .\.venv\Scripts\python.exe scripts/export_openapi.py --check
    Assert-NativeSuccess "OpenAPI drift check"
    .\.venv\Scripts\ruff.exe check src tests
    Assert-NativeSuccess "Ruff"
    .\.venv\Scripts\pyright.exe
    Assert-NativeSuccess "Pyright"
    New-Item -ItemType Directory -Force -Path .tmp | Out-Null
    .\.venv\Scripts\python.exe -m pytest --cov=vocalsieve --cov-report=xml --basetemp .tmp/pytest-release
    Assert-NativeSuccess "pytest"
    .\.venv\Scripts\pip-audit.exe --skip-editable
    Assert-NativeSuccess "pip-audit"
    .\.venv\Scripts\pip-licenses.exe --format=markdown --with-urls --ignore-packages vocalsieve --output-file=docs/PYTHON_LICENSES.md
    Assert-NativeSuccess "Python license inventory"
    .\.venv\Scripts\python.exe -m build
    Assert-NativeSuccess "Python package build"

    if (-not $SkipWeb) {
        npm --prefix web ci
        Assert-NativeSuccess "npm ci"
        npm --prefix web audit --audit-level=high
        Assert-NativeSuccess "npm audit"
        npm --prefix web run licenses
        Assert-NativeSuccess "Node license inventory"
        npm --prefix web run build
        Assert-NativeSuccess "Web build"
    }

    git diff --exit-code -- docs/PYTHON_LICENSES.md docs/NODE_LICENSES.md
    Assert-NativeSuccess "license inventory drift check"

    .\.venv\Scripts\vocalsieve.exe doctor --deep --device cuda --model tiny
    Assert-NativeSuccess "native CUDA doctor"

    if ($BuildPortable) {
        .\scripts\build_windows_portable.ps1
        Assert-NativeSuccess "portable package build"
        .\dist\windows\VocalSieve\VocalSieve.exe doctor --deep --device cuda --model tiny
        Assert-NativeSuccess "portable CUDA doctor"
    }

    if ($CorpusPath) {
        $benchmarkArgs = @(
            "scripts/benchmark_corpus.py",
            $CorpusPath,
            $CorpusOutput,
            "--sizes"
        ) + $BenchmarkSizes + @(
            "--model", "tiny",
            "--device", "cuda",
            "--compute-type", "float16",
            "--language", "auto",
            "--top-n", "10",
            "--verify-resume"
        )
        .\.venv\Scripts\python.exe @benchmarkArgs
        Assert-NativeSuccess "private corpus benchmark"
    }

    if (-not $SkipDocker) {
        docker build --target cpu -t vocalsieve:release-gate .
        Assert-NativeSuccess "CPU Docker build"
        docker run --rm vocalsieve:release-gate doctor
        Assert-NativeSuccess "CPU Docker doctor"
        docker build --target gpu -t vocalsieve:gpu-release-gate .
        Assert-NativeSuccess "GPU Docker build"
        docker run --rm --gpus all vocalsieve:gpu-release-gate doctor --deep --device cuda --model tiny
        Assert-NativeSuccess "GPU Docker CUDA doctor"
    }
}
finally {
    Pop-Location
}
