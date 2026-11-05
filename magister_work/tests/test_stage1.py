"""Тесты Этапа 1: контракты, framing, огибающая, VAD, метрики, R/S.

Все тесты детерминированы и не требуют внешних зависимостей, кроме pytest.
"""

from __future__ import annotations

import math

import pytest

from speechdyn import (
    EnergyVad,
    EntropyVad,
    SegmentRecord,
    complement_segments,
    frame_metrics,
    modified_rs_hurst,
    modified_rs_hurst_full_record,
    parabolic_envelope,
    rasterize,
    states_to_spans,
    validate_non_overlapping,
)
from speechdyn.framing import TimeGrid, compute_rms_frames
from speechdyn.synthetic import speech_pause_sequence, synthetic_utterance
from speechdyn.vad.entropy import phase_space_entropy, window_entropy_features


# --- контракты -----------------------------------------------------------

def test_segment_record_rejects_bad_span():
    with pytest.raises(ValueError):
        SegmentRecord(file_id="f", start_sec=0.5, end_sec=0.5, label="speech", source_backend="x")


def test_segment_record_rejects_unknown_label():
    with pytest.raises(ValueError):
        SegmentRecord(file_id="f", start_sec=0.0, end_sec=0.5, label="foo", source_backend="x")


def test_validate_non_overlapping_allows_adjacent():
    first = SegmentRecord(file_id="f", start_sec=0.0, end_sec=0.5, label="speech", source_backend="x")
    second = SegmentRecord(file_id="f", start_sec=0.5, end_sec=1.0, label="speech", source_backend="x")
    validate_non_overlapping([first, second])


def test_validate_non_overlapping_rejects_overlap():
    first = SegmentRecord(file_id="f", start_sec=0.0, end_sec=0.6, label="speech", source_backend="x")
    second = SegmentRecord(file_id="f", start_sec=0.5, end_sec=1.0, label="speech", source_backend="x")
    with pytest.raises(ValueError):
        validate_non_overlapping([first, second])


def test_complement_segments_fills_gaps():
    speech = [
        SegmentRecord(file_id="f", start_sec=0.2, end_sec=0.5, label="speech", source_backend="x"),
        SegmentRecord(file_id="f", start_sec=0.8, end_sec=1.0, label="speech", source_backend="x"),
    ]
    full = complement_segments(speech, 1.5, file_id="f")
    assert [(s.start_sec, s.end_sec, s.label) for s in full] == [
        (0.0, 0.2, "non_speech"),
        (0.2, 0.5, "speech"),
        (0.5, 0.8, "non_speech"),
        (0.8, 1.0, "speech"),
        (1.0, 1.5, "non_speech"),
    ]
    validate_non_overlapping(full)


# --- framing -------------------------------------------------------------

def test_time_grid_roundtrip():
    grid = TimeGrid.from_ms(16000, 20, 10)
    assert grid.frame_samples == 320
    assert grid.hop_samples == 160
    assert math.isclose(grid.frame_sec, 0.02)
    assert math.isclose(grid.hop_sec, 0.01)


def test_compute_rms_frames_matches_manual():
    grid = TimeGrid.from_ms(1000, 10, 10)
    audio = [1.0] * 10 + [0.0] * 10
    times, rms = compute_rms_frames(audio, grid)
    assert len(rms) == 2
    assert math.isclose(rms[0], 1.0)
    assert math.isclose(rms[1], 0.0)


def test_parabolic_envelope_tracks_peak():
    sample_rate = 1000
    audio = [0.0] * 5 + [1.0] * 5 + [0.0] * 5
    times, values = parabolic_envelope(audio, sample_rate, window_ms=5, hop_ms=5)
    assert values
    assert max(values) == pytest.approx(1.0)
    assert len(times) == len(values)


# --- states -> segments --------------------------------------------------

def test_states_to_spans_drops_short_speech():
    spans = states_to_spans([True, False, False], step_sec=0.02, duration_sec=0.06,
                            min_speech_sec=0.1, min_pause_sec=0.0)
    assert spans == []


