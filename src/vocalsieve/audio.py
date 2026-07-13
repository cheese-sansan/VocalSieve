"""Acoustic analysis port and librosa implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .domain import AudioMetrics


class AudioAnalyzer(Protocol):
    def analyze(self, path: Path) -> AudioMetrics: ...


class LibrosaAudioAnalyzer:
    def analyze(self, path: Path) -> AudioMetrics:
        import librosa
        import numpy as np

        samples, sample_rate = librosa.load(path, sr=None, mono=True)
        duration = float(librosa.get_duration(y=samples, sr=sample_rate))
        rms = float(np.mean(librosa.feature.rms(y=samples)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=samples, sr=sample_rate)))
        return AudioMetrics(duration=duration, rms=rms, spectral_centroid=centroid)
