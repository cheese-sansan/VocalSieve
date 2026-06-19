# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

datas = collect_data_files("faster_whisper")
binaries = collect_dynamic_libs("ctranslate2")
hiddenimports = ["av", "ctranslate2", "librosa", "soundfile", "textual"]
hiddenimports += collect_submodules("faster_whisper")

a = Analysis(
    ["portable_entry.py"],
    pathex=["../src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["fastapi", "httpx2", "pip_audit", "pytest", "pyright", "ruff", "uvicorn"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VocalSieve",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VocalSieve",
)
