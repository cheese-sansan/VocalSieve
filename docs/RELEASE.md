# Prerelease checklist

VocalSieve has no official release until every item below succeeds for the
same commit. The recommended tag format is `v0.9.0-rc.2`.

1. Confirm `main` is clean and choose the release commit.
2. Replace `Unreleased` in `CHANGELOG.md` with the release date and verify the
   release notes describe supported platforms, CUDA/cuDNN and FFmpeg
   requirements, first-run model downloads, local-only operation, and known
   limitations.
3. Run `python scripts/check_versions.py` and the complete release gate:

   ```powershell
   .\scripts\release_gate.ps1 -BuildPortable -CorpusPath "E:\data\release-corpus"
   ```

   `CorpusPath` must contain at least 50,000 supported audio files. The gate runs
   deterministic 1k/10k/50k private-corpus tiers and the cancel/resume comparison;
   only aggregate benchmark outputs may be published.

4. Create and push the annotated tag on that exact commit.
5. Run the `GPU release gate` and `Signed Windows package` workflows for the
   tagged commit. Both must succeed; unsigned output is not a release asset.
6. Trigger `Release artifacts` with the tag and the successful GPU and Windows
   run IDs. The workflow verifies that all three SHAs match.
7. Verify the prerelease contains the Python wheel and sdist, OpenAPI contract,
   signed `VocalSieve-Windows-x64.zip`, SBOMs, checksums, FFmpeg source
   materials, the public signing certificate and fingerprint, and CPU/GPU GHCR
   images. State clearly that the prerelease certificate is self-signed and is
   not trusted by Windows by default.
8. Install the published assets on a clean Windows machine and run
   `VocalSieve.exe doctor` before announcing the prerelease.

Tags containing a hyphen, such as `v0.9.0-rc.2`, are published as prereleases.
Stable tags such as `v1.0.0` are published as full releases by the same workflow.

Keep the README installation status marked unreleased until the GitHub Release
is visible and its assets have passed the final smoke test.
