#!/usr/bin/env python3
"""Run VAD then the modified R/S analysis (Hurst H and characteristic time T)
on the detected speech segments of a WAV file.

Step 4 of HOW-TO-RUN.md.
"""

import argparse
import wave
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals import EnergyVad, modified_rs_hurst, load_config


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


def analyze(segment_audio: list[float], sample_rate: int, *, use_piecewise_fit: bool,
            envelope_window_sec: float, min_tau: int, max_tau: int | None) -> None:
    result = modified_rs_hurst(
        segment_audio,
        sample_rate,
        envelope_window_sec=envelope_window_sec,
        min_tau=min_tau,
        max_tau=max_tau,
        use_piecewise_fit=use_piecewise_fit,
    )
    if not result.valid:
        print(f"  Analysis failed: {', '.join(result.warnings)}")
        return
    print(f"  Hurst exponent H: {result.hurst_h:.3f}")
    print(f"  Characteristic time T: {result.characteristic_time_sec:.3f}s")
    print(f"  Fit R-squared: {result.fit_r_squared:.3f}")
    print(f"  Fit method: {result.fit_method}")
    print(f"  Tau range: {min(result.tau_values)} - {max(result.tau_values)}")
    if result.warnings:
        print(f"  Warnings: {', '.join(result.warnings)}")
    print(f"  > {interpret(result.hurst_h)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run VAD and modified R/S analysis on a WAV file")
    parser.add_argument(
        "wav", nargs="?", type=Path,
        default=PROJECT_ROOT / "tests" / "test_data" / "Ru-Vegetables.wav",
    )
    parser.add_argument(
        "--segment", type=int, default=0,
        help="speech segment index to analyze (default: 0)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="analyze every detected speech segment",
    )
    parser.add_argument(
        "--no-piecewise", action="store_true",
        help="use the legacy argmax fit for the characteristic time T",
    )
    parser.add_argument(
        "--config", type=Path,
        default=PROJECT_ROOT / "configs" / "default.yaml",
    )
    args = parser.parse_args()

    if not args.wav.is_file():
        parser.error(f"WAV file not found: {args.wav}")

    dynamics = load_config(args.config)["dynamics"]["modified_rs"]
    envelope_window_sec = dynamics["envelope_window_sec"]
    min_tau = dynamics["min_tau"]
    max_tau = dynamics["max_tau"]
    use_piecewise_fit = not args.no_piecewise

    audio, sample_rate = load_audio(args.wav)
    segments = EnergyVad().process_file(args.wav)

    print(f"File: {args.wav}")
    print(f"Speech segments: {len(segments)}")
    if not segments:
        return

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
        print(f"\nSegment {i} ({seg.start_sec:.3f}s - {seg.end_sec:.3f}s):")
        analyze(
            audio[start:end],
            sample_rate,
            use_piecewise_fit=use_piecewise_fit,
            envelope_window_sec=envelope_window_sec,
            min_tau=min_tau,
            max_tau=max_tau,
        )


if __name__ == "__main__":
    main()
