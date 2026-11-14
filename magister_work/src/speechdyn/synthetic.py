"""Синтетический генератор речи/пауз для тестов.

Детерминированный (seed), без внешних зависимостей. Не претендует на
имитацию реального корпуса — только проверка работоспособности алгоритмов.
"""

from __future__ import annotations

import math
import random

from .contracts import SegmentRecord


def synthetic_utterance(
    sample_rate: int = 16000,
    *,
    durations_sec: list[tuple[str, float]] | None = None,
    seed: int = 0,
    noise: float = 0.001,
) -> tuple[list[float], list[SegmentRecord]]:
    """Чередование речи и пауз. Возвращает (сигнал, ground truth речь).

    Речь — амплитудно-модулированный шум (формантоподобная огибающая),
    паузы — низкоамплитудный шум.
    """
    if durations_sec is None:
        durations_sec = [("speech", 0.8), ("pause", 0.5), ("speech", 1.2),
                         ("pause", 0.3), ("speech", 0.6)]
    rng = random.Random(seed)
    audio: list[float] = []
    truth: list[SegmentRecord] = []
    cursor = 0.0

    for kind, duration in durations_sec:
        n = int(round(duration * sample_rate))
        start = len(audio)
        for index in range(n):
            t = index / sample_rate
            if kind == "speech":
                carrier = math.sin(2 * math.pi * 120 * t) + 0.5 * math.sin(2 * math.pi * 220 * t)
                envelope = 0.5 + 0.5 * math.sin(2 * math.pi * 4 * t)
                sample = 0.3 * carrier * envelope + noise * (rng.random() * 2 - 1)
            else:
                sample = noise * (rng.random() * 2 - 1)
            audio.append(sample)

        if kind == "speech":
            truth.append(
                SegmentRecord(
                    file_id="synthetic",
                    start_sec=start / sample_rate,
                    end_sec=len(audio) / sample_rate,
                    label="speech",
                    source_backend="ground_truth",
                )
            )
        cursor = len(audio) / sample_rate
    return audio, truth


def speech_pause_sequence() -> list[tuple[str, float]]:
    return [("pause", 0.4), ("speech", 0.7), ("pause", 0.6),
            ("speech", 1.0), ("pause", 0.3), ("speech", 0.5)]
