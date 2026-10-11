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


@dataclass(frozen=True)
class FileAuditRecord:
    """Результат аудита WAV-файла (TASK-01)."""

    file_id: str
    file_path: str
    duration_sec: float
    sample_rate: int
    n_channels: int
    bit_depth: int
    file_size_bytes: int
    is_valid: bool
    warnings: tuple[str, ...] = ()
    subject_id: str | None = None  # UNKNOWN до получения реальных данных
    task_type: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrameFeatureRecord:
    """Кадровые признаки (TASK-02)."""

    file_id: str
    subject_id: str | None
    task_type: str
    sample_rate: int
    frame_ms: float
    hop_ms: float
    n_frames: int
    feature_names: tuple[str, ...]
    feature_versions: dict[str, str]  # {"log_mel": "0.1.0", "mfcc": "0.1.0"}
    checksum_audio: str  # hash входного аудио
    checksum_config: str  # hash конфигурации признаков

    # Фактические признаки хранятся отдельно (parquet/npy)
    # Этот контракт — только метаданные

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperimentRecord:
    """Результат эксперимента (TASK-10)."""

    experiment_id: str
    config_hash: str
    dataset_version: str
    train_subjects: tuple[str, ...]
    val_subjects: tuple[str, ...]
    test_subjects: tuple[str, ...]
    model_name: str  # "energy", "webrtc", "custom_vad_v1"
    model_version: str
    metrics: dict[str, float]  # {"false_pause_precision": 0.85, ...}
    created_at: str  # ISO8601
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
