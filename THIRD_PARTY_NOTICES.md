# Third-party notices

VocalSieve depends on third-party Python packages distributed under their own
licenses. The authoritative dependency set is recorded in `uv.lock` and
`pyproject.toml`.

Model weights are downloaded from their respective publishers at runtime and
are not part of this repository or its container images. Users are responsible
for reviewing the model license that applies to their selected model.

FFmpeg is discovered from the host system or installed by the container image;
no FFmpeg binary is redistributed in this repository.

