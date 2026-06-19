# CUDA support

VocalSieve uses CTranslate2 through `faster-whisper`. A visible NVIDIA GPU or a
working `nvidia-smi` command is not sufficient: the process must also load the
CUDA 12 cuBLAS and cuDNN 9 runtime libraries and complete a real transcription.

## Release matrix

| Environment | Driver | Runtime | CTranslate2 | Result |
| --- | --- | --- | --- | --- |
| Docker Desktop Linux, RTX 4060 | 610.47 | CUDA 12.8.1 + cuDNN runtime | 4.8.0 | Passed `tiny` deep inference |
| Windows native, RTX 4060 | 610.47 | CUDA 12.8 cuBLAS + cuDNN 9, alongside CUDA 13 | 4.8.0 | Passed `tiny` deep inference |

The Windows release gate requires a side-by-side CUDA 12 runtime. CUDA 13
contains `cublas64_13.dll`; renaming it is unsafe and unsupported. Install the
official CUDA 12 toolkit/runtime and cuDNN 9 for CUDA 12. VocalSieve discovers
standard side-by-side CUDA 12 and cuDNN locations automatically.

## Verification

Open a new PowerShell window after installation:

```powershell
where.exe cublas64_12.dll
where.exe cudnn64_9.dll
vocalsieve doctor --deep --device cuda --model tiny
```

The final line must report `Inference probe ... on cuda`. An explicit
`--device cuda` fails before a job starts when the probe fails. `--device auto`
falls back to CPU and emits the reason once.

## Common failures

- `cublas64_12.dll not loadable`: install CUDA 12 runtime components and fix
  `PATH`; a CUDA 13-only installation is not compatible.
- `cudnn64_9.dll not loadable`: install cuDNN 9 built for CUDA 12 and add its
  `bin` directory to `PATH`.
- Model download failure: verify HTTPS access to Hugging Face, or set `HF_HOME`
  to a persistent cache and optionally provide `HF_TOKEN`.
- GPU container unavailable: verify `docker run --rm --gpus all nvidia/cuda`
  can execute `nvidia-smi` before testing VocalSieve.

The GPU image is pinned to `nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04`.
