"""VAD на энтропии заполнения фазового пространства.

Реализация метода Кузенкова/Логинова из сборника «Нейроинформатика-2021»,
раздел «Обнаружение речевой активности с использованием метода энтропии
заполнения фазового пространства».

Идея:
* траектория сигнала в 2D-фазовом пространстве ``{(x_n, x_{n+k})}``, задержка
  ``k`` — характерное время в отсчётах;
* фазовую плоскость делим на ``N x N`` квадратов, считаем вероятности
  ``p_i = m_i / M_k``, ``M_k = M - 2k``;
* энтропия ``S_k = -sum_i p_i log2 p_i``;
* для каждого окна берём трёхмерный вектор признаков
  ``(ln E, <S>, sigma(S))``, где ``E`` — параболическая огибающая;
* решающее правило: окно — пауза, если ``ln E < lnE_thr`` **или** энтропийная
  точка лежит внутри сферы ``(c_s - <S>)^2 + (c_sigma - sigma(S))^2 < r^2``;
  иначе — речь.

Числовые пороги (``lnE_thr = -5.0``, центр ``(3.43, 0.0653)``, радиус²
``0.0288``) взяты из статьи для записей с SNR не хуже 35 дБ. Они вынесены в
конфигурацию как **стартовые**, а не окончательные: калибровка на целевом
корпусе пока не выполнена.

ASSUMPTION: сигнал нормируется по пику к 1 перед расчётом (``ln E``
масштабно-зависима). Реальная нормировка согласуется после аудита корпуса.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..framing import parabolic_envelope
from .base import VadBackend, states_to_spans


@dataclass(frozen=True)
class EntropyVadConfig:
    # Сетка анализа энтропии.
    window_ms: float = 100.0
    hop_ms: float = 25.0
    n_bins: int = 10
    k_min: int = 2
    k_max: int = 16
    # Огибающая.
    envelope_window_ms: float = 10.0
    # Общая постобработка.
    frame_ms: float = 25.0
    min_speech_ms: float = 80.0
    min_pause_ms: float = 80.0
    # Стартовые пороги статьи (SNR >= 35 дБ).
    ln_e_threshold: float = -5.0
    entropy_center_s: float = 3.43
    entropy_center_sigma: float = 0.0653
    entropy_radius_sq: float = 0.0288

    def __post_init__(self) -> None:
        if self.n_bins < 2:
            raise ValueError("n_bins must be >= 2")
        if self.k_min < 1 or self.k_max <= self.k_min:
            raise ValueError("require 1 <= k_min < k_max")


def phase_space_entropy(
    values: list[float],
    n_bins: int,
    k: int,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    """Энтропия заполнения фазового пространства для одной задержки `k`.

    Занятость квадратов считается в плоский список размера `n_bins**2`
    (без словаря) — заметно быстрее на длинных окнах. `lo`/`hi` можно
    передать заранее, чтобы не пересчитывать минимум/максимум для каждого
    `k` внутри одного окна.
    """
    m = len(values)
    count = m - 2 * k
    if count <= 0:
        return 0.0
    if lo is None:
        lo = min(values)
    if hi is None:
        hi = max(values)
    span = hi - lo
    if span <= 1e-12:
        return 0.0
    inv = n_bins / span
    n_cells = n_bins * n_bins
    occupancy = [0] * n_cells
    for index in range(count):
        bx = int((values[index] - lo) * inv)
        if bx >= n_bins:
            bx = n_bins - 1
        elif bx < 0:
            bx = 0
        by = int((values[index + k] - lo) * inv)
        if by >= n_bins:
            by = n_bins - 1
        elif by < 0:
            by = 0
        occupancy[bx * n_bins + by] += 1
    total = 0.0
    for hits in occupancy:
        if hits:
            p = hits / count
            total -= p * math.log2(p)
    return total


def window_entropy_features(
    values: list[float],
    sample_rate: int,
    config: EntropyVadConfig,
) -> list[tuple[float, float, float]]:
    """Признаки ``(время, lnE, <S>, sigma(S))`` по окнам.

    Огибающая ``lnE`` берётся в центре окна; ``<S>`` и ``sigma(S)`` — среднее
    и СКО энтропии по задержкам ``k_min..k_max`` внутри окна.
    """
    env_times, env_values = parabolic_envelope(
        values, sample_rate,
        window_ms=config.envelope_window_ms,
        hop_ms=config.envelope_window_ms,
    )
    window = max(4, round(sample_rate * config.window_ms / 1000))
    hop = max(1, round(sample_rate * config.hop_ms / 1000))
    env_hop_sec = config.envelope_window_ms / 1000

    features: list[tuple[float, float, float]] = []
    start = 0
    while start + window <= len(values):
        chunk = values[start:start + window]
        lo = min(chunk)
        hi = max(chunk)
        entropies = [
            phase_space_entropy(chunk, config.n_bins, k, lo=lo, hi=hi)
            for k in range(config.k_min, config.k_max + 1)
        ]
        mean_s = sum(entropies) / len(entropies)
        variance = sum((value - mean_s) ** 2 for value in entropies) / len(entropies)
        sigma_s = math.sqrt(variance)

        center_sec = (start + window / 2) / sample_rate
        ln_e = _sample_envelope(env_times, env_values, center_sec, hop_sec=env_hop_sec)
        features.append((center_sec, ln_e, mean_s, sigma_s))
        start += hop
    return features


def _sample_envelope(
    times: list[float],
    values: list[float],
    target: float,
    *,
    hop_sec: float | None = None,
) -> float:
    if not values:
        return -30.0
    if hop_sec and hop_sec > 0 and len(times) > 1:
        index = round((target - times[0]) / hop_sec)
        index = min(len(values) - 1, max(0, index))
    else:
        index = min(range(len(times)), key=lambda position: abs(times[position] - target))
    return math.log(max(values[index], 1e-12))


class EntropyVad(VadBackend):
    name = "entropy"
    version = "0.1.0"

    def __init__(self, config: EntropyVadConfig | None = None) -> None:
        self.config = config or EntropyVadConfig()
        self._frame_ms = self.config.frame_ms
        self._hop_ms = self.config.hop_ms
        self._min_speech_ms = self.config.min_speech_ms
        self._min_pause_ms = self.config.min_pause_ms

    def is_pause(self, ln_e: float, mean_s: float, sigma_s: float) -> bool:
        if ln_e < self.config.ln_e_threshold:
            return True
        ds = self.config.entropy_center_s - mean_s
        dg = self.config.entropy_center_sigma - sigma_s
        return ds * ds + dg * dg < self.config.entropy_radius_sq

    def frame_activity(
        self,
        audio: list[float],
        sample_rate: int,
    ) -> tuple[list[float], list[bool]]:
        peak = max((abs(sample) for sample in audio), default=0.0)
        if peak <= 1e-12:
            return [], []
        normalized = [sample / peak for sample in audio]
        features = window_entropy_features(normalized, sample_rate, self.config)
        times = [time for time, _, _ in features]
        active = [
            not self.is_pause(ln_e, mean_s, sigma_s)
            for _, ln_e, mean_s, sigma_s in features
        ]
        return times, active

    def process_array(self, audio, sample_rate, *, file_id="array", subject_id=None, task_type="vad"):
        # Сетка окон энтропии может не совпадать с сеткой постобработки,
        # поэтому отрезки строим по фактическому шагу окна.
        peak = max((abs(sample) for sample in audio), default=0.0)
        if peak <= 1e-12:
            return []
        normalized = [sample / peak for sample in audio]
        features = window_entropy_features(normalized, sample_rate, self.config)
        active = [
            not self.is_pause(ln_e, mean_s, sigma_s)
            for _, ln_e, mean_s, sigma_s in features
        ]
        step = self.config.hop_ms / 1000
        duration = len(audio) / sample_rate
        spans = states_to_spans(
            active,
            step,
            duration,
            min_speech_sec=self.config.min_speech_ms / 1000,
            min_pause_sec=self.config.min_pause_ms / 1000,
        )
        from ..contracts import SegmentRecord, validate_non_overlapping

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
