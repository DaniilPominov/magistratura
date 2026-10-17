#!/usr/bin/env python3
"""Audit WAV files: extract metadata, energy statistics, and quality flags.

Generates CSV reports with per-file audit records and summary statistics.
"""

import argparse
import csv
import math
import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import List

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals.schemas import FileAuditRecord


def extract_subject_task(filename: str) -> tuple[str, str]:
    """Extract subject_id and task_type from filename using heuristics."""
    # Try pattern like: subj01_task_reading.wav or syn_001_snr20.wav
    match = re.search(r'(subj|syn)_?(\d+)', filename, re.IGNORECASE)
    if match:
        subject_id = f"{match.group(1)}_{match.group(2)}"
    else:
        subject_id = "UNKNOWN"
    
    if 'read' in filename.lower():
        task_type = "reading"
    elif 'mono' in filename.lower():
        task_type = "monolog"
    elif 'syn' in filename.lower():
        task_type = "synthetic"
    else:
        task_type = "UNKNOWN"
    
    return subject_id, task_type


def audit_wav_file(wav_path: Path) -> FileAuditRecord:
    """Perform full audit of a WAV file."""
    filename = wav_path.name
    file_id = wav_path.stem
    
    # Extract metadata from filename
    subject_id, task_type = extract_subject_task(filename)
    
    try:
        with wave.open(str(wav_path), 'rb') as wf:
            n_channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            sample_width = wf.getsampwidth()
            
            duration_sec = n_frames / sample_rate if sample_rate > 0 else 0.0
            
            # Read audio data
            raw_bytes = wf.readframes(n_frames)
            
            # Convert to samples (assume 16-bit PCM)
            if sample_width == 2:
                samples = []
                for i in range(0, len(raw_bytes), 2):
                    if i + 1 < len(raw_bytes):
                        sample = int.from_bytes(raw_bytes[i:i+2], byteorder='little', signed=True)
                        samples.append(sample / 32768.0)  # Normalize to [-1, 1]
            else:
                samples = []  # Unsupported format
            
            # Energy statistics
            if samples:
                abs_samples = [abs(s) for s in samples]
                peak_amplitude = max(abs_samples)
                rms = math.sqrt(mean(s * s for s in samples))
                
                # Crest factor: peak/RMS
                crest_factor = peak_amplitude / rms if rms > 1e-10 else 0.0
                
                # Silence detection: frames below -40 dB
                silence_threshold = 0.01  # -40 dB
                silence_frames = sum(1 for s in abs_samples if s < silence_threshold)
                silence_ratio = silence_frames / len(samples)
                
                # Clipping detection: samples at or near ±1.0
                clip_threshold = 0.99
                clipped_frames = sum(1 for s in abs_samples if s >= clip_threshold)
                clipping_ratio = clipped_frames / len(samples)
                
                # Noise floor estimate (5th percentile of energy)
                sorted_abs = sorted(abs_samples)
                noise_floor = sorted_abs[int(len(sorted_abs) * 0.05)] if sorted_abs else 0.0
                noise_floor_db = 20 * math.log10(noise_floor + 1e-10)
                
                # Quality flags
                quality_flags = []
                if clipping_ratio > 0.01:
                    quality_flags.append("clipping")
                if silence_ratio > 0.7:
                    quality_flags.append("mostly_silent")
                if rms < 0.005:  # Very low energy
                    quality_flags.append("low_energy")
                if n_channels != 1:
                    quality_flags.append("stereo_or_multi")
                if sample_width != 2:
                    quality_flags.append("non_16bit")
                if sample_rate not in [8000, 16000, 44100, 48000]:
                    quality_flags.append("unusual_sample_rate")
            else:
                peak_amplitude = 0.0
                rms = 0.0
                crest_factor = 0.0
                silence_ratio = 1.0
                clipping_ratio = 0.0
                noise_floor_db = -100.0
                quality_flags = ["read_error"]
            
            return FileAuditRecord(
                file_id=file_id,
                subject_id=subject_id,
                task_type=task_type,
                file_path=str(wav_path),
                sample_rate=sample_rate,
                n_channels=n_channels,
                duration_sec=duration_sec,
                sample_width_bytes=sample_width,
                peak_amplitude=peak_amplitude,
                rms_amplitude=rms,
                crest_factor=crest_factor,
                silence_ratio=silence_ratio,
                clipping_ratio=clipping_ratio,
                noise_floor_db=noise_floor_db,
                quality_flags=tuple(quality_flags),
                notes=f"subject/task inferred from filename" if subject_id != "UNKNOWN" else None
            )
    
    except Exception as e:
        # Return error record
        return FileAuditRecord(
            file_id=file_id,
            subject_id="UNKNOWN",
            task_type="UNKNOWN",
            file_path=str(wav_path),
            sample_rate=0,
            n_channels=0,
            duration_sec=0.0,
            sample_width_bytes=0,
            peak_amplitude=0.0,
            rms_amplitude=0.0,
            crest_factor=0.0,
            silence_ratio=0.0,
            clipping_ratio=0.0,
            noise_floor_db=-100.0,
            quality_flags=("error",),
            notes=f"Error: {str(e)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit WAV files and generate reports"
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing WAV files to audit"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search for WAV files"
    )
    
    args = parser.parse_args()
    
    if not args.input_dir.exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        return
    
    # Find WAV files
    if args.recursive:
        wav_files = list(args.input_dir.rglob("*.wav"))
    else:
        wav_files = list(args.input_dir.glob("*.wav"))
    
    if not wav_files:
        print(f"No WAV files found in {args.input_dir}")
        return
    
    print(f"Found {len(wav_files)} WAV files")
    
    # Audit all files
    records: List[FileAuditRecord] = []
    for i, wav_path in enumerate(wav_files, 1):
        print(f"  [{i}/{len(wav_files)}] {wav_path.name}", end="")
        record = audit_wav_file(wav_path)
        records.append(record)
        
        if record.quality_flags:
            print(f" → {', '.join(record.quality_flags)}")
        else:
            print(" → OK")
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write detailed CSV
    csv_path = args.output_dir / "wav_audit.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'file_id', 'subject_id', 'task_type', 'file_path',
            'sample_rate', 'n_channels', 'duration_sec', 'sample_width_bytes',
            'peak_amplitude', 'rms_amplitude', 'crest_factor',
            'silence_ratio', 'clipping_ratio', 'noise_floor_db',
            'quality_flags', 'notes'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for record in records:
            row = asdict(record)
            row['quality_flags'] = '; '.join(record.quality_flags) if record.quality_flags else ''
            writer.writerow(row)
    
    # Generate summary statistics
    valid_records = [r for r in records if 'error' not in r.quality_flags]
    
    summary_lines = [
        "# WAV Audit Summary\n",
        f"Total files: {len(records)}",
        f"Valid files: {len(valid_records)}",
        f"Errors: {len(records) - len(valid_records)}\n",
    ]
    
    if valid_records:
        sample_rates = [r.sample_rate for r in valid_records]
        durations = [r.duration_sec for r in valid_records]
        
        summary_lines.extend([
            "## Sample Rates",
            f"  Unique: {sorted(set(sample_rates))}",
            f"  Most common: {max(set(sample_rates), key=sample_rates.count)} Hz\n",
            
            "## Durations",
            f"  Total: {sum(durations):.1f} sec",
            f"  Mean: {mean(durations):.1f} sec",
            f"  Range: {min(durations):.1f} - {max(durations):.1f} sec\n",
            
            "## Channels",
            f"  Mono: {sum(1 for r in valid_records if r.n_channels == 1)}",
            f"  Stereo: {sum(1 for r in valid_records if r.n_channels == 2)}\n",
        ])
        
        # Quality issues
        all_flags = [flag for r in valid_records for flag in r.quality_flags]
        if all_flags:
            from collections import Counter
            flag_counts = Counter(all_flags)
            summary_lines.append("## Quality Flags")
            for flag, count in flag_counts.most_common():
                summary_lines.append(f"  {flag}: {count}")
    
    summary_path = args.output_dir / "wav_audit_summary.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    
    # Write issues CSV
    issues = [r for r in records if r.quality_flags]
    if issues:
        issues_path = args.output_dir / "wav_audit_issues.csv"
        with open(issues_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['file_id', 'quality_flags', 'notes'])
            writer.writeheader()
            for record in issues:
                writer.writerow({
                    'file_id': record.file_id,
                    'quality_flags': '; '.join(record.quality_flags),
                    'notes': record.notes or ''
                })
        print(f"\n✓ Issues: {issues_path}")
    
    print(f"\n✓ Audit complete: {len(records)} files")
    print(f"✓ Detailed report: {csv_path}")
    print(f"✓ Summary: {summary_path}")


if __name__ == "__main__":
    main()