def test_states_to_spans_merges_short_pause():
    states = [True, True, False, True, True]
    spans = states_to_spans(states, step_sec=0.02, duration_sec=0.1,
                            min_speech_sec=0.0, min_pause_sec=0.1)
    assert spans == [(0.0, pytest.approx(0.1))]


# --- energy VAD ----------------------------------------------------------

def test_energy_vad_finds_speech():
    audio, truth = synthetic_utterance(durations_sec=speech_pause_sequence())
    segments = EnergyVad().process_array(audio, 16000)
    assert segments, "energy VAD should find some speech"
    validate_non_overlapping(segments)
    # Первый и последний сегменты не должны пересекать границы файла.
    duration = len(audio) / 16000
    assert all(0 <= s.start_sec < s.end_sec <= duration for s in segments)


def test_energy_vad_silence_is_empty():
    audio = [0.0] * 16000
    segments = EnergyVad().process_array(audio, 16000)
    assert segments == []


# --- entropy VAD ---------------------------------------------------------

def test_phase_space_entropy_constant_signal():
    assert phase_space_entropy([0.5] * 20, 8, 2) == 0.0


def test_phase_space_entropy_in_range():
    values = [math.sin(i / 3) for i in range(60)]
    value = phase_space_entropy(values, 8, 2)
    assert 0.0 <= value <= math.log2(8 * 8)


def test_window_entropy_features_shape():
    audio, _ = synthetic_utterance(durations_sec=[("speech", 0.5), ("pause", 0.5)])
    features = window_entropy_features([v * 0.9 for v in audio], 16000, EntropyVad().config)
    assert features
    assert all(len(row) == 4 for row in features)


def test_entropy_vad_produces_valid_segments():
    audio, _ = synthetic_utterance(durations_sec=speech_pause_sequence())
    segments = EntropyVad().process_array(audio, 16000)
    validate_non_overlapping(segments)
    duration = len(audio) / 16000
    assert all(0 <= s.start_sec < s.end_sec <= duration for s in segments)


# --- metrics -------------------------------------------------------------

def test_frame_metrics_perfect_match():
    mask = [True, True, False, False]
    metrics = frame_metrics(mask, mask, hop_sec=0.01)
    assert metrics.f1 == 1.0
    assert metrics.iou == 1.0
    assert metrics.false_pause_precision == 1.0


def test_frame_metrics_false_pause_precision():
    # Предсказание: пауза, пауза, речь, речь.
    # Эталон:       пауза, речь,  речь, пауза.
    # Одна верная пауза (idx0) и одна ложная (idx1) -> FPP = 0.5.
    predicted = [False, False, True, True]
    reference = [False, True, True, False]
    metrics = frame_metrics(predicted, reference, hop_sec=0.01)
    assert metrics.false_pause_precision == pytest.approx(0.5)
    assert metrics.recall == pytest.approx(0.5)


def test_rasterize_marks_speech():
    segments = [SegmentRecord(file_id="f", start_sec=0.02, end_sec=0.04,
                              label="speech", source_backend="x")]
    mask = rasterize(segments, duration_sec=0.1, hop_sec=0.01)
    assert mask == [False, False, True, True, False, False, False, False, False, False]


# --- R/S dynamics --------------------------------------------------------

def test_modified_rs_full_record_flags_comparable():
    audio, _ = synthetic_utterance(durations_sec=[("speech", 2.0), ("pause", 1.0)] * 3)
    result = modified_rs_hurst_full_record(audio, 16000)
    assert result.scope == "full_record"
    assert result.comparable_to_reference is True


def test_modified_rs_segment_flags_not_comparable():
    audio, _ = synthetic_utterance(durations_sec=[("speech", 1.0)])
    result = modified_rs_hurst(audio, 16000)
    assert result.scope == "segment"
    assert result.comparable_to_reference is False


def test_modified_rs_short_input_invalid():
    result = modified_rs_hurst([0.1, 0.2, 0.3], 16000)
    assert result.valid is False
    assert "input_too_short" in result.warnings
