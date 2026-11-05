"""speechdyn — сегментация речи (VAD) и признаки временной динамики.

Этап 1: детектор речевой активности (energy + энтропия фазового пространства)
с единым контрактом `SegmentRecord` и метриками качества.
"""

from .config import config_hash, load_config, validate_config
from .contracts import (
    STAGE1_LABELS,
    TAXONOMY,
    SegmentRecord,
    complement_segments,
    validate_non_overlapping,
)
from .dynamics import HurstRSResult, modified_rs_hurst, modified_rs_hurst_full_record
from .framing import FrameScore, TimeGrid, compute_rms_frames, parabolic_envelope
from .metrics import FrameMetrics, frame_metrics, rasterize, segment_f1
from .vad import (
    EnergyVad,
    EnergyVadConfig,
    EntropyVad,
    EntropyVadConfig,
    VadBackend,
    states_to_spans,
)
from .wav import read_wav_mono

__all__ = [
    "STAGE1_LABELS",
    "TAXONOMY",
    "SegmentRecord",
    "complement_segments",
    "validate_non_overlapping",
    "config_hash",
    "load_config",
    "validate_config",
    "FrameScore",
    "TimeGrid",
    "compute_rms_frames",
    "parabolic_envelope",
    "read_wav_mono",
    "VadBackend",
    "EnergyVad",
    "EnergyVadConfig",
    "EntropyVad",
    "EntropyVadConfig",
    "states_to_spans",
    "FrameMetrics",
    "frame_metrics",
    "rasterize",
    "segment_f1",
    "HurstRSResult",
    "modified_rs_hurst",
    "modified_rs_hurst_full_record",
]
