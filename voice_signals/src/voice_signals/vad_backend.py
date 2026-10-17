"""Unified VAD backend interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .schemas import SegmentRecord


class VadBackend(ABC):
    """Abstract base class for all VAD implementations."""
    
    name: str = "base"
    version: str = "0.0.0"
    
    @abstractmethod
    def process_array(
        self,
        audio: List[float],
        sample_rate: int,
        *,
        file_id: str = "array",
        subject_id: str | None = None,
        task_type: str = "vad",
    ) -> List[SegmentRecord]:
        """Process audio samples and return speech segments."""
        pass
    
    @abstractmethod
    def process_file(
        self,
        path: str | Path,
        *,
        subject_id: str | None = None,
        task_type: str = "vad",
    ) -> List[SegmentRecord]:
        """Process a WAV file and return speech segments."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r})"
