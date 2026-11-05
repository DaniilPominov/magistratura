"""Единый интерфейс всех VAD-бэкендов.

Каждый бэкенд возвращает `list[SegmentRecord]` с непересекающимися
отрезками. Это позволяет сравнивать energy-базу, WebRTC и собственный
энтропийный детектор на одном наборе метрик без изменения вызывающего кода.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..contracts import (
    SegmentRecord,
    validate_non_overlapping,
)
from ..wav import read_wav_mono


class VadBackend(ABC):
    name: str = "base"
    version: str = "0.0.0"

    @abstractmethod
    def frame_activity(
        self,
        audio: list[float],
        sample_rate: int,
    ) -> tuple[list[float], list[bool]]:
        """Возвращает (времена кадров, признак активности) на общей сетке."""

    def process_array(
        self,
        audio: list[float],
        sample_rate: int,
        *,
        file_id: str = "array",
        subject_id: str | None = None,
        task_type: str = "vad",
    ) -> list[SegmentRecord]:
        _, active = self.frame_activity(audio, sample_rate)
        return self._segments(active, audio, sample_rate, file_id, subject_id, task_type)

    def process_file(
        self,
        path: str | Path,
        *,
        subject_id: str | None = None,
        task_type: str = "vad",
    ) -> list[SegmentRecord]:
        audio, sample_rate = read_wav_mono(path)
        return self.process_array(
            audio,
            sample_rate,
            file_id=Path(path).stem,
            subject_id=subject_id,
            task_type=task_type,
        )

    # --- общая постобработка: состояния -> отрезки ---------------------

    def _segments(
        self,
        active: list[bool],
        audio: list[float],
        sample_rate: int,
        file_id: str,
        subject_id: str | None,
        task_type: str,
    ) -> list[SegmentRecord]:
        from ..framing import TimeGrid

        grid = TimeGrid.from_ms(sample_rate, self._frame_ms, self._hop_ms)
        duration = len(audio) / sample_rate
        spans = states_to_spans(
            active,
            grid.hop_sec,
            duration,
            min_speech_sec=self._min_speech_ms / 1000,
            min_pause_sec=self._min_pause_ms / 1000,
        )
        segments = [
            SegmentRecord(
                file_id=file_id,
                start_sec=start,
                end_sec=end,
                label="speech",
                source_backend=self.name,
                subject_id=subject_id,
                task_type=task_type,
                notes=f"version={self.version}",
            )
            for start, end in spans
        ]
        validate_non_overlapping(segments)
        return segments

    # Параметры постобработки задаются наследником.
    _frame_ms: float = 20.0
    _hop_ms: float = 10.0
    _min_speech_ms: float = 80.0
    _min_pause_ms: float = 80.0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r})"


def states_to_spans(
    states: list[bool],
    step_sec: float,
    duration_sec: float,
    *,
    min_speech_sec: float,
    min_pause_sec: float,
) -> list[tuple[float, float]]:
    """Состояния по кадрам -> непересекающиеся отрезки речи.

    1. короткие всплески речи (< `min_speech_sec`) отбрасываются;
    2. короткие разрывы (< `min_pause_sec`) склеиваются.
    """
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
