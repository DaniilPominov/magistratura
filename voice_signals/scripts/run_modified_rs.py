#!/usr/bin/env python3
"""Run VAD then the modified R/S analysis (Hurst H and characteristic time T).

Supports both methodology-gap protocols decided in
docs/rs-methodology-gap-2026-10-31.md (variant A + C):

- ``segment`` (variant C, default): per speech-segment analysis on
  VAD-trimmed audio. Diagnostic feature; NOT comparable across segments of
  different length and NOT comparable to Kuzenkov/Loginov (2014).
- ``full_record`` (variant A): one R/S series on the whole file, pauses
  included, 100 ms envelope window, geometric tau scale up to N. Comparable
  to the paper's Table 1.
- ``both``: run both and print both, clearly labeled.

Step 4 of HOW-TO-RUN.md.
"""

import argparse
import csv
import wave
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals import (
    EnergyVad,
    modified_rs_hurst,
    modified_rs_hurst_full_record,
    load_config,
)
from voice_signals.dynamics import HurstRSResult

CSV_FIELDS = [
    "scope",
    "segment_index",
    "segment_start_sec",
    "segment_end_sec",
    "valid",
    "comparable_to_reference",
    "hurst_h",
    "characteristic_time_sec",
    "fit_r_squared",
    "fit_method",
    "tau_scale",
    "tau_min",
    "tau_max",
    "input_length_sec",
    "interpretation",
    "warnings",
]


