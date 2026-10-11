"""Tests for unified framing utilities."""

import math

from voice_signals.framing import FrameScore, TimeGrid, compute_rms_frames


def test_time_grid_from_ms() -> None:
    """Test TimeGrid creation from milliseconds."""
    grid = TimeGrid.from_ms(sample_rate=16000, frame_ms=25.0, hop_ms=10.0)
    assert grid.sample_rate == 16000
    assert grid.frame_samples == 400  # 16000 * 0.025
    assert grid.hop_samples == 160  # 16000 * 0.010
    assert abs(grid.frame_sec - 0.025) < 1e-6
    assert abs(grid.hop_sec - 0.010) < 1e-6


def test_time_grid_frame_times() -> None:
    """Test frame time calculation."""
    grid = TimeGrid.from_ms(sample_rate=8000, frame_ms=20.0, hop_ms=10.0)
    times = grid.frame_times(5)
    assert len(times) == 5
    assert times[0] == 0.0
    assert abs(times[1] - 0.01) < 1e-6
    assert abs(times[4] - 0.04) < 1e-6


def test_compute_rms_frames_basic() -> None:
    """Test basic RMS frame computation."""
    # Create a simple signal: 1 second of tone at 8000 Hz
    sample_rate = 8000
    audio = [0.5 * math.sin(2 * math.pi * 440 * i / sample_rate) for i in range(sample_rate)]
    
    grid = TimeGrid.from_ms(sample_rate=sample_rate, frame_ms=25.0, hop_ms=10.0)
    times, rms_values = compute_rms_frames(audio, grid)
    
    # Should produce frames
    assert len(times) > 0
    assert len(rms_values) == len(times)
    
    # RMS of sine wave should be approximately amplitude / sqrt(2)
    expected_rms = 0.5 / math.sqrt(2)
    for rms in rms_values:
        assert abs(rms - expected_rms) < 0.05  # Allow some tolerance


def test_compute_rms_frames_determinism() -> None:
    """Test that compute_rms_frames is deterministic."""
    audio = [0.1 * i for i in range(1000)]
    grid = TimeGrid.from_ms(sample_rate=8000, frame_ms=20.0, hop_ms=10.0)
    
    times1, rms1 = compute_rms_frames(audio, grid)
    times2, rms2 = compute_rms_frames(audio, grid)
    
    assert times1 == times2
    assert rms1 == rms2


def test_compute_rms_frames_empty() -> None:
    """Test compute_rms_frames with insufficient samples."""
    grid = TimeGrid.from_ms(sample_rate=8000, frame_ms=25.0, hop_ms=10.0)
    audio = [0.1] * 10  # Too short for even one frame
    
    times, rms_values = compute_rms_frames(audio, grid)
    assert len(times) == 0
    assert len(rms_values) == 0


def test_frame_score_creation() -> None:
    """Test FrameScore dataclass."""
    score = FrameScore(time_sec=0.5, energy_db=12.3, is_speech=True, baseline_db=5.0)
    assert score.time_sec == 0.5
    assert score.energy_db == 12.3
    assert score.is_speech is True
    assert score.baseline_db == 5.0
    
    # Test without baseline
    score2 = FrameScore(time_sec=1.0, energy_db=8.0, is_speech=False)
    assert score2.baseline_db is None
