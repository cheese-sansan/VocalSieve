import wave
from pathlib import Path

from vocalsieve.audio import LibrosaAudioAnalyzer


def test_librosa_analyzer_reads_real_wav(tmp_path: Path):
    path = tmp_path / "tone.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x10\x00" * 8_000)
    metrics = LibrosaAudioAnalyzer().analyze(path)
    assert metrics.duration == 0.5
    assert metrics.rms > 0
