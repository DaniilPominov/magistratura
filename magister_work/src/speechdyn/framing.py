"""Единая временная сетка, RMS-кадры и параболическая огибающая.

`TimeGrid` — единственный источник соответствия «кадр ↔ время» для всех
модулей. Параболическая огибающая реализует способ из статьи
Кузенкова/Логинова (Нейроинформатика-2021): |отсчёт| умножается на
параболу (0 на краях окна, 1 в центре), берётся максимум по окну.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TimeGrid:
    """Соответствие кадров и времени на фиксированной частоте дискретизации."""

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
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        return cls(
            sample_rate,
            max(1, round(sample_rate * frame_ms / 1000)),
            max(1, round(sample_rate * hop_ms / 1000)),
        )

    def frame_times(self, n_frames: int) -> list[float]:
        """Центры кадров в секундах."""
        return [index * self.hop_sec for index in range(n_frames)]


def compute_rms_frames(
    audio: list[float],
    grid: TimeGrid,
) -> tuple[list[float], list[float]]:
    """RMS на временной сетке. Возвращает (времена, RMS)."""
    values: list[float] = []
    for start in range(0, len(audio) - grid.frame_samples + 1, grid.hop_samples):
        chunk = audio[start:start + grid.frame_samples]
        values.append(math.sqrt(sum(sample * sample for sample in chunk) / len(chunk)))
    return grid.frame_times(len(values)), values


@dataclass(frozen=True)
class FrameScore:
    """Покадровый результат VAD (для диагностики и метрик)."""

    time_sec: float
    value: float
    is_active: bool
    baseline: float | None = None


def _parabola(window_samples: int) -> list[float]:
    """Парабола: 0 на краях, 1 в центре."""
    if window_samples <= 1:
        return [1.0]
    span = window_samples - 1
    return [
        1.0 - ((2.0 * index / span) - 1.0) ** 2
        for index in range(window_samples)
    ]


def parabolic_envelope(
    audio: list[float],
    sample_rate: int,
    *,
    window_ms: float = 10.0,
    hop_ms: float = 10.0,
) -> tuple[list[float], list[float]]:
    """Огибающая по способу Кузенкова/Логинова (2021).

    Для каждого положения окна `max(|x_i| * parabola_i)` — огибающая
    приближена к локальным максимумам, устойчива к смене формы сигнала.
    Возвращает (времена, значения огибающей).
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    window = max(2, round(sample_rate * window_ms / 1000))
    hop = max(1, round(sample_rate * hop_ms / 1000))
    weights = _parabola(window)
    times: list[float] = []
    values: list[float] = []
    last_start = len(audio) - window
    start = 0
    while start <= last_start:
        chunk = audio[start:start + window]
        peak = max(abs(sample) * weight for sample, weight in zip(chunk, weights))
        times.append((start + window / 2) / sample_rate)
        values.append(peak)
        start += hop
    return times, values
