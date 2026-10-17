"""Local voice activity segmentation primitives."""

from .config import config_hash, load_config, validate_config
from .dynamics import HurstRSResult, modified_rs_hurst
from .framing import FrameScore, TimeGrid, compute_rms_frames
from .schemas import (
    ExperimentRecord,
    FileAuditRecord,
    FrameFeatureRecord,
    SegmentRecord,
    validate_non_overlapping,
)
from .vad import EnergyVad, EnergyVadConfig
from .vad_backend import VadBackend

__all__ = [
    # Core contracts
    "SegmentRecord",
    "FileAuditRecord",
    "FrameFeatureRecord",
    "ExperimentRecord",
    "validate_non_overlapping",
    # VAD
    "VadBackend",
    "EnergyVad",
    "EnergyVadConfig",
    # Framing
    "TimeGrid",
    "compute_rms_frames",
    "FrameScore",
    # Dynamics
    "HurstRSResult",
    "modified_rs_hurst",
    # Config
    "load_config",
    "config_hash",
    "validate_config",
]
