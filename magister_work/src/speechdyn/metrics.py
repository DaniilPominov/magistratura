"""Метрики качества VAD (Этап 1).

Две группы:

* **покадровые** — по выровненной временной сетке: ``precision``, ``recall``,
  ``f1``, ``iou``, ``false_pause_precision`` (первичная метрика проекта),
  ``speech_recall``, ``pause_duration_bias``;
* **покрытие сегментов** — ``segment_f1`` с допуском по краям.

Все функции принимают предсказанную и эталонную маски (списки bool) либо
отрезки, приведённые к сетке, чтобы результат был детерминирован.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import SegmentRecord


@dataclass(frozen=True)
class FrameMetrics:
    precision: float
    recall: float
    f1: float
    iou: float
    false_pause_precision: float
    speech_recall: float
    pause_duration_bias_sec: float
    n_frames: int


def frame_metrics(predicted: list[bool], reference: list[bool], hop_sec: float) -> FrameMetrics:
    """Покадровые метрики по двум булевым маскам равной длины."""
    if len(predicted) != len(reference):
        raise ValueError("predicted and reference masks must have equal length")
    n = len(predicted)
    if n == 0:
        return FrameMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    tp = sum(1 for p, r in zip(predicted, reference) if p and r)
    fp = sum(1 for p, r in zip(predicted, reference) if p and not r)
    fn = sum(1 for p, r in zip(predicted, reference) if not p and r)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    union = tp + fp + fn
    iou = tp / union if union else 0.0

    # false_pause_precision: доля верных пауз среди предсказанных пауз.
    pause_tp = sum(1 for p, r in zip(predicted, reference) if not p and not r)
    pause_fp = sum(1 for p, r in zip(predicted, reference) if not p and r)
    false_pause_precision = pause_tp / (pause_tp + pause_fp) if pause_tp + pause_fp else 1.0

    predicted_speech = sum(predicted) * hop_sec
    reference_speech = sum(reference) * hop_sec
    pause_duration_bias = reference_speech - predicted_speech

    return FrameMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        iou=iou,
        false_pause_precision=false_pause_precision,
        speech_recall=recall,
        pause_duration_bias_sec=pause_duration_bias,
        n_frames=n,
    )


def rasterize(
    segments: list[SegmentRecord],
    duration_sec: float,
    hop_sec: float,
    *,
    speech_labels: frozenset[str] = frozenset({"speech"}),
) -> list[bool]:
    """Отрезки -> булева маска на сетке с шагом `hop_sec`."""
    n = max(1, round(duration_sec / hop_sec))
    mask = [False] * n
    for segment in segments:
        start = max(0, round(segment.start_sec / hop_sec))
        end = min(n, round(segment.end_sec / hop_sec))
        active = segment.label in speech_labels
        for index in range(start, end):
            mask[index] = active
    return mask


def segment_f1(
    predicted: list[SegmentRecord],
    reference: list[SegmentRecord],
    tolerance_sec: float = 0.1,
) -> float:
    """F1 по совпадению отрезков с допуском по обоим краям."""
    matched_ref: set[int] = set()
    hits = 0
    for p in sorted(predicted, key=lambda s: s.start_sec):
        for index, r in enumerate(reference):
            if index in matched_ref:
                continue
            if (
                abs(p.start_sec - r.start_sec) <= tolerance_sec
                and abs(p.end_sec - r.end_sec) <= tolerance_sec
            ):
                matched_ref.add(index)
                hits += 1
                break
    if not predicted or not reference:
        return 0.0
    precision = hits / len(predicted)
    recall = hits / len(reference)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
