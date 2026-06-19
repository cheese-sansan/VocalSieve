# FFmpeg on Windows

VocalSieve does not bundle FFmpeg. Install it with a trusted system package
manager or a build linked from the official FFmpeg download page, then open a
new terminal and verify:

```powershell
ffmpeg -version
vocalsieve doctor
```

Typical package-manager commands are `winget install Gyan.FFmpeg`,
`choco install ffmpeg`, or `scoop install ffmpeg`, depending on which manager
is already installed. Do not copy `ffmpeg.exe` into this repository: large
third-party binaries make every clone heavier and complicate licensing and
updates.
