#!/usr/bin/env python3
"""Extract frame-level acoustic features from WAV files.

Features: RMS energy, ZCR, spectral flatness, basic spectral statistics.
Note: This is a minimal implementation without MFCC/Mel dependencies.
"""

import argparse
import csv
import math
import wave
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import List

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals.config import config_hash, load_config
from voice_signals.framing import TimeGrid, compute_rms_frames
from voice_signals.schemas import FrameFeatureRecord


def compute_zcr(samples: List[float]) -> float:
    """Compute zero-crossing rate for a frame."""
    if len(samples) < 2:
        return 0.0
    crossings = sum(
        1 for i in range(1, len(samples))
        if samples[i] * samples[i-1] < 0
    )
    return crossings / len(samples)


def compute_spectral_flatness(samples: List[float]) -> float:
    """Compute spectral flatness (geometric mean / arithmetic mean of power spectrum).
    
    This is a simplified approximation without FFT.
    Returns a proxy based on sample variance.
    """
    if len(samples) < 2:
        return 0.0
    
    # Proxy: ratio of std to max absolute value
    abs_samples = [abs(s) for s in samples]
    max_val = max(abs_samples) if abs_samples else 0.0
    if max_val < 1e-10:
        return 0.0
    
    variance = sum((s - mean(samples)) ** 2 for s in samples) / len(samples)
    std = math.sqrt(variance)
    
    return min(1.0, std / (max_val + 1e-10))


def extract_frame_features(
    audio: List[float],
    sample_rate: int,
    frame_samples: int,
    hop_samples: int
) -> List[dict]:
    """Extract features for each frame."""
    features = []
    
    grid = TimeGrid(sample_rate, frame_samples, hop_samples)
    times, rms_values = compute_rms_frames(audio, grid)
    
    for i, time_sec in enumerate(times):
        start_idx = i * hop_samples
        end_idx = start_idx + frame_samples
        frame = audio[start_idx:end_idx]
        
        if len(frame) < frame_samples:
            frame.extend([0.0] * (frame_samples - len(frame)))
        
        rms = rms_values[i]
        energy_db = 10 * math.log10(rms * rms + 1e-12)
        
        zcr = compute_zcr(frame)
        spectral_flatness = compute_spectral_flatness(frame)
        
        features.append({
            'time_sec': time_sec,
            'rms': rms,
            'energy_db': energy_db,
            'zcr': zcr,
            'spectral_flatness': spectral_flatness
        })
    
    return features


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract frame-level acoustic features"
    )
    parser.add_argument(
        "input_wav",
        type=Path,
        help="Input WAV file or directory"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "features",
        help="Output directory for features"
    )
    parser.add_argument(
        "--frame-ms",
        type=float,
        default=25.0,
        help="Frame size in milliseconds"
    )
    parser.add_argument(
        "--hop-ms",
        type=float,
        default=10.0,
        help="Hop size in milliseconds"
    )
    
    args = parser.parse_args()
    
    # Find WAV files
    if args.input_wav.is_file():
        wav_files = [args.input_wav]
    elif args.input_wav.is_dir():
        wav_files = list(args.input_wav.glob("*.wav"))
    else:
        print(f"Error: {args.input_wav} not found")
        return
    
    if not wav_files:
        print(f"No WAV files found")
        return
    
    # Load config
    config = load_config(PROJECT_ROOT / "configs" / "default.yaml")
    cfg_hash = config_hash(config)
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {len(wav_files)} files...")
    print(f"Frame: {args.frame_ms}ms, Hop: {args.hop_ms}ms")
    print(f"Config hash: {cfg_hash}")
    
    for wav_path in wav_files:
        file_id = wav_path.stem
        print(f"  {file_id}...", end="")
        
        try:
            # Read WAV
            with wave.open(str(wav_path), 'rb') as wf:
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                
                if n_channels != 1 or sample_width != 2:
                    print(f" SKIP (only mono 16-bit supported)")
                    continue
                
                raw_bytes = wf.readframes(n_frames)
                audio = []
                for i in range(0, len(raw_bytes), 2):
                    if i + 1 < len(raw_bytes):
                        sample = int.from_bytes(raw_bytes[i:i+2], byteorder='little', signed=True)
                        audio.append(sample / 32768.0)
            
            # Extract features
            frame_samples = int(args.frame_ms * sample_rate / 1000)
            hop_samples = int(args.hop_ms * sample_rate / 1000)
            
            features = extract_frame_features(audio, sample_rate, frame_samples, hop_samples)
            
            # Save to CSV
            output_path = args.output_dir / f"{file_id}_features.csv"
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if features:
                    writer = csv.DictWriter(f, fieldnames=features[0].keys())
                    writer.writeheader()
                    writer.writerows(features)
            
            print(f" {len(features)} frames → {output_path.name}")
        
        except Exception as e:
            print(f" ERROR: {e}")
    
    print(f"\n✓ Features saved to {args.output_dir}")


if __name__ == "__main__":
    main()
