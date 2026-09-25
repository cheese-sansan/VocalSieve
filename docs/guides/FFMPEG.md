# FFmpeg on Windows

Source and pip installations do not bundle FFmpeg. Install it with a trusted
system package manager or a build linked from the official FFmpeg download
page, then open a new terminal and verify:

```powershell
ffmpeg -version
vocalsieve doctor
```

Doctor executes `ffmpeg -version` with a short timeout instead of checking only
that a filename exists. Use `vocalsieve doctor --output PATH` to verify the
nearest existing parent of an intended output directory is writable.

Typical package-manager commands are `winget install Gyan.FFmpeg`,
`choco install ffmpeg`, or `scoop install ffmpeg`, depending on which manager
is already installed. Do not copy `ffmpeg.exe` into this repository: large
third-party binaries make every clone heavier and complicate licensing and
updates.

The signed Windows portable release is different: its packaging workflow adds
one pinned `ffmpeg.exe` beside the application after verifying SHA256. The
binary remains a separate GPLv3 program. Its license, build provenance, exact
FFmpeg commit, and corresponding source/build archives ship with the GitHub
Release. FFmpeg is never added to Git history.

Pinned Windows artifact:

- FFmpeg commit: `482395f830a18686d23c12f783b7ea927c2f2bdb`
- Build project commit: `ddd38fbb847aa759126f20e9a2179b3ea8699a63`
- Executable SHA256: `1BA2B052F0663119B55C071270374539F52FD1443D1D27DCE5738DE116F173D3`
