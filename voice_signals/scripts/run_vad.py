#!/usr/bin/env python3
"""Run the local energy VAD on a WAV file.

Modified for testing only; the associated TASK-06 has not been implemented.
"""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voice_signals.vad import EnergyVad


def main() -> None:
    parser = argparse.ArgumentParser(description="Run energy VAD on a WAV file")
    parser.add_argument(
        "wav", nargs="?", type=Path,
        default=PROJECT_ROOT / "tests" / "test_data" / (
            "12_Arrival In_aid_edit_seder_veronika_melnikova.wav"
        ),
    )
    args = parser.parse_args()
    if not args.wav.is_file():
        parser.error(f"WAV file not found: {args.wav}")

    segments = EnergyVad().process_file(args.wav)
    print(f"File: {args.wav}")
    print(f"Speech segments: {len(segments)}")
    for segment in segments:
        print(f"{segment.start_sec:.3f}\t{segment.end_sec:.3f}\t{segment.label}")

if __name__ == "__main__":
    main()
