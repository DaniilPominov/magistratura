"""A compact, deterministic energy VAD with hysteresis."""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .framing import FrameScore, TimeGrid, compute_rms_frames
from .schemas import SegmentRecord, validate_non_overlapping


@dataclass(frozen=True)
class EnergyVadConfig:
    frame_ms: float = 20.0
    hop_ms: float = 10.0
    speech_threshold_db: float = 10.0
    release_threshold_db: float = 6.0
    noise_percentile: float = 0.2
    min_speech_ms: float = 80.0
    min_pause_ms: float = 80.0


class EnergyVad:
    name = "energy"
    version = "0.1.0"

    def __init__(self, config: EnergyVadConfig | None = None) -> None:
        self.config = config or EnergyVadConfig()
        if self.config.release_threshold_db > self.config.speech_threshold_db:
            raise ValueError("release threshold cannot exceed speech threshold")

    def process_array(
        self,
        audio: Iterable[float],
        sample_rate: int,
        *,
        file_id: str = "array",
        subject_id: str | None = None,
        task_type: str = "vad",
        return_frame_scores: bool = False,
    ) -> list[SegmentRecord] | tuple[list[SegmentRecord], list[FrameScore]]:
        samples = list(audio)
        if sample_rate <= 0 or not samples:
            if return_frame_scores:
                return [], []
            return []
        
        # Use unified framing
        grid = TimeGrid.from_ms(sample_rate, self.config.frame_ms, self.config.hop_ms)
        times, energies = compute_rms_frames(samples, grid)
        
        # Convert RMS to energy (square) and then to dB
        db = [10 * math.log10(energy * energy + 1e-12) for energy in energies]
        baseline = _percentile(db, self.config.noise_percentile)
        
        # Hysteresis logic
        states: list[bool] = []
        active = False
        for value in db:
            limit = self.config.release_threshold_db if active else self.config.speech_threshold_db
            active = value - baseline >= limit
            states.append(active)
        
        # Convert states to segments
        segments = _states_to_segments(
            states, grid.hop_sec, len(samples) / sample_rate,
            self.config.min_speech_ms / 1000, self.config.min_pause_ms / 1000,
        )
        result = [
            SegmentRecord(file_id, subject_id, task_type, start, end, "speech", None, self.name,
                          notes=f"version={self.version}")
            for start, end in segments
        ]
        validate_non_overlapping(result)
        
        if return_frame_scores:
            scores = [
                FrameScore(time, db_val, state, baseline)
                for time, db_val, state in zip(times, db, states)
            ]
            return result, scores
        return result

    def process_file(
        self,
        path: str | Path,
        *,
        subject_id: str | None = None,
        task_type: str = "vad",
    ) -> list[SegmentRecord]:
        with wave.open(str(path), "rb") as source:
            if source.getnchannels() != 1 or source.getsampwidth() != 2:
                raise ValueError("only mono 16-bit PCM WAV is supported")
            sample_rate = source.getframerate()
            raw = source.readframes(source.getnframes())
        audio = [
            int.from_bytes(raw[index:index + 2], "little", signed=True) / 32768.0
            for index in range(0, len(raw), 2)
        ]
        return self.process_array(
            audio,
            sample_rate,
            file_id=Path(path).stem,
            subject_id=subject_id,
            task_type=task_type,
        )


def _percentile(values: list[float], fraction: float) -> float:
    if not 0 <= fraction <= 1:
        raise ValueError("noise_percentile must be between 0 and 1")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _states_to_segments(
    states: list[bool], step_sec: float, duration_sec: float,
    min_speech_sec: float, min_pause_sec: float,
) -> list[tuple[float, float]]:
    raw: list[tuple[float, float]] = []
    start: float | None = None
    for index, state in enumerate(states + [False]):
        if state and start is None:
            start = index * step_sec
        elif not state and start is not None:
            end = min(index * step_sec, duration_sec)
            if end - start >= min_speech_sec:
                raw.append((start, end))
            start = None
    merged: list[tuple[float, float]] = []
    for current in raw:
        if merged and current[0] - merged[-1][1] < min_pause_sec:
            merged[-1] = (merged[-1][0], current[1])
        else:
            merged.append(current)
    return merged