def load_audio(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise ValueError("only mono 16-bit PCM WAV is supported")
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    audio = [
        int.from_bytes(raw[i:i + 2], "little", signed=True) / 32768.0
        for i in range(0, len(raw), 2)
    ]
    return audio, sample_rate


def interpret(hurst_h: float) -> str:
    if hurst_h > 0.6:
        return "Persistent (H > 0.5): long-range correlations detected"
    if hurst_h < 0.4:
        return "Anti-persistent (H < 0.5): mean-reverting"
    return "Brownian-like (H ~= 0.5): random walk"


def print_result(result: HurstRSResult) -> None:
    if not result.valid:
        print(f"  Analysis failed: {', '.join(result.warnings)}")
        return
    print(f"  Scope: {result.scope} (comparable to Kuzenkov/Loginov 2014: "
          f"{result.comparable_to_reference})")
    print(f"  Hurst exponent H: {result.hurst_h:.3f}")
    print(f"  Characteristic time T: {result.characteristic_time_sec:.3f}s")
    print(f"  Fit R-squared: {result.fit_r_squared:.3f}")
    print(f"  Fit method: {result.fit_method}")
    print(f"  Tau scale: {result.tau_scale}")
    print(f"  Tau range: {min(result.tau_values)} - {max(result.tau_values)}")
    print(f"  Input length: {result.input_length_sec:.3f}s")
    if result.warnings:
        print(f"  Warnings: {', '.join(result.warnings)}")
    print(f"  > {interpret(result.hurst_h)}")


def result_to_row(
    result: HurstRSResult,
    *,
    segment_index: int | None = None,
    segment_start_sec: float | None = None,
    segment_end_sec: float | None = None,
) -> dict:
    row = {field: "" for field in CSV_FIELDS}
    row["scope"] = result.scope
    row["segment_index"] = "" if segment_index is None else segment_index
    row["segment_start_sec"] = "" if segment_start_sec is None else f"{segment_start_sec:.3f}"
    row["segment_end_sec"] = "" if segment_end_sec is None else f"{segment_end_sec:.3f}"
    row["valid"] = result.valid
    row["comparable_to_reference"] = result.comparable_to_reference
    row["tau_scale"] = result.tau_scale
    row["input_length_sec"] = (
        "" if result.input_length_sec is None else f"{result.input_length_sec:.3f}"
    )
    row["warnings"] = ";".join(result.warnings)
    if result.valid:
        row["hurst_h"] = f"{result.hurst_h:.6f}"
        row["characteristic_time_sec"] = f"{result.characteristic_time_sec:.6f}"
        row["fit_r_squared"] = (
            "" if result.fit_r_squared is None else f"{result.fit_r_squared:.6f}"
        )
        row["fit_method"] = result.fit_method
        row["tau_min"] = min(result.tau_values)
        row["tau_max"] = max(result.tau_values)
        row["interpretation"] = interpret(result.hurst_h)
    return row


def analyze_segment(segment_audio: list[float], sample_rate: int, *, cfg: dict) -> HurstRSResult:
    return modified_rs_hurst(
        segment_audio,
        sample_rate,
        envelope_window_sec=cfg["envelope_window_sec"],
        min_tau=cfg["min_tau"],
        max_tau=cfg["max_tau"],
        tau_scale=cfg.get("tau_scale", "arithmetic"),
        r_squared_threshold=cfg.get("r_squared_threshold", 0.7),
        use_piecewise_fit=cfg.get("use_piecewise_fit", True),
    )


def analyze_full_record(audio: list[float], sample_rate: int, *, cfg: dict) -> HurstRSResult:
    return modified_rs_hurst_full_record(
        audio,
        sample_rate,
        envelope_window_sec=cfg["envelope_window_sec"],
        min_tau=cfg["min_tau"],
        max_tau=cfg["max_tau"],
        n_geometric_scales=cfg.get("n_geometric_scales", 16),
        r_squared_threshold=cfg.get("r_squared_threshold", 0.7),
        use_piecewise_fit=cfg.get("use_piecewise_fit", True),
    )


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run VAD and modified R/S analysis on a WAV file")
    parser.add_argument(
        "wav", nargs="?", type=Path,
        default=PROJECT_ROOT / "tests" / "test_data" / "Ru-Vegetables.wav",
    )
    parser.add_argument(
        "--scope", choices=["segment", "full_record", "both"], default="segment",
        help="which methodology-gap protocol to run (default: segment, variant C)",
    )
    parser.add_argument(
        "--segment", type=int, default=0,
        help="speech segment index to analyze when --scope=segment (default: 0)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="analyze every detected speech segment (--scope=segment only)",
    )
    parser.add_argument(
        "--no-piecewise", action="store_true",
        help="use the legacy argmax fit for the characteristic time T",
    )
    parser.add_argument(
        "--config", type=Path,
        default=PROJECT_ROOT / "configs" / "default.yaml",
    )
    parser.add_argument(
        "--csv", type=Path, default=None,
        help="write all results (one row per run) to this CSV file for easy "
             "tabular viewing, instead of/in addition to the console output",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="suppress the per-result console output (useful with --csv)",
    )
    args = parser.parse_args()

    if not args.wav.is_file():
        parser.error(f"WAV file not found: {args.wav}")

    dynamics_cfg = load_config(args.config)["dynamics"]["modified_rs"]
    use_piecewise_fit = not args.no_piecewise
    segment_cfg = {**dynamics_cfg["segment"], "use_piecewise_fit": use_piecewise_fit}
    full_record_cfg = {**dynamics_cfg["full_record"], "use_piecewise_fit": use_piecewise_fit}

    audio, sample_rate = load_audio(args.wav)
    segments = EnergyVad().process_file(args.wav)

    if not args.quiet:
        print(f"File: {args.wav}")
        print(f"Speech segments: {len(segments)}")

    rows: list[dict] = []

    if args.scope in ("full_record", "both"):
        if not args.quiet:
            print("\nFull-record analysis (variant A, pauses included):")
        result_full = analyze_full_record(audio, sample_rate, cfg=full_record_cfg)
        if not args.quiet:
            print_result(result_full)
        rows.append(result_to_row(result_full))

    if args.scope in ("segment", "both"):
        if not segments:
            if not args.quiet:
                print("\nNo speech segments detected; skipping segment analysis.")
        else:
            if args.all:
                indices = range(len(segments))
            else:
                if not 0 <= args.segment < len(segments):
                    parser.error(
                        f"segment {args.segment} out of range (0..{len(segments) - 1})")
                indices = [args.segment]

            for i in indices:
                seg = segments[i]
                start = int(seg.start_sec * sample_rate)
                end = int(seg.end_sec * sample_rate)
                if not args.quiet:
                    print(f"\nSegment {i} ({seg.start_sec:.3f}s - {seg.end_sec:.3f}s, "
                          f"variant C, not comparable across segments):")
                result_seg = analyze_segment(audio[start:end], sample_rate, cfg=segment_cfg)
                if not args.quiet:
                    print_result(result_seg)
                rows.append(result_to_row(
                    result_seg,
                    segment_index=i,
                    segment_start_sec=seg.start_sec,
                    segment_end_sec=seg.end_sec,
                ))

    if args.csv is not None:
        write_csv(rows, args.csv)
        print(f"\nWrote {len(rows)} row(s) to {args.csv}")


if __name__ == "__main__":
    main()
