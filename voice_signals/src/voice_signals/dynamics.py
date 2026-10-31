"""Interpretable temporal-dynamics features for the first VAD iteration.

Two protocols are supported, following the methodology gap analysis in
`docs/rs-methodology-gap-2026-10-31.md` (decision: variant A + C):

- **full_record** (variant A): one R/S series per recording, built on the
  envelope of the *entire* file including pauses, with a geometric tau
  scale up to `N` — matching Kuzenkov & Loginov (2014). Use
  `modified_rs_hurst_full_record()`. Values are comparable to the paper's
  Table 1.
- **segment** (variant C): the legacy per-segment calculation on VAD-trimmed
  speech only. Kept as a distinct feature, explicitly marked
  non-comparable across segments of different length and not comparable to
  the paper. Use `modified_rs_hurst()` (default `scope="segment"`).

Both protocols share the same core R/S-by-tau estimator; they differ in the
envelope window, the tau scale construction, and the upper tau bound.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

__all__ = [
    "HurstRSResult",
    "modified_rs_hurst",
    "modified_rs_hurst_full_record",
]

_DEFAULT_R_SQUARED_THRESHOLD = 0.7

# Above this many arithmetic-scale tau values, the O(N^2) R/S curve (and the
# O(k^2) piecewise breakpoint search over its taus) becomes expensive enough
# that it is almost certainly a misuse of the per-segment function on a
# much longer series than intended (e.g. a whole recording passed to
# modified_rs_hurst() instead of modified_rs_hurst_full_record()). Measured:
# ~27s for a 124s/8kHz full-record input (2477 taus) vs. ~0.6s for the same
# input through the geometric full-record path (16 taus).
_ARITHMETIC_TAU_COUNT_GUARD = 200


@dataclass(frozen=True)
class HurstRSResult:
    hurst_h: float | None
    characteristic_time_sec: float | None
    tau_values: tuple[int, ...]
    fit_r_squared: float | None
    valid: bool
    warnings: tuple[str, ...] = ()
    fit_method: str = "argmax"  # "argmax" or "piecewise"
    scope: str = "segment"  # "segment" (variant C) or "full_record" (variant A)
    comparable_to_reference: bool = False
    input_length_sec: float | None = None
    tau_scale: str = "arithmetic"  # "arithmetic" or "geometric"


def _geometric_taus(min_tau: int, max_tau: int, n_scales: int) -> list[int]:
    """Geometric tau progression per Kuzenkov/Loginov (2014), §"Модификация".

    tau_1 = min_tau, tau_i = a * tau_(i-1), a = (max_tau / min_tau) ** (1 / (n-1)).
    Returned as integers (rounded), deduplicated, ascending.
    """
    if max_tau <= min_tau:
        return [min_tau]
    if n_scales < 2:
        return [min_tau]
    ratio = (max_tau / min_tau) ** (1.0 / (n_scales - 1))
    raw = [min_tau * (ratio ** i) for i in range(n_scales)]
    rounded = sorted({max(min_tau, round(value)) for value in raw})
    return [tau for tau in rounded if tau <= max_tau]


def _rs_for_window(chunk: list[float]) -> float | None:
    """Rescaled range R/S for one window, per the classical R/S formulas."""
    avg = mean(chunk)
    centered = [item - avg for item in chunk]
    running = 0.0
    cumulative: list[float] = []
    for item in centered:
        running += item
        cumulative.append(running)
    span = max(cumulative) - min(cumulative)
    deviation = math.sqrt(mean(item * item for item in centered))
    if deviation <= 1e-12:
        return None
    return span / deviation


def _mean_rs_at_tau(envelope: list[float], tau: int) -> float | None:
    """Average R/S over overlapping windows of length tau across the envelope."""
    stride = max(1, tau // 2)
    ratios = [
        rs
        for start in range(0, len(envelope) - tau + 1, stride)
        if (rs := _rs_for_window(envelope[start:start + tau])) is not None
    ]
    if not ratios:
        return None
    return mean(ratios)


def _fit_log_log(points: list[tuple[float, float]]) -> tuple[float, float, float | None]:
    """OLS fit of ln(R/S) vs ln(tau/2). Returns (slope, intercept, r_squared)."""
    x_mean = mean(point[0] for point in points)
    y_mean = mean(point[1] for point in points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    intercept = y_mean - slope * x_mean
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    total = sum((y - y_mean) ** 2 for _, y in points)
    r_squared = 1.0 - residual / total if total > 0 else None
    return slope, intercept, r_squared


def _rs_curve(
    envelope: list[float],
    *,
    min_tau: int,
    upper: int,
    tau_scale: str,
    n_geometric_scales: int,
) -> tuple[tuple[int, ...], list[tuple[float, float]], list[float], list[int]]:
    """Build the (tau, ln(tau/2), ln(R/S)) curve for either tau scale.

    Returns (all_taus_considered, log_log_points, rs_by_tau, valid_taus).
    """
    if tau_scale == "geometric":
        taus = tuple(_geometric_taus(max(2, min_tau), upper, n_geometric_scales))
    else:
        taus = tuple(tau for tau in range(max(2, min_tau), upper + 1) if tau >= 2)

    points: list[tuple[float, float]] = []
    rs_by_tau: list[float] = []
    valid_taus: list[int] = []
    for tau in taus:
        rs = _mean_rs_at_tau(envelope, tau)
        if rs is not None:
            points.append((math.log(tau / 2), math.log(rs)))
            rs_by_tau.append(rs)
            valid_taus.append(tau)
    return taus, points, rs_by_tau, valid_taus


def _compute_envelope(
    values: list[float],
    sample_rate: int,
    envelope_window_sec: float,
) -> list[float]:
    window = max(1, round(envelope_window_sec * sample_rate))
    return [
        math.sqrt(mean(value * value for value in values[index:index + window]))
        for index in range(0, len(values) - window + 1, window)
    ]


def _run_rs_analysis(
    envelope: list[float],
    *,
    min_tau: int,
    max_tau: int | None,
    upper_bound_divisor: int,
    tau_scale: str,
    n_geometric_scales: int,
    use_piecewise_fit: bool,
    envelope_window_sec: float,
    r_squared_threshold: float,
    scope: str,
    comparable_to_reference: bool,
    input_length_sec: float,
) -> HurstRSResult:
    if len(envelope) < 8 or max(envelope) - min(envelope) <= 1e-12:
        return HurstRSResult(
            None, None, (), None, False, ("constant_or_short_envelope",),
            scope=scope, comparable_to_reference=comparable_to_reference,
            input_length_sec=input_length_sec, tau_scale=tau_scale,
        )

    natural_upper = len(envelope) // upper_bound_divisor
    upper = min(max_tau, natural_upper) if max_tau is not None else natural_upper

    if tau_scale == "arithmetic":
        approx_tau_count = max(0, upper - max(2, min_tau) + 1)
        if approx_tau_count > _ARITHMETIC_TAU_COUNT_GUARD:
            raise ValueError(
                f"arithmetic tau scale would produce {approx_tau_count} tau "
                f"values (envelope length {len(envelope)}), which is O(N^2) "
                "and likely unintended; this usually means whole-recording "
                "audio was passed to the per-segment function. Use "
                "modified_rs_hurst_full_record() for whole-file input, or "
                "pass tau_scale='geometric' if a large arithmetic-style "
                "sweep is genuinely intended."
            )

    taus, points, rs_by_tau, valid_taus = _rs_curve(
        envelope,
        min_tau=min_tau,
        upper=upper,
        tau_scale=tau_scale,
        n_geometric_scales=n_geometric_scales,
    )
    if len(points) < 3:
        return HurstRSResult(
            None, None, taus, None, False, ("insufficient_rs_scales",),
            scope=scope, comparable_to_reference=comparable_to_reference,
            input_length_sec=input_length_sec, tau_scale=tau_scale,
        )

    slope, _intercept, r_squared = _fit_log_log(points)

    fit_method = "argmax"
    if use_piecewise_fit and len(points) >= 6:
        characteristic_time = _piecewise_fit_characteristic_time(
            valid_taus, rs_by_tau, envelope_window_sec
        )
        fit_method = "piecewise"
    else:
        peak_index = max(range(len(rs_by_tau)), key=rs_by_tau.__getitem__)
        characteristic_time = valid_taus[peak_index] * envelope_window_sec

    warnings: list[str] = []
    if r_squared is None or r_squared < r_squared_threshold:
        warnings.append("weak_log_log_fit")

    return HurstRSResult(
        slope, characteristic_time, taus, r_squared, True, tuple(warnings),
        fit_method, scope=scope, comparable_to_reference=comparable_to_reference,
        input_length_sec=input_length_sec, tau_scale=tau_scale,
    )


def modified_rs_hurst(
    values: list[float],
    sample_rate: int,
    *,
    envelope_window_sec: float = 0.025,
    min_tau: int = 4,
    max_tau: int | None = None,
    precomputed_envelope: list[float] | None = None,
    use_piecewise_fit: bool = True,
    tau_scale: str = "arithmetic",
    n_geometric_scales: int = 12,
    r_squared_threshold: float = _DEFAULT_R_SQUARED_THRESHOLD,
) -> HurstRSResult:
    """Estimate H and a coarse T from overlapping R/S windows on one segment.

    This is variant **C** of the methodology decision in
    `docs/rs-methodology-gap-2026-10-31.md`: a per-segment diagnostic
    feature, explicitly **not comparable** across segments of different
    length and **not comparable** to Kuzenkov/Loginov (2014) Table 1 (that
    requires the whole-record protocol, see `modified_rs_hurst_full_record`).
    The result always carries `scope="segment"` and
    `comparable_to_reference=False` so downstream consumers cannot conflate
    the two.

    Short or constant inputs return an invalid result.

    Args:
        values: Audio samples or pre-computed RMS values.
        sample_rate: Sample rate in Hz (or effective rate for envelope).
        envelope_window_sec: Window size for envelope computation (ignored
            if precomputed_envelope is provided).
        min_tau: Minimum tau for R/S analysis.
        max_tau: Maximum tau for R/S analysis. `None` means "auto":
            `len(envelope) // 2`. Explicit `0` is treated literally (an
            empty tau range -> invalid result), it is no longer coerced to
            "auto".
        precomputed_envelope: Optional pre-computed RMS envelope.
        tau_scale: "arithmetic" (legacy, `range(min_tau, upper+1)`) or
            "geometric" (Kuzenkov/Loginov progression). Geometric is closer
            to the reference algorithm but still bounded by the segment
            length, so it does not by itself make per-segment values
            comparable to the paper.
        n_geometric_scales: Number of tau points when `tau_scale="geometric"`.
        r_squared_threshold: Threshold below which `weak_log_log_fit` is
            warned. Previously hard-coded to 0.7; now a parameter so the
            config value is actually used (see methodology gap doc, §5.2).

    Raises:
        ValueError: if `tau_scale="arithmetic"` (the default) would produce
            more than `_ARITHMETIC_TAU_COUNT_GUARD` tau values. The
            arithmetic scale is O(N) taus x O(N) work per tau, i.e. O(N^2)
            total; this guard catches whole-recording audio accidentally
            passed here instead of to `modified_rs_hurst_full_record()`
            (confirmed ~27s vs ~0.6s on a 124s/8kHz recording). Use
            `tau_scale="geometric"` if a genuinely large sweep is intended.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(values) < 16:
        return HurstRSResult(
            None, None, (), None, False, ("input_too_short",),
            scope="segment", comparable_to_reference=False, tau_scale=tau_scale,
        )
    if not all(math.isfinite(value) for value in values):
        return HurstRSResult(
            None, None, (), None, False, ("non_finite_input",),
            scope="segment", comparable_to_reference=False, tau_scale=tau_scale,
        )

    if precomputed_envelope is not None:
        envelope = precomputed_envelope
    else:
        envelope = _compute_envelope(values, sample_rate, envelope_window_sec)

    input_length_sec = len(values) / sample_rate

    return _run_rs_analysis(
        envelope,
        min_tau=min_tau,
        max_tau=max_tau,
        upper_bound_divisor=2,
        tau_scale=tau_scale,
        n_geometric_scales=n_geometric_scales,
        use_piecewise_fit=use_piecewise_fit,
        envelope_window_sec=envelope_window_sec,
        r_squared_threshold=r_squared_threshold,
        scope="segment",
        comparable_to_reference=False,
        input_length_sec=input_length_sec,
    )


