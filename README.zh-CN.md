# VocalSieve

[English](README.md)

[![CI](https://github.com/cheese-sansan/VocalSieve/actions/workflows/ci.yml/badge.svg)](https://github.com/cheese-sansan/VocalSieve/actions/workflows/ci.yml)
[![Security](https://github.com/cheese-sansan/VocalSieve/actions/workflows/security.yml/badge.svg)](https://github.com/cheese-sansan/VocalSieve/actions/workflows/security.yml)
[![Release](https://img.shields.io/github/v/release/cheese-sansan/VocalSieve?include_prereleases)](https://github.com/cheese-sansan/VocalSieve/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 把原始语音文件夹整理成可复核、可复现的语音数据集——全程本地完成。

VocalSieve 在不上传音频的前提下完成筛选、转录、排序、复核与导出。指定一个
源文件夹并保持它只读，即可得到带有可追溯决策的数据集，而不是一堆来源不明的复制文件。

## 从文件夹到数据集

1. **安全扫描。** 发现支持的音频文件，不改动源目录。
2. **先做声学检测。** 按时长、能量与频谱规则淘汰不可用文件。
3. **本地转录。** 仅对合格音频运行 `faster-whisper`，并记录后端回退情况。
4. **排序与人工复核。** 选出质量较好的候选文件，再人工处理边界样本。
5. **可复现导出。** 保留相对路径，同时写出 CSV、JSON、汇总、事件与任务状态。

每次任务的配置、进度、转录、淘汰原因、人工决定与恢复状态都存入 SQLite。
因此，最终导出结果可以检查、重复运行，也可以安全地再次复核和修订。

![VocalSieve 终端界面](docs/images/tui.svg)

React/Vite 工作区通过同一套版本化本地 API 完成任务创建、取消/恢复、结果查看、
报告、复核、事件流与重新导出。它仍是实验性开发预览，不属于 Windows portable 的支持承诺。

![VocalSieve 实验性 Web 工作区](docs/images/web-dashboard.png)

## 为什么坚持本地优先

- 源音频和转录文本始终保留在你控制的机器上。
- 原生 API 仅绑定 `127.0.0.1`，并使用会话令牌保护。
- 源目录与输出目录不得重叠；导出过程不会修改源语料。
- 模型首次使用时下载，不会提交到仓库或预置在镜像中。
- CPU、CUDA 与后端回退信息都会记录在诊断、事件和报告中。

## 项目状态

当前最新公开预发布版本为
[`v0.9.0-rc.1`](https://github.com/cheese-sansan/VocalSieve/releases/tag/v0.9.0-rc.1)。
源码正在准备 `0.9.0-rc.2`，但 rc.2 尚未发布，也没有官方可下载文件。
CI 产物和本地构建的压缩包都不属于正式 Release。

| 平台 | 支持范围 |
| --- | --- |
| Windows 10/11 | 原生 CLI 与中英双语 TUI；CPU 可用，CUDA 12 + cuDNN 9 有完整说明 |
| Linux | CPU 与 NVIDIA GPU 容器 |
| macOS | 实验性支持，不属于发布门禁 |

源码安装需要 Python 3.11 或 3.12。原生运行需要在 `PATH` 中提供 FFmpeg；
参见 [FFMPEG.md](docs/FFMPEG.md) 和 [CUDA.md](docs/CUDA.md)。

## 快速开始

### Windows portable

只使用可见 GitHub Release 中附带的资产。下载 `VocalSieve-Windows-x64.zip`，
用 `SHA256SUMS` 校验后解压到新目录，再启动 `VocalSieve.exe` 或
`Start-VocalSieve.cmd`。portable 包不需要 Python 或 uv，支持 CLI、TUI 和 `doctor`。

预发布包使用公开说明的项目自签名证书，而不是商业可信证书。SBOM、证书指纹、
校验和以及 FFmpeg GPL 源码来源会与压缩包一起发布。

### 使用 uv 开发安装

```powershell
git clone https://github.com/cheese-sansan/VocalSieve.git
cd VocalSieve
uv sync --extra tui
uv run vocalsieve doctor
uv run vocalsieve
```

### 使用 pip 开发安装

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[tui]"
.venv\Scripts\vocalsieve doctor
.venv\Scripts\vocalsieve
```

本地 HTTP API 使用 `.[api]`；完整开发环境使用 `.[tui,api,dev]`。

## 筛选、复核与导出

```powershell
vocalsieve run "E:\data\raw" "E:\data\screened" --model small --device auto --top-n 1200
vocalsieve jobs
vocalsieve resume JOB_ID
vocalsieve report JOB_ID
vocalsieve export JOB_ID
```

`top-n` 是全部规则执行后的上限，不保证一定导出相同数量。选中音频写入
`OUTPUT/final_selected/`；输出根目录还会生成逐行 CSV、JSON 和 schema v2 汇总报告。

任务完成后，可通过 TUI、SDK 或本地 API 将任意结果设置为人工选入、人工排除或恢复自动。
原始流水线状态保持不变，每次复核都有审计记录；重新导出只会协调该任务此前管理的文件。

## 使用界面

- **TUI：** 运行 `vocalsieve`；首次启动可选择 English 或简体中文。
- **CLI：** 使用 `run`、`jobs`、`resume`、`export`、`report`、`doctor` 和 `serve` 自动化处理。
- **Python SDK：** 从 `vocalsieve` 导入版本化公开接口。
- **本地 API：** 运行 `vocalsieve serve`；访问任务、路径、结果、转录和事件必须携带打印出的令牌。
- **实验性 Web：** Vite 客户端只使用由 OpenAPI 生成的类型与本地 API 通信。

```python
from vocalsieve import PipelineConfig, VocalSieveClient

config = PipelineConfig(
    source_dir=r"E:\data\raw",
    output_dir=r"E:\data\screened",
    device="auto",
    top_n=100,
)

with VocalSieveClient("vocalsieve.db") as client:
    job = client.create_job(config)
    completed = client.run_job(job.id)
    results = client.query_results(completed.id)
```

默认最多运行两个任务，其中 CUDA 任务最多一个。共享同一 SQLite 数据库的进程会协调这些限制；
路径冲突或容量耗尽时会立即拒绝提交，而不是静默排队。

### 实验性 Web 工作区

```powershell
uv sync --extra api
uv run vocalsieve serve

# 在另一个终端中使用上一步打印的令牌：
$env:VITE_VOCALSIEVE_TOKEN = "the-local-session-token"
npm --prefix web ci
npm --prefix web run dev
```

打开 `http://127.0.0.1:5173`。浏览器仅允许从文档列出的两个 localhost 来源访问，
也不会获得直接文件系统权限。

## 容器

```powershell
$env:VOCALSIEVE_SESSION_TOKEN = "replace-with-a-long-random-value"
docker compose --profile cpu up --build
```

在装有 NVIDIA Container Toolkit 的主机上使用 `--profile gpu`。服务只绑定
`127.0.0.1:8765`；`/data/input` 为只读挂载，输出、状态与模型缓存使用独立挂载。
参见 [DOCKER.md](docs/DOCKER.md)。

## 开发

```powershell
uv sync --all-extras
uv run pre-commit run --all-files
uv run pyright
uv run pytest --cov=vocalsieve
uv run python scripts/export_openapi.py --check
npm --prefix web ci
npm --prefix web run build
```

私有语料测试流程及公开边界见 [BENCHMARK.md](docs/BENCHMARK.md)。本 README 不会把
本地 benchmark 等同于发布门禁或公开 Release。

## 项目维护与开发辅助

项目方向、决策、审查与发布由 Hueter
（[@cheese-sansan](https://github.com/cheese-sansan)）负责。开发过程中使用
ChatGPT Codex 辅助，所有 AI 辅助变更均由维护者审查并确认。

依赖更新由每周安全工作流、GitHub 漏洞告警或发布准备触发，并通过维护者/Codex 分支实施。
项目已主动关闭 Dependabot 自动更新 PR。

## 文档

- [筛选与淘汰原因](docs/FILTERING.md)
- [本地 API 与安全](docs/API.md)
- [CUDA 配置](docs/CUDA.md)
- [FFmpeg 配置与来源](docs/FFMPEG.md)
- [容器运行](docs/DOCKER.md)
- [依赖策略](docs/DEPENDENCIES.md)
- [发布流程](docs/RELEASE.md)
- [安全策略](SECURITY.md)
- [参与贡献](CONTRIBUTING.md)

VocalSieve 使用 [MIT License](LICENSE) 发布。第三方组件继续遵循各自许可证，
详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
