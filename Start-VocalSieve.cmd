@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0VocalSieve.exe" (
  "%~dp0VocalSieve.exe" %*
  goto :done
)

if exist "%~dp0.venv\Scripts\vocalsieve.exe" (
  "%~dp0.venv\Scripts\vocalsieve.exe" %*
  goto :done
)

where uv >nul 2>nul
if %errorlevel% equ 0 (
  uv run --extra tui vocalsieve %*
  goto :done
)

echo VocalSieve could not find VocalSieve.exe, .venv, or uv.
echo See README.md for installation instructions.
set "VOCALSIEVE_EXIT=1"

:done
if not defined VOCALSIEVE_EXIT set "VOCALSIEVE_EXIT=%errorlevel%"
if not "%VOCALSIEVE_EXIT%"=="0" pause
exit /b %VOCALSIEVE_EXIT%
