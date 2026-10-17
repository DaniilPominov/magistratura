#!/usr/bin/env python3
"""Generate synthetic audio corpus with ground-truth labels for VAD testing.

This script creates speech-like events, pauses, hesitations, and artifacts
with known parameters for validation of VAD and nonlinear dynamics features.
"""

import argparse
import csv
import json
import math
import random
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals.config import config_hash, load_config
from voice_signals.schemas import SegmentRecord


@dataclass
class SyntheticEvent:
    """Ground truth for one synthetic event."""
    file_id: str
    start_sec: float
    end_sec: float
    label: str
    event_type: str
    params: dict
    true_h: float | None = None
    true_entropy: float | None = None
    noise_level_db: float | None = None


def generate_tone_burst(
    duration_sec: float,
    sample_rate: int,
    freq_hz: float = 220.0,
    amplitude: float = 0.3,
    modulation_hz: float = 5.0
) -> List[float]:
    """Generate a harmonic burst with amplitude modulation (speech-like)."""
    n_samples = int(duration_sec * sample_rate)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        # Carrier + amplitude modulation
        carrier = amplitude * math.sin(2 * math.pi * freq_hz * t)
        modulation = 0.5 + 0.5 * math.sin(2 * math.pi * modulation_hz * t)
        samples.append(carrier * modulation)
    return samples


def generate_silence(duration_sec: float, sample_rate: int) -> List[float]:
    """Generate silence (low-level noise)."""
    n_samples = int(duration_sec * sample_rate)
    return [random.gauss(0, 0.001) for _ in range(n_samples)]


def generate_hesitation(duration_sec: float, sample_rate: int) -> List[float]:
    """Generate hesitation-like sound (low frequency, irregular)."""
    n_samples = int(duration_sec * sample_rate)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        # Low frequency components with phase noise
        phase_noise = random.gauss(0, 0.1)
        sample = 0.1 * math.sin(2 * math.pi * 80 * t + phase_noise)
        samples.append(sample)
    return samples


def generate_artifact(duration_sec: float, sample_rate: int) -> List[float]:
    """Generate transient artifact (click, breath-like)."""
    n_samples = int(duration_sec * sample_rate)
    samples = []
    for i in range(n_samples):
        # Exponentially decaying burst
        decay = math.exp(-10 * i / n_samples)
        noise = random.gauss(0, 0.2)
        samples.append(decay * noise)
    return samples


def add_noise(samples: List[float], snr_db: float) -> List[float]:
    """Add white noise to achieve target SNR."""
    if snr_db >= 100:  # Effectively no noise
        return samples
    
    signal_power = sum(s * s for s in samples) / len(samples)
    signal_rms = math.sqrt(signal_power)
    
    noise_rms = signal_rms / (10 ** (snr_db / 20))
    
    noisy = [s + random.gauss(0, noise_rms) for s in samples]
    return noisy


