"""Unified framing utilities for time grid and RMS envelope computation."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TimeGrid:
    """Единая временная сетка для всех модулей."""

    sample_rate: int
    frame_samples: int
    hop_samples: int

    @property
    def frame_sec(self) -> float:
        return self.frame_samples / self.sample_rate

    @property
    def hop_sec(self) -> float:
        return self.hop_samples / self.sample_rate

    @classmethod
    def from_ms(cls, sample_rate: int, frame_ms: float, hop_ms: float) -> "TimeGrid":
        return cls(
            sample_rate,
            max(1, round(sample_rate * frame_ms / 1000)),
            max(1, round(sample_rate * hop_ms / 1000)),
        )

    def frame_times(self, n_frames: int) -> list[float]:
        """Возвращает центры кадров в секундах."""
        return [i * self.hop_sec for i in range(n_frames)]


def compute_rms_frames(
    audio: list[float] | tuple[float, ...],
    grid: TimeGrid,
) -> tuple[list[float], list[float]]:
    """Вычисляет RMS-огибающую на временной сетке.

    Returns:
        (times_sec, rms_values): центры кадров и RMS-значения
    """
    frames = []
    for start in range(0, len(audio) - grid.frame_samples + 1, grid.hop_samples):
        chunk = audio[start : start + grid.frame_samples]
        if chunk:
            rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
            frames.append(rms)
    times = grid.frame_times(len(frames))
    return times, frames


@dataclass(frozen=True)
class FrameScore:
    """Кадровые результаты VAD."""

    time_sec: float
    energy_db: float
    is_speech: bool
    baseline_db: float | None = None
