VocalSieve for Windows
======================

Double-click VocalSieve.exe or Start-VocalSieve.cmd to open the terminal UI.
No Python or uv installation is required.

Command Prompt examples:
  VocalSieve.exe doctor
  VocalSieve.exe doctor --deep --device cuda --model tiny
  VocalSieve.exe run "C:\audio\input" "C:\audio\output" --top-n 100

Model weights are not included. The selected faster-whisper model is downloaded
on first use and cached in your user profile. CPU mode works without CUDA.

This archive contains a separate GPLv3 FFmpeg executable. Its license and
source/build provenance are in the licenses\FFmpeg directory. VocalSieve itself
is licensed under MIT.
