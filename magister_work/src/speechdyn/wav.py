"""Чтение WAV строго в mono PCM.

Единственный поддерживаемый формат на этом этапе — mono 16-bit PCM WAV.
Любое отклонение — явная ошибка с понятным сообщением, без догадок о
свойствах данных. Дополнительные форматы вводятся отдельной задачей после
аудита реального корпуса.
"""

from __future__ import annotations

import wave
from pathlib import Path


def read_wav_mono(path: str | Path) -> tuple[list[float], int]:
    """Возвращает (отсчёты в [-1, 1], частота дискретизации)."""
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1:
            raise ValueError(
                f"only mono WAV is supported, got {source.getnchannels()} channels: {path}"
            )
        if source.getsampwidth() != 2:
            raise ValueError(
                f"only 16-bit PCM WAV is supported, got {source.getsampwidth() * 8}-bit: {path}"
            )
        sample_rate = source.getframerate()
        frames = source.readframes(source.getnframes())
    audio = [
        int.from_bytes(frames[index:index + 2], "little", signed=True) / 32768.0
        for index in range(0, len(frames), 2)
    ]
    return audio, sample_rate
