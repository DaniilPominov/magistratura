"""Energy VAD с гистерезисом — инженерная база Этапа 1.

Перенесён и упрощён из `voice_signals`. Алгоритм: RMS по кадрам -> дБ ->
шумовой порог как низкий перцентиль -> двухпороговое состояние
(вход `speech_threshold_db`, выход `release_threshold_db`) -> отрезки с
общей постобработкой.

`ASSUMPTION: sample_rate 16000` в конфиге — инженерное допущение; фактические
параметры фиксируются после аудита реального корпуса (правило 1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..contracts import SegmentRecord
from ..framing import TimeGrid, compute_rms_frames
from .base import VadBackend


@dataclass(frozen=True)
class EnergyVadConfig:
    frame_ms: float = 20.0
    hop_ms: float = 10.0
    speech_threshold_db: float = 10.0
    release_threshold_db: float = 6.0
    noise_percentile: float = 0.2
    min_speech_ms: float = 80.0
    min_pause_ms: float = 80.0

    def __post_init__(self) -> None:
        if self.release_threshold_db > self.speech_threshold_db:
            raise ValueError("release threshold cannot exceed speech threshold")
        if not 0.0 <= self.noise_percentile <= 1.0:
            raise ValueError("noise_percentile must be between 0 and 1")


class EnergyVad(VadBackend):
    name = "energy"
    version = "1.0.0"

    def __init__(self, config: EnergyVadConfig | None = None) -> None:
        self.config = config or EnergyVadConfig()
        self._frame_ms = self.config.frame_ms
        self._hop_ms = self.config.hop_ms
        self._min_speech_ms = self.config.min_speech_ms
        self._min_pause_ms = self.config.min_pause_ms

    def frame_activity(
        self,
        audio: list[float],
        sample_rate: int,
    ) -> tuple[list[float], list[bool]]:
        grid = TimeGrid.from_ms(sample_rate, self.config.frame_ms, self.config.hop_ms)
        times, rms = compute_rms_frames(audio, grid)
        if not rms:
            return [], []
        db = [10 * math.log10(value * value + 1e-12) for value in rms]
        baseline = _percentile(db, self.config.noise_percentile)

        active = False
        states: list[bool] = []
        for value in db:
            limit = self.config.release_threshold_db if active else self.config.speech_threshold_db
            active = value - baseline >= limit
            states.append(active)
        return times, states

    def activity_trace(
        self,
        audio: list[float],
        sample_rate: int,
    ) -> tuple[list[float], list[float], list[bool], float]:
        """Диагностика: (времена, дБ, активность, порог шума)."""
        grid = TimeGrid.from_ms(sample_rate, self.config.frame_ms, self.config.hop_ms)
        times, rms = compute_rms_frames(audio, grid)
        if not rms:
            return [], [], [], 0.0
        db = [10 * math.log10(value * value + 1e-12) for value in rms]
        baseline = _percentile(db, self.config.noise_percentile)
        active = False
        states: list[bool] = []
        for value in db:
            limit = self.config.release_threshold_db if active else self.config.speech_threshold_db
            active = value - baseline >= limit
            states.append(active)
        return times, db, states, baseline


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
