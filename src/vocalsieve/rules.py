"""Pure screening and ranking rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .domain import AudioMetrics, PipelineConfig, Transcript

HALLUCINATION_KEYWORDS = (
    "subtitle",
    "subscribe",
    "字幕",
    "視聴",
    "ご視聴",
    "チャンネル登録",
    "..",
)


@dataclass(frozen=True, slots=True)
class RuleDecision:
    accepted: bool
    code: str | None = None
    detail: str | None = None


def evaluate_physics(metrics: AudioMetrics, config: PipelineConfig) -> RuleDecision:
    if metrics.duration < config.min_duration:
        return RuleDecision(False, "duration_too_short", f"{metrics.duration:.2f}s")
    if metrics.rms < config.min_rms:
        return RuleDecision(False, "energy_too_low", f"RMS {metrics.rms:.4f}")
    if metrics.spectral_centroid < config.min_centroid:
        return RuleDecision(
            False,
            "spectral_centroid_too_low",
            f"{metrics.spectral_centroid:.0f} Hz",
        )
    return RuleDecision(True)


def evaluate_transcript(transcript: Transcript, config: PipelineConfig) -> RuleDecision:
    if transcript.no_speech_prob > config.no_speech_threshold:
        return RuleDecision(False, "no_speech", f"Probability {transcript.no_speech_prob:.2f}")
    length = len(transcript.text)
    if length < config.min_text_length:
        return RuleDecision(False, "text_too_short", f"{length} characters")
    if length > config.max_text_length:
        return RuleDecision(False, "text_too_long", f"{length} characters")
    pattern = rf"(.)\1{{{config.repeat_char_threshold - 1},}}"
    if re.search(pattern, transcript.text, flags=re.IGNORECASE):
        return RuleDecision(False, "repeated_characters", "Repeated character run")
    folded = transcript.text.casefold()
    for keyword in HALLUCINATION_KEYWORDS:
        if keyword.casefold() in folded:
            return RuleDecision(False, "hallucination_keyword", keyword)
    return RuleDecision(True)


def rank_score(text: str, ideal_length: int) -> float:
    return float(abs(len(text) - ideal_length))
