"""Общие контракты данных проекта.

Единственный тип обмена между модулями — `SegmentRecord`. Все времена в
секундах, отрезки полуоткрытые `[start_sec, end_sec)` и не пересекаются.
`duration_sec` не может быть неположительной.

Таксономия разметки:
`speech`, `silent_pause`, `hesitation`, `artifact`.
Дыхание относится к `artifact`, лексические заполнители — к `speech`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

#: Полная таксономия разметки.
TAXONOMY: tuple[str, ...] = ("speech", "silent_pause", "hesitation", "artifact")

#: Допустимые метки в контракте (включая бинарную редукцию для Этапа 1).
SEGMENT_LABELS: frozenset[str] = frozenset(TAXONOMY) | {"non_speech"}

#: Таксономия Этапа 1 (VAD): только бинарное речь / не-речь.
STAGE1_LABELS: tuple[str, ...] = ("speech", "non_speech")


@dataclass(frozen=True)
class SegmentRecord:
    """Один временной отрезок файла с меткой."""

    file_id: str
    start_sec: float
    end_sec: float
    label: str
    source_backend: str
    score: float | None = None
    subject_id: str | None = None
    task_type: str = "vad"
    is_pseudo_label: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.start_sec < 0 or self.end_sec <= self.start_sec:
            raise ValueError("segment must satisfy 0 <= start_sec < end_sec")
        if self.label not in SEGMENT_LABELS:
            raise ValueError(f"unsupported label: {self.label}")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SegmentRecord":
        return cls(**dict(value))


def validate_non_overlapping(segments: list[SegmentRecord]) -> None:
    """Отклоняет пересечения, разрешая примыкающие отрезки."""
    ordered = sorted(segments, key=lambda segment: segment.start_sec)
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_sec < previous.end_sec:
            raise ValueError("segments overlap")


def complement_segments(
    segments: list[SegmentRecord],
    duration_sec: float,
    *,
    label: str = "non_speech",
    file_id: str = "array",
) -> list[SegmentRecord]:
    """Достраивает разбиение: речь из `segments` + промежутки как `label`.

    Возвращает полный набор непересекающихся отрезков, покрывающих
    `[0, duration_sec)`, пригодный для покадровой оценки Этапа 1.
    """
    ordered = sorted(segments, key=lambda segment: segment.start_sec)
    result: list[SegmentRecord] = []
    cursor = 0.0
    for segment in ordered:
        if segment.start_sec > cursor:
            result.append(
                SegmentRecord(
                    file_id=segment.file_id,
                    start_sec=cursor,
                    end_sec=segment.start_sec,
                    label=label,
                    source_backend=segment.source_backend,
                    subject_id=segment.subject_id,
                    task_type=segment.task_type,
                )
            )
        result.append(segment)
        cursor = max(cursor, segment.end_sec)
    if cursor < duration_sec:
        result.append(
            SegmentRecord(
                file_id=file_id,
                start_sec=cursor,
                end_sec=duration_sec,
                label=label,
                source_backend=ordered[0].source_backend if ordered else "none",
            )
        )
    return result
