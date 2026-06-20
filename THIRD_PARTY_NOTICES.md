# Third-party notices

VocalSieve depends on third-party Python packages distributed under their own
licenses. The authoritative dependency set is recorded in `uv.lock` and
`pyproject.toml`.

Generated inventories are published in `docs/PYTHON_LICENSES.md` and
`docs/NODE_LICENSES.md`. PyInstaller is used only to construct the Windows
executable; its bootloader exception permits distribution of the resulting
application under VocalSieve's MIT terms.

Model weights are downloaded from their respective publishers at runtime and
are not part of this repository or its container images. Users are responsible
for reviewing the model license that applies to their selected model.

FFmpeg is discovered from the host system or installed by the container image;
no FFmpeg binary is stored in this repository. The Windows portable Release
redistributes one separately invoked GPLv3 FFmpeg executable. That Release also
provides its GPLv3 license, pinned source/build provenance, and corresponding
source materials. VocalSieve's Python source remains MIT licensed.

The pinned FFmpeg build enables GPL components. It must not be replaced without
updating `packaging/ffmpeg-manifest.json`, reviewing the build configuration,
and publishing the matching source materials.