def generate_synthetic_file(
    file_id: str,
    output_dir: Path,
    sample_rate: int = 16000,
    snr_db: float = 20.0,
    seed: int | None = None
) -> tuple[Path, List[SyntheticEvent]]:
    """Generate one synthetic WAV file with mixed events."""
    if seed is not None:
        random.seed(seed)
    
    events: List[SyntheticEvent] = []
    audio_segments: List[List[float]] = []
    current_time = 0.0
    
    # Define a sequence of events
    event_sequence = [
        ("silence", 0.5),
        ("speech", 1.0),
        ("silent_pause", 0.3),
        ("speech", 0.8),
        ("hesitation", 0.2),
        ("speech", 1.2),
        ("artifact", 0.15),
        ("silent_pause", 0.4),
        ("speech", 1.5),
        ("silence", 0.5),
    ]
    
    for event_type, duration in event_sequence:
        start_sec = current_time
        end_sec = current_time + duration
        
        if event_type == "speech":
            # Vary frequency for different speech events
            freq = random.uniform(180, 280)
            segment = generate_tone_burst(duration, sample_rate, freq_hz=freq)
            label = "speech"
            true_h = 0.65  # Persistent (speech-like)
        elif event_type == "silent_pause":
            segment = generate_silence(duration, sample_rate)
            label = "non_speech"
            true_h = 0.5  # Brownian
        elif event_type == "hesitation":
            segment = generate_hesitation(duration, sample_rate)
            label = "hesitation"
            true_h = 0.55
        elif event_type == "artifact":
            segment = generate_artifact(duration, sample_rate)
            label = "artifact"
            true_h = None  # Not applicable
        else:  # silence
            segment = generate_silence(duration, sample_rate)
            label = "non_speech"
            true_h = 0.5
        
        audio_segments.append(segment)
        
        events.append(SyntheticEvent(
            file_id=file_id,
            start_sec=start_sec,
            end_sec=end_sec,
            label=label,
            event_type=event_type,
            params={"duration": duration, "snr_db": snr_db},
            true_h=true_h,
            noise_level_db=snr_db
        ))
        
        current_time = end_sec
    
    # Concatenate all segments
    full_audio = []
    for segment in audio_segments:
        full_audio.extend(segment)
    
    # Add noise
    full_audio = add_noise(full_audio, snr_db)
    
    # Normalize to int16 range
    max_val = max(abs(s) for s in full_audio)
    if max_val > 0:
        scale = 0.8 / max_val  # Leave headroom
        full_audio = [int(s * scale * 32767) for s in full_audio]
    else:
        full_audio = [0] * len(full_audio)
    
    # Write WAV
    wav_path = output_dir / f"{file_id}.wav"
    with wave.open(str(wav_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(bytes([b for sample in full_audio for b in [sample & 0xFF, (sample >> 8) & 0xFF]]))
    
    return wav_path, events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic audio corpus with ground truth"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "synthetic",
        help="Output directory for synthetic data"
    )
    parser.add_argument(
        "--n-files",
        type=int,
        default=10,
        help="Number of synthetic files to generate"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Sample rate in Hz"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    
    args = parser.parse_args()
    
    # Create output directories
    audio_dir = args.output_dir / "audio"
    labels_dir = args.output_dir / "labels"
    audio_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    # Load config for hash
    config = load_config(PROJECT_ROOT / "configs" / "default.yaml")
    cfg_hash = config_hash(config)
    
    all_events: List[SyntheticEvent] = []
    manifest_rows = []
    
    print(f"Generating {args.n_files} synthetic files...")
    print(f"Config hash: {cfg_hash}")
    
    for i in range(args.n_files):
        # Vary SNR across files
        snr_db = [5, 10, 20, 30][i % 4]
        file_id = f"syn_{i:03d}_snr{snr_db}"
        
        wav_path, events = generate_synthetic_file(
            file_id=file_id,
            output_dir=audio_dir,
            sample_rate=args.sample_rate,
            snr_db=snr_db,
            seed=args.seed + i
        )
        
        all_events.extend(events)
        
        # Write per-file labels
        label_path = labels_dir / f"{file_id}.csv"
        with open(label_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'file_id', 'start_sec', 'end_sec', 'label', 'event_type',
                'true_h', 'noise_level_db'
            ])
            writer.writeheader()
            for event in events:
                writer.writerow({
                    'file_id': event.file_id,
                    'start_sec': f"{event.start_sec:.3f}",
                    'end_sec': f"{event.end_sec:.3f}",
                    'label': event.label,
                    'event_type': event.event_type,
                    'true_h': event.true_h if event.true_h is not None else '',
                    'noise_level_db': event.noise_level_db
                })
        
        manifest_rows.append({
            'file_id': file_id,
            'wav_path': str(wav_path.relative_to(args.output_dir)),
            'label_path': str(label_path.relative_to(args.output_dir)),
            'snr_db': snr_db,
            'duration_sec': events[-1].end_sec,
            'n_events': len([e for e in events if e.label == "speech"])
        })
        
        print(f"  {file_id}: {len(events)} events, {events[-1].end_sec:.1f}s")
    
    # Write manifest
    manifest_path = args.output_dir / "manifest.csv"
    with open(manifest_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'file_id', 'wav_path', 'label_path', 'snr_db', 'duration_sec', 'n_events'
        ])
        writer.writeheader()
        writer.writerows(manifest_rows)
    
    # Write metadata
    metadata = {
        'version': '0.2.0',
        'config_hash': cfg_hash,
        'sample_rate': args.sample_rate,
        'n_files': args.n_files,
        'seed': args.seed,
        'total_events': len(all_events),
        'taxonomy': ['speech', 'non_speech', 'hesitation', 'artifact']
    }
    
    metadata_path = args.output_dir / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Generated {args.n_files} files with {len(all_events)} events")
    print(f"✓ Manifest: {manifest_path}")
    print(f"✓ Metadata: {metadata_path}")
    print(f"✓ Audio: {audio_dir}")
    print(f"✓ Labels: {labels_dir}")


if __name__ == "__main__":
    main()
