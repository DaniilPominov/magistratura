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
    
    # Load audio for dynamics analysis
    import wave
    with wave.open(str(test_wav), 'rb') as wf:
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    audio = [
        int.from_bytes(raw[i:i+2], 'little', signed=True) / 32768.0
        for i in range(0, len(raw), 2)
    ]
    
    # Analyze first speech segment if available
    if segments:
        seg = segments[0]
        start_sample = int(seg.start_sec * sample_rate)
        end_sample = int(seg.end_sec * sample_rate)
        segment_audio = audio[start_sample:end_sample]
        
        print(f"\nAnalyzing segment 1 ({seg.start_sec:.3f}s - {seg.end_sec:.3f}s)...")
        result = modified_rs_hurst(segment_audio, sample_rate, use_piecewise_fit=True)
        
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
    print(f"OK Modified R/S: H and T computed with {result.fit_method} method")
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
