"""Interpretable temporal-dynamics features for the first VAD iteration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

from .framing import TimeGrid, compute_rms_frames


@dataclass(frozen=True)
class HurstRSResult:
    hurst_h: float | None
    characteristic_time_sec: float | None
    tau_values: tuple[int, ...]
    fit_r_squared: float | None
    valid: bool
    warnings: tuple[str, ...] = ()


def modified_rs_hurst(
    values: list[float],
    sample_rate: int,
    *,
    envelope_window_sec: float = 0.025,
    min_tau: int = 4,
    max_tau: int | None = None,
    precomputed_envelope: list[float] | None = None,
) -> HurstRSResult:
    """Estimate H and a coarse T from overlapping R/S windows.

    This is deliberately a diagnostic feature, not a standalone speech
    decision. Short or constant inputs return an invalid result.
    
    Args:
        values: Audio samples or pre-computed RMS values
        sample_rate: Sample rate in Hz (or effective rate for envelope)
        envelope_window_sec: Window size for envelope computation (ignored if precomputed_envelope is provided)
        min_tau: Minimum tau for R/S analysis
        max_tau: Maximum tau for R/S analysis (auto: len(envelope) // 2)
        precomputed_envelope: Optional pre-computed RMS envelope
    """
    warnings: list[str] = []
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(values) < 16:
        return HurstRSResult(None, None, (), None, False, ("input_too_short",))
    if not all(math.isfinite(value) for value in values):
        return HurstRSResult(None, None, (), None, False, ("non_finite_input",))
    
    # Use precomputed envelope or compute it
    if precomputed_envelope is not None:
        envelope = precomputed_envelope
    else:
        window = max(1, round(envelope_window_sec * sample_rate))
        envelope = [
            math.sqrt(mean(value * value for value in values[index:index + window]))
            for index in range(0, len(values) - window + 1, window)
        ]
    
    if len(envelope) < 8 or max(envelope) - min(envelope) <= 1e-12:
        return HurstRSResult(None, None, (), None, False, ("constant_or_short_envelope",))

    upper = min(max_tau or len(envelope) // 2, len(envelope) // 2)
    taus = tuple(tau for tau in range(max(2, min_tau), upper + 1) if tau >= 2)
    points: list[tuple[float, float]] = []
    rs_by_tau: list[float] = []
    valid_taus: list[int] = []
    for tau in taus:
        ratios: list[float] = []
        for start in range(0, len(envelope) - tau + 1, max(1, tau // 2)):
            chunk = envelope[start:start + tau]
            centered = [item - mean(chunk) for item in chunk]
            cumulative: list[float] = []
            running = 0.0
            for item in centered:
                running += item
                cumulative.append(running)
            span = max(cumulative) - min(cumulative)
            deviation = math.sqrt(mean(item * item for item in centered))
            if deviation > 1e-12:
                ratios.append(span / deviation)
        if ratios:
            rs = mean(ratios)
            points.append((math.log(tau / 2), math.log(rs)))
            rs_by_tau.append(rs)
            valid_taus.append(tau)
    if len(points) < 3:
        return HurstRSResult(None, None, taus, None, False, ("insufficient_rs_scales",))

    x_mean, y_mean = mean(point[0] for point in points), mean(point[1] for point in points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    intercept = y_mean - slope * x_mean
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    total = sum((y - y_mean) ** 2 for _, y in points)
    r_squared = 1.0 - residual / total if total > 0 else None
    peak_index = max(range(len(rs_by_tau)), key=rs_by_tau.__getitem__)
    characteristic_time = valid_taus[peak_index] * envelope_window_sec
    if r_squared is None or r_squared < 0.7:
        warnings.append("weak_log_log_fit")
    return HurstRSResult(slope, characteristic_time, taus, r_squared, True, tuple(warnings))
