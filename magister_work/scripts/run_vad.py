#!/usr/bin/env python3
"""Прогон VAD на WAV-файле: сравнение energy и entropy-бэкендов.

Пример:
    python scripts/run_vad.py path/to/file.wav
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from speechdyn import EnergyVad, EntropyVad, read_wav_mono  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VAD backends on a WAV file")
    parser.add_argument("wav", type=Path)
    parser.add_argument("--backend", choices=["energy", "entropy", "both"], default="both")
    args = parser.parse_args()
    if not args.wav.is_file():
        parser.error(f"WAV file not found: {args.wav}")

    audio, sample_rate = read_wav_mono(args.wav)
    print(f"File: {args.wav}")
    print(f"Sample rate: {sample_rate} Hz, duration: {len(audio) / sample_rate:.2f} s")

    backends = []
    if args.backend in ("energy", "both"):
        backends.append(EnergyVad())
    if args.backend in ("entropy", "both"):
        backends.append(EntropyVad())

    for backend in backends:
        segments = backend.process_array(audio, sample_rate, file_id=args.wav.stem)
        total = sum(s.duration_sec for s in segments)
        print(f"\n[{backend.name}] speech segments: {len(segments)}, speech time: {total:.2f} s "
              f"({100 * total / (len(audio) / sample_rate):.1f}%)")
        for segment in segments:
            print(f"  {segment.start_sec:8.3f}  {segment.end_sec:8.3f}  {segment.label}")


if __name__ == "__main__":
    main()
