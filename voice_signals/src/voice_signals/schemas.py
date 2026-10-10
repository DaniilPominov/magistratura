"""Small data contracts shared by VAD components."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


LABELS = frozenset({"speech", "non_speech"})


@dataclass(frozen=True)
class SegmentRecord:
    file_id: str
    subject_id: str | None
    task_type: str
    start_sec: float
    end_sec: float
    label: str
    score: float | None
    source_backend: str
    is_pseudo_label: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.start_sec < 0 or self.end_sec <= self.start_sec:
            raise ValueError("segment must satisfy 0 <= start_sec < end_sec")
        if self.label not in LABELS:
            raise ValueError(f"unsupported label: {self.label}")
        if self.score is not None and not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SegmentRecord":
        return cls(**dict(value))


def validate_non_overlapping(segments: list[SegmentRecord]) -> None:
    """Reject overlaps while allowing adjacent segments."""
    ordered = sorted(segments, key=lambda segment: segment.start_sec)
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_sec < previous.end_sec:
            raise ValueError("segments overlap")
