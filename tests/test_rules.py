from vocalsieve.domain import AudioMetrics, PipelineConfig, Transcript
from vocalsieve.rules import evaluate_physics, evaluate_transcript, rank_score

CONFIG = PipelineConfig("source", "output")


def test_physics_rules_report_stable_codes():
    decision = evaluate_physics(AudioMetrics(0.1, 1.0, 2000), CONFIG)
    assert not decision.accepted
    assert decision.code == "duration_too_short"
    assert evaluate_physics(AudioMetrics(1.0, 0.2, 2000), CONFIG).accepted
    assert evaluate_physics(AudioMetrics(1.0, 0.001, 2000), CONFIG).code == "energy_too_low"
    assert evaluate_physics(AudioMetrics(1.0, 0.2, 100), CONFIG).code == "spectral_centroid_too_low"


def test_transcript_rules_reject_hallucination_and_repetition():
    hallucination = evaluate_transcript(Transcript("Please subscribe", "en", 0.1), CONFIG)
    repeated = evaluate_transcript(Transcript("aaaa hello", "en", 0.1), CONFIG)
    assert hallucination.code == "hallucination_keyword"
    assert repeated.code == "repeated_characters"
    assert evaluate_transcript(Transcript("", "en", 0.9), CONFIG).code == "no_speech"
    assert evaluate_transcript(Transcript("x", "en", 0.1), CONFIG).code == "text_too_short"
    assert evaluate_transcript(Transcript("x" * 50, "en", 0.1), CONFIG).code == "text_too_long"


def test_rank_score_prefers_ideal_length():
    assert rank_score("1234567890", 10) < rank_score("short", 10)
