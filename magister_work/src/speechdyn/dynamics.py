"""Модифицированный R/S-анализ: показатель Хёрста `H` и характерное время `T`.

Методика: Кузенков, Логинов (2014), «Использование метода нормированного
размаха…». Реализованы два протокола:

* ``modified_rs_hurst`` — **вариант C**: один сегмент (speech), окно
  огибающей 25 мс, `tau` до `N/2`. Диагностический признак, **не сопоставим**
  между сегментами разной длины и со статьёй. Результат помечен
  ``scope="segment"``, ``comparable_to_reference=False``.
* ``modified_rs_hurst_full_record`` — **вариант A**: вся запись с паузами,
  окно 100 мс, `tau` до `N`, геометрическая шкала. Сопоставим с таблицей 1
  статьи. Результат помечен ``scope="full_record"``,
  ``comparable_to_reference=True``.

`T` оценивается кусочно-линейным фитом (точка излома); кусочно-полиномиальный
вариант пока не реализован.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

_DEFAULT_R_SQUARED_THRESHOLD = 0.7


@dataclass(frozen=True)
class HurstRSResult:
    hurst_h: float | None
    characteristic_time_sec: float | None
    tau_values: tuple[int, ...]
    fit_r_squared: float | None
    valid: bool
    warnings: tuple[str, ...] = ()
    fit_method: str = "piecewise"
    scope: str = "segment"
    comparable_to_reference: bool = False
    input_length_sec: float | None = None
    tau_scale: str = "arithmetic"


def _geometric_taus(min_tau: int, max_tau: int, n_scales: int) -> list[int]:
    if max_tau <= min_tau or n_scales < 2:
        return [min_tau]
    ratio = (max_tau / min_tau) ** (1.0 / (n_scales - 1))
    rounded = sorted({max(min_tau, round(min_tau * ratio ** index)) for index in range(n_scales)})
    return [tau for tau in rounded if tau <= max_tau]


def _rs_for_window(chunk: list[float]) -> float | None:
    avg = mean(chunk)
    centered = [value - avg for value in chunk]
    running = 0.0
    cumulative: list[float] = []
    for value in centered:
        running += value
        cumulative.append(running)
    span = max(cumulative) - min(cumulative)
    deviation = math.sqrt(mean(value * value for value in centered))
    if deviation <= 1e-12:
        return None
    return span / deviation


def _mean_rs_at_tau(envelope: list[float], tau: int) -> float | None:
    stride = max(1, tau // 2)
    ratios = [
        ratio
        for start in range(0, len(envelope) - tau + 1, stride)
        if (ratio := _rs_for_window(envelope[start:start + tau])) is not None
    ]
    return mean(ratios) if ratios else None


def _fit_log_log(points: list[tuple[float, float]]) -> tuple[float, float, float | None]:
    x_mean = mean(point[0] for point in points)
    y_mean = mean(point[1] for point in points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    intercept = y_mean - slope * x_mean
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    total = sum((y - y_mean) ** 2 for _, y in points)
    return slope, intercept, 1.0 - residual / total if total > 0 else None


def _piecewise_characteristic_time(
    taus: list[int], rs_values: list[float], window_sec: float
) -> float:
    if len(taus) < 6:
        peak = max(range(len(rs_values)), key=rs_values.__getitem__)
        return taus[peak] * window_sec
    log_taus = [math.log(tau / 2) for tau in taus]
    log_rs = [math.log(value) for value in rs_values]
    best_index = len(taus) // 2
    best_residual = math.inf
    for break_index in range(2, len(taus) - 2):
        total = _segment_residual(log_taus, log_rs, break_index)
        if total < best_residual:
            best_residual = total
            best_index = break_index
    return taus[best_index] * window_sec


def _segment_residual(xs: list[float], ys: list[float], break_index: int) -> float:
    left = _ols(xs[:break_index + 1], ys[:break_index + 1])
    right = _ols(xs[break_index:], ys[break_index:])
    total = 0.0
    for x, y in zip(xs[:break_index + 1], ys[:break_index + 1]):
        total += (y - (left[0] + left[1] * x)) ** 2
    for x, y in zip(xs[break_index:], ys[break_index:]):
        total += (y - (right[0] + right[1] * x)) ** 2
    return total


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) < 2:
        return 0.0, (ys[0] if ys else 0.0)
    x_mean = mean(xs)
    y_mean = mean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator < 1e-12:
        return 0.0, y_mean
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator
    return y_mean - slope * x_mean, slope


def _compute_envelope(values: list[float], sample_rate: int, window_sec: float) -> list[float]:
    window = max(1, round(window_sec * sample_rate))
    return [
        math.sqrt(mean(value * value for value in values[index:index + window]))
        for index in range(0, len(values) - window + 1, window)
    ]


def _run(
    envelope: list[float],
    *,
    min_tau: int,
    max_tau: int | None,
    upper_divisor: int,
    tau_scale: str,
    n_geometric_scales: int,
    envelope_window_sec: float,
    r_squared_threshold: float,
    scope: str,
    comparable: bool,
    input_length_sec: float,
) -> HurstRSResult:
    if len(envelope) < 8 or max(envelope) - min(envelope) <= 1e-12:
        return HurstRSResult(None, None, (), None, False, ("constant_or_short_envelope",),
                             scope=scope, comparable_to_reference=comparable,
                             input_length_sec=input_length_sec, tau_scale=tau_scale)

    upper = min(max_tau, len(envelope) // upper_divisor) if max_tau is not None \
        else len(envelope) // upper_divisor
    if tau_scale == "geometric":
        taus = _geometric_taus(max(2, min_tau), upper, n_geometric_scales)
    else:
        taus = list(range(max(2, min_tau), upper + 1))

    points: list[tuple[float, float]] = []
    rs_values: list[float] = []
    valid_taus: list[int] = []
    for tau in taus:
        ratio = _mean_rs_at_tau(envelope, tau)
        if ratio is not None:
            points.append((math.log(tau / 2), math.log(ratio)))
            rs_values.append(ratio)
            valid_taus.append(tau)

    if len(points) < 3:
        return HurstRSResult(None, None, tuple(taus), None, False, ("insufficient_rs_scales",),
                             scope=scope, comparable_to_reference=comparable,
                             input_length_sec=input_length_sec, tau_scale=tau_scale)

    slope, _, r_squared = _fit_log_log(points)
    characteristic_time = _piecewise_characteristic_time(valid_taus, rs_values, envelope_window_sec)
    warnings = ["weak_log_log_fit"] if (r_squared is None or r_squared < r_squared_threshold) else []
    return HurstRSResult(slope, characteristic_time, tuple(taus), r_squared, True, tuple(warnings),
                         "piecewise", scope, comparable, input_length_sec, tau_scale)


def modified_rs_hurst(
    values: list[float],
    sample_rate: int,
    *,
    envelope_window_sec: float = 0.025,
    min_tau: int = 4,
    max_tau: int | None = None,
    tau_scale: str = "arithmetic",
    n_geometric_scales: int = 12,
    r_squared_threshold: float = _DEFAULT_R_SQUARED_THRESHOLD,
) -> HurstRSResult:
    """Вариант C: per-segment диагностический признак (несопоставим)."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(values) < 16:
        return HurstRSResult(None, None, (), None, False, ("input_too_short",),
                             scope="segment", comparable_to_reference=False, tau_scale=tau_scale)
    envelope = _compute_envelope(values, sample_rate, envelope_window_sec)
    return _run(envelope, min_tau=min_tau, max_tau=max_tau, upper_divisor=2, tau_scale=tau_scale,
                n_geometric_scales=n_geometric_scales, envelope_window_sec=envelope_window_sec,
                r_squared_threshold=r_squared_threshold, scope="segment", comparable=False,
                input_length_sec=len(values) / sample_rate)


def modified_rs_hurst_full_record(
    values: list[float],
    sample_rate: int,
    *,
    envelope_window_sec: float = 0.1,
    min_tau: int = 3,
    max_tau: int | None = None,
    n_geometric_scales: int = 16,
    r_squared_threshold: float = _DEFAULT_R_SQUARED_THRESHOLD,
) -> HurstRSResult:
    """Вариант A: вся запись с паузами, окно 100 мс, tau до N. Сопоставим со статьёй."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(values) < 16:
        return HurstRSResult(None, None, (), None, False, ("input_too_short",),
                             scope="full_record", comparable_to_reference=True, tau_scale="geometric")
    envelope = _compute_envelope(values, sample_rate, envelope_window_sec)
    return _run(envelope, min_tau=min_tau, max_tau=max_tau, upper_divisor=1, tau_scale="geometric",
                n_geometric_scales=n_geometric_scales, envelope_window_sec=envelope_window_sec,
                r_squared_threshold=r_squared_threshold, scope="full_record", comparable=True,
                input_length_sec=len(values) / sample_rate)
