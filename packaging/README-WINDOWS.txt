VocalSieve for Windows
======================

Double-click VocalSieve.exe or Start-VocalSieve.cmd to open the terminal UI.
No Python or uv installation is required.
The portable package provides the CLI, TUI, and doctor command. Install the
Python wheel or use a container for the local HTTP API.

Command Prompt examples:
  VocalSieve.exe doctor
  VocalSieve.exe doctor --deep --device cuda --model tiny
  VocalSieve.exe run "C:\audio\input" "C:\audio\output" --top-n 100

Model weights are not included. The selected faster-whisper model is downloaded
on first use and cached in your user profile. CPU mode works without CUDA.
Run VocalSieve.exe doctor --json to see actionable checks and the application
data, model cache, database, and log locations.

Default user locations:
  Database and settings: %LOCALAPPDATA%\VocalSieve
  Rotating logs:         %LOCALAPPDATA%\VocalSieve\Logs
  Model cache:           %USERPROFILE%\.cache\huggingface\hub

Upgrade by extracting a new release to a new directory while VocalSieve is not
running. The first launch migrates the SQLite database transactionally and keeps
a vocalsieve.db.pre-v3.bak backup when upgrading from an earlier schema.

To uninstall the executable, delete its extracted directory. User data and model
weights are deliberately retained. After backing up any jobs you need, those
default user locations may be removed manually for a complete cleanup.

This archive contains a separate GPLv3 FFmpeg executable. Its license and
source/build provenance are in the licenses\FFmpeg directory. VocalSieve itself
is licensed under MIT.

VocalSieve.exe is Authenticode-signed with the self-signed VocalSieve
prerelease certificate. Windows will not trust this certificate by default.
The public certificate is in licenses\VocalSieve; compare its fingerprint with
the release notes and checksum files before choosing whether to trust it.
