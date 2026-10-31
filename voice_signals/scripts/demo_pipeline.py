#!/usr/bin/env python3
"""Comprehensive pipeline demonstration for iteration 02.

This script demonstrates the complete workflow:
1. Generate synthetic corpus
2. Audit WAV files
3. Extract features
4. Run VAD and analyze with modified R/S
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals import (
    EnergyVad,
    modified_rs_hurst,
    modified_rs_hurst_full_record,
    load_config,
    config_hash
)


def main() -> None:
    print("=" * 60)
    print("Voice Signals Project - Iteration 02 Demo Pipeline")
    print("=" * 60)
    
    # Load configuration
    config = load_config(PROJECT_ROOT / "configs" / "default.yaml")
    cfg_hash = config_hash(config)
    print(f"\nConfig hash: {cfg_hash}")
    print(f"Version: {config.get('version', 'unknown')}")
    
    # Check test file
    test_wav = PROJECT_ROOT / "tests" / "test_data" / "Ru-Vegetables.wav"
    if not test_wav.exists():
        print(f"\nError: Test file not found: {test_wav}")
        print("Place a test WAV file at this location to continue.")
        return
    
    print(f"\n{'Step 1: VAD Analysis':-^60}")
    print(f"Processing: {test_wav.name}")
    
    vad = EnergyVad()
    segments = vad.process_file(test_wav)
    
    print(f"\nDetected {len(segments)} speech segments:")
    for i, seg in enumerate(segments[:5], 1):  # Show first 5
        print(f"  {i}. {seg.start_sec:.3f} - {seg.end_sec:.3f}s ({seg.end_sec - seg.start_sec:.3f}s)")
    if len(segments) > 5:
        print(f"  ... and {len(segments) - 5} more")
    
    print(f"\n{'Step 2: Nonlinear Dynamics Analysis (Modified R/S)':-^60}")
    print("Two protocols, per docs/rs-methodology-gap-2026-10-31.md (variant A + C):")

    # Load audio for dynamics analysis
    import wave
    with wave.open(str(test_wav), 'rb') as wf:
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    audio = [
        int.from_bytes(raw[i:i+2], 'little', signed=True) / 32768.0
        for i in range(0, len(raw), 2)
    ]

    # Fail fast on a missing/renamed config key rather than silently falling
    # back to a hardcoded default that could drift from configs/default.yaml.
    rs_cfg = config["dynamics"]["modified_rs"]

    # Variant A: whole-record series (pauses included), comparable to the paper.
    print("\n[A] Full-record (pauses included, comparable to Kuzenkov/Loginov 2014):")
    full_cfg = rs_cfg["full_record"]
    result_full = modified_rs_hurst_full_record(
        audio,
        sample_rate,
        envelope_window_sec=full_cfg["envelope_window_sec"],
        min_tau=full_cfg["min_tau"],
        max_tau=full_cfg["max_tau"],
        n_geometric_scales=full_cfg["n_geometric_scales"],
        r_squared_threshold=full_cfg["r_squared_threshold"],
        use_piecewise_fit=True,
    )
    if result_full.valid:
        print(f"  Hurst exponent H: {result_full.hurst_h:.3f}")
        print(f"  Characteristic time T: {result_full.characteristic_time_sec:.3f}s")
        print(f"  Fit R-squared: {result_full.fit_r_squared:.3f}")
        print(f"  Input length: {result_full.input_length_sec:.3f}s")
        if result_full.warnings:
            print(f"  Warnings: {', '.join(result_full.warnings)}")
    else:
        print(f"  Analysis failed: {', '.join(result_full.warnings)}")

    # Variant C: per-segment diagnostic feature, NOT comparable across segments
    # or to the paper (different N, different envelope window, no pauses).
    result = None
    if segments:
        seg = segments[0]
        start_sample = int(seg.start_sec * sample_rate)
        end_sample = int(seg.end_sec * sample_rate)
        segment_audio = audio[start_sample:end_sample]

        print(f"\n[C] Per-segment, segment 1 ({seg.start_sec:.3f}s - {seg.end_sec:.3f}s), "
              f"NOT comparable across segments or to the paper:")
        seg_cfg = rs_cfg["segment"]
        result = modified_rs_hurst(
            segment_audio,
            sample_rate,
            envelope_window_sec=seg_cfg["envelope_window_sec"],
            min_tau=seg_cfg["min_tau"],
            max_tau=seg_cfg["max_tau"],
            tau_scale=seg_cfg["tau_scale"],
            r_squared_threshold=seg_cfg["r_squared_threshold"],
            use_piecewise_fit=True,
        )

        if result.valid:
            print(f"  Hurst exponent H: {result.hurst_h:.3f}")
            print(f"  Characteristic time T: {result.characteristic_time_sec:.3f}s")
            print(f"  Fit R-squared: {result.fit_r_squared:.3f}")
            print(f"  Fit method: {result.fit_method}")
            print(f"  Tau range: {min(result.tau_values)} - {max(result.tau_values)}")
            
            if result.warnings:
                print(f"  Warnings: {', '.join(result.warnings)}")
            
            # Interpretation
            if result.hurst_h:
                if result.hurst_h > 0.6:
                    print(f"  > Persistent behavior (H > 0.5): long-range correlations detected")
                elif result.hurst_h < 0.4:
                    print(f"  > Anti-persistent behavior (H < 0.5): mean-reverting")
                else:
                    print(f"  > Brownian-like behavior (H ~= 0.5): random walk")
        else:
            print(f"  Analysis failed: {', '.join(result.warnings)}")
    
    print(f"\n{'Summary':-^60}")
    print(f"OK VAD: {len(segments)} speech segments detected")
    print(f"OK Modified R/S [A] full_record: valid={result_full.valid}, "
          f"fit_method={result_full.fit_method if result_full.valid else 'n/a'}")
    if result is not None:
        print(f"OK Modified R/S [C] segment: valid={result.valid}, "
              f"fit_method={result.fit_method if result.valid else 'n/a'}")
    print(f"OK Config: {cfg_hash}")
    
    print(f"\n{'Available Scripts':-^60}")
    print("  python scripts/generate_synthetic.py  - Generate synthetic corpus")
    print("  python scripts/run_audit.py <dir>    - Audit WAV files")
    print("  python scripts/extract_features.py <wav> - Extract frame features")
    print("  python scripts/run_vad.py <wav>      - Run VAD on single file")
    print("  python scripts/demo_pipeline.py      - This demo")
    
    print(f"\n{'Next Steps':-^60}")
    print("1. Generate synthetic data:")
    print("   python scripts/generate_synthetic.py --n-files 10")
    print("2. Run full audit:")
    print("   python scripts/run_audit.py data/synthetic/audio")
    print("3. Extract features:")
    print("   python scripts/extract_features.py data/synthetic/audio")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
