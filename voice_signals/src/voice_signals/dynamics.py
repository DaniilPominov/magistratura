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
    fit_method: str = "argmax"  # "argmax" or "piecewise"


def modified_rs_hurst(
    values: list[float],
    sample_rate: int,
    *,
    envelope_window_sec: float = 0.025,
    min_tau: int = 4,
    max_tau: int | None = None,
    precomputed_envelope: list[float] | None = None,
    use_piecewise_fit: bool = True,
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
    
    # Compute characteristic time T
    fit_method = "argmax"
    if use_piecewise_fit and len(points) >= 6:
        # Piecewise linear fit: find breakpoint that minimizes total residual
        characteristic_time = _piecewise_fit_characteristic_time(
            valid_taus, rs_by_tau, envelope_window_sec
        )
        fit_method = "piecewise"
    else:
        # Fallback: simple argmax
        peak_index = max(range(len(rs_by_tau)), key=rs_by_tau.__getitem__)
        characteristic_time = valid_taus[peak_index] * envelope_window_sec
    
    if r_squared is None or r_squared < 0.7:
        warnings.append("weak_log_log_fit")
    return HurstRSResult(slope, characteristic_time, taus, r_squared, True, tuple(warnings), fit_method)


def _piecewise_fit_characteristic_time(
    taus: list[int],
    rs_values: list[float],
    window_sec: float
) -> float:
    """Find characteristic time using piecewise linear fit.
    
    Searches for breakpoint where two linear segments meet, minimizing
    total residual. Returns tau at the breakpoint.
    """
    if len(taus) < 6:
        # Fallback to argmax
        peak_idx = max(range(len(rs_values)), key=rs_values.__getitem__)
        return taus[peak_idx] * window_sec
    
    log_taus = [math.log(tau / 2) for tau in taus]
    log_rs = [math.log(rs) for rs in rs_values]
    
    best_breakpoint_idx = len(taus) // 2
    min_residual = float('inf')
    
    # Try each potential breakpoint (excluding first 2 and last 2)
    for break_idx in range(2, len(taus) - 2):
        # Fit left segment
        left_x = log_taus[:break_idx + 1]
        left_y = log_rs[:break_idx + 1]
        if len(left_x) < 2:
            continue
        
        left_x_mean = mean(left_x)
        left_y_mean = mean(left_y)
        left_denom = sum((x - left_x_mean) ** 2 for x in left_x)
        if left_denom < 1e-12:
            continue
        left_slope = sum((x - left_x_mean) * (y - left_y_mean) for x, y in zip(left_x, left_y)) / left_denom
        left_intercept = left_y_mean - left_slope * left_x_mean
        
        # Fit right segment
        right_x = log_taus[break_idx:]
        right_y = log_rs[break_idx:]
        if len(right_x) < 2:
            continue
        
        right_x_mean = mean(right_x)
        right_y_mean = mean(right_y)
        right_denom = sum((x - right_x_mean) ** 2 for x in right_x)
        if right_denom < 1e-12:
            continue
        right_slope = sum((x - right_x_mean) * (y - right_y_mean) for x, y in zip(right_x, right_y)) / right_denom
        right_intercept = right_y_mean - right_slope * right_x_mean
        
        # Calculate total residual
        left_residual = sum((y - (left_intercept + left_slope * x)) ** 2 for x, y in zip(left_x, left_y))
        right_residual = sum((y - (right_intercept + right_slope * x)) ** 2 for x, y in zip(right_x, right_y))
        total_residual = left_residual + right_residual
        
        if total_residual < min_residual:
            min_residual = total_residual
            best_breakpoint_idx = break_idx
    
    return taus[best_breakpoint_idx] * window_sec

