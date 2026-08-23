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
class RejectionInfo:
    title: str
    description: str
    config_field: str | None
    guidance: str


REJECTION_CATALOG: dict[str, RejectionInfo] = {
    "duration_too_short": RejectionInfo(
        "Duration too short",
        "Audio is shorter than the minimum duration.",
        "min_duration",
        "Lower min_duration only when very short utterances are useful.",
    ),
    "energy_too_low": RejectionInfo(
        "Energy too low",
        "Average RMS energy is below the configured floor.",
        "min_rms",
        "Lower min_rms for quiet recordings after checking their signal quality.",
    ),
    "spectral_centroid_too_low": RejectionInfo(
        "Spectral centroid too low",
        "The signal has too little high-frequency content.",
        "min_centroid",
        "Lower min_centroid for naturally dark voices or narrow-band audio.",
    ),
    "no_speech": RejectionInfo(
        "No speech detected",
        "The transcription backend assigned a high no-speech probability.",
        "no_speech_threshold",
        "Raise no_speech_threshold only after listening to false rejects.",
    ),
    "text_too_short": RejectionInfo(
        "Transcript too short",
        "The transcript has fewer characters than allowed.",
        "min_text_length",
        "Lower min_text_length to retain one-character utterances.",
    ),
    "text_too_long": RejectionInfo(
        "Transcript too long",
        "The transcript has more characters than allowed.",
        "max_text_length",
        "Raise max_text_length when longer utterances are acceptable.",
    ),
    "repeated_characters": RejectionInfo(
        "Repeated characters",
        "The transcript contains a suspicious repeated-character run.",
        "repeat_char_threshold",
        "Raise repeat_char_threshold if legitimate repetitions are common.",
    ),
    "hallucination_keyword": RejectionInfo(
        "Possible hallucination",
        "The transcript contains a known hallucination phrase.",
        None,
        "Review the transcript and audio; this rule has no CLI threshold.",
    ),
    "physics_error": RejectionInfo(
        "Audio analysis error",
        "The file could not be decoded or analyzed.",
        None,
        "Check the codec, file integrity, and FFmpeg installation.",
    ),
    "transcription_error": RejectionInfo(
        "Transcription error",
        "The transcription backend failed for this file.",
        None,
        "Run vocalsieve doctor and inspect the job warning/error events.",
    ),
}


def rejection_info(code: str) -> RejectionInfo:
    return REJECTION_CATALOG.get(
        code,
        RejectionInfo(
            "Unknown rejection",
            "No catalog entry exists for this code.",
            None,
            "Update VocalSieve or inspect reject_detail.",
        ),
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