def modified_rs_hurst_full_record(
    values: list[float],
    sample_rate: int,
    *,
    envelope_window_sec: float = 0.1,
    min_tau: int = 3,
    max_tau: int | None = None,
    use_piecewise_fit: bool = True,
    n_geometric_scales: int = 16,
    r_squared_threshold: float = _DEFAULT_R_SQUARED_THRESHOLD,
) -> HurstRSResult:
    """Estimate H and T on the whole recording, per Kuzenkov/Loginov (2014).

    This is variant **A** of the methodology decision in
    `docs/rs-methodology-gap-2026-10-31.md`: one R/S series per file, built
    from the envelope of the *entire* signal (speech and pauses together —
    do not pass VAD-trimmed audio here), 100 ms envelope window, geometric
    tau scale from `min_tau` up to the series length `N` (not `N/2`).
    Results carry `scope="full_record"` and `comparable_to_reference=True`
    and may be compared with the paper's Table 1, subject to the same
    sample-rate/preprocessing caveats discussed in the methodology doc.

    Args:
        values: Full-file audio samples, pauses included.
        sample_rate: Sample rate in Hz.
        envelope_window_sec: RMS envelope window; 100 ms matches the paper.
        min_tau: Minimum tau (paper uses tau_1 = 3 envelope samples).
        max_tau: Maximum tau. `None` means "auto": the full envelope length
            `N` (not halved), matching the paper's scale ceiling.
        use_piecewise_fit: Piecewise-linear breakpoint fit for `T` (paper
            uses a piecewise-polynomial fit; the linear two-segment fit here
            is the project's existing approximation of it).
        n_geometric_scales: Number of tau points on the geometric scale.
        r_squared_threshold: Threshold below which `weak_log_log_fit` is
            warned.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(values) < 16:
        return HurstRSResult(
            None, None, (), None, False, ("input_too_short",),
            scope="full_record", comparable_to_reference=True, tau_scale="geometric",
        )
    if not all(math.isfinite(value) for value in values):
        return HurstRSResult(
            None, None, (), None, False, ("non_finite_input",),
            scope="full_record", comparable_to_reference=True, tau_scale="geometric",
        )

    envelope = _compute_envelope(values, sample_rate, envelope_window_sec)
    input_length_sec = len(values) / sample_rate

    return _run_rs_analysis(
        envelope,
        min_tau=min_tau,
        max_tau=max_tau,
        upper_bound_divisor=1,  # variant A: upper bound is N, not N/2
        tau_scale="geometric",
        n_geometric_scales=n_geometric_scales,
        use_piecewise_fit=use_piecewise_fit,
        envelope_window_sec=envelope_window_sec,
        r_squared_threshold=r_squared_threshold,
        scope="full_record",
        comparable_to_reference=True,
        input_length_sec=input_length_sec,
    )


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
