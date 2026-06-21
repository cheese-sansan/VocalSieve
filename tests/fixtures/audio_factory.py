from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 16_000


def _write_wav(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(
        struct.pack("<h", max(-32768, min(32767, round(sample * 32767))))
        for sample in samples
    )
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(frames)


def tone(path: Path, *, duration: float, frequency: float, amplitude: float) -> None:
    count = round(duration * SAMPLE_RATE)
    _write_wav(
        path,
        [amplitude * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
         for index in range(count)],
    )


def generated_corpus(root: Path) -> dict[str, Path]:
    files = {
        "silence": root / "silence.wav",
        "short": root / "short.wav",
        "quiet": root / "quiet.wav",
        "normal": root / "speaker" / "normal.wav",
        "noise": root / "noise.wav",
        "broken": root / "broken.wav",
    }
    _write_wav(files["silence"], [0.0] * SAMPLE_RATE)
    tone(files["short"], duration=0.1, frequency=3_000, amplitude=0.3)
    tone(files["quiet"], duration=1.0, frequency=3_000, amplitude=0.001)
    tone(files["normal"], duration=1.0, frequency=3_000, amplitude=0.3)
    rng = random.Random(20260622)
    _write_wav(files["noise"], [rng.uniform(-0.3, 0.3) for _ in range(SAMPLE_RATE)])
    files["broken"].write_bytes(b"not a wave file")
    return files
