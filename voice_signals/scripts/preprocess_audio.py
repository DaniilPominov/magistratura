#!/usr/bin/env python3
"""Preprocess arbitrary audio files into the project's target WAV format.

The rest of the pipeline (EnergyVad, modified_rs_hurst, run_audit.py, ...)
only accepts mono 16-bit PCM WAV. Real-world samples show up as WAV at
arbitrary sample rates/bit depths/channel counts, or as MP3 at arbitrary
bitrates, or as other container/codec combinations ffmpeg understands.
This script normalizes any of those into mono 16-bit PCM WAV at a fixed
sample rate using ffmpeg (external process, no extra Python audio deps).

Usage:
    python scripts/preprocess_audio.py input.mp3 -o data/real_samples/
    python scripts/preprocess_audio.py path/to/raw_dir/ -o data/real_samples/ --recursive
    python scripts/preprocess_audio.py input.wav -o out/ --rate 8000
    python scripts/preprocess_audio.py path/to/raw_dir/ -o out/ --dry-run

Requires ffmpeg (and ffprobe) on PATH. Install: https://ffmpeg.org/download.html
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Extensions ffmpeg is asked to try. Not exhaustive; ffmpeg will simply fail
# on anything it doesn't understand, and that failure is reported per file.
SUPPORTED_INPUT_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma",
    ".aiff", ".aif", ".webm", ".mp4",
}

TARGET_SAMPLE_RATE_DEFAULT = 16_000  # matches configs/default.yaml ASSUMPTION


@dataclass
class ConversionResult:
    source: Path
    dest: Path | None
    ok: bool
    message: str
    source_sample_rate: int | None = None
    source_channels: int | None = None
    source_codec: str | None = None


def check_ffmpeg_available() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise SystemExit(
                f"'{tool}' not found on PATH. Install ffmpeg "
                "(https://ffmpeg.org/download.html) and ensure it is on "
                "PATH, then retry."
            )


def probe_audio(path: Path) -> tuple[int | None, int | None, str | None]:
    """Return (sample_rate, channels, codec_name) for the first audio stream."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=sample_rate,channels,codec_name",
                "-of", "json",
                str(path),
            ],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(proc.stdout or "{}")
        streams = data.get("streams") or []
        if not streams:
            return None, None, None
        stream = streams[0]
        sample_rate = int(stream["sample_rate"]) if "sample_rate" in stream else None
        channels = int(stream["channels"]) if "channels" in stream else None
        codec = stream.get("codec_name")
        return sample_rate, channels, codec
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError):
        return None, None, None


def convert_one(
    source: Path,
    dest: Path,
    *,
    sample_rate: int,
    overwrite: bool,
    dry_run: bool,
) -> ConversionResult:
    src_rate, src_channels, src_codec = probe_audio(source)

    if dest.exists() and not overwrite:
        return ConversionResult(
            source, dest, False,
            "destination exists (use --overwrite to replace)",
            src_rate, src_channels, src_codec,
        )

    if dry_run:
        return ConversionResult(
            source, dest, True, "dry-run: would convert",
            src_rate, src_channels, src_codec,
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y" if overwrite else "-n",
        "-i", str(source),
        "-ac", "1",              # mono
        "-ar", str(sample_rate),  # target sample rate
        "-sample_fmt", "s16",    # 16-bit PCM
        "-c:a", "pcm_s16le",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Keep the message short; ffmpeg stderr can be very verbose.
        tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        return ConversionResult(
            source, dest, False, f"ffmpeg failed: {tail}",
            src_rate, src_channels, src_codec,
        )
    return ConversionResult(
        source, dest, True, "converted",
        src_rate, src_channels, src_codec,
    )


def discover_inputs(input_path: Path, *, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    pattern_fn = input_path.rglob if recursive else input_path.glob
    files = [
        p for p in pattern_fn("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
    ]
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert audio files (any ffmpeg-readable format) to "
                    "mono 16-bit PCM WAV at a fixed sample rate, as required "
                    "by the rest of the voice_signals pipeline.",
    )
    parser.add_argument(
        "input", type=Path,
        help="a single audio file, or a directory to scan for audio files",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, required=True,
        help="directory to write the converted mono 16-bit WAV files into",
    )
    parser.add_argument(
        "--rate", type=int, default=TARGET_SAMPLE_RATE_DEFAULT,
        help=f"target sample rate in Hz (default: {TARGET_SAMPLE_RATE_DEFAULT}, "
             "matching the ASSUMPTION in configs/default.yaml)",
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="when input is a directory, scan it recursively",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="overwrite existing output files instead of skipping them",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="list what would be converted without writing any files",
    )
    args = parser.parse_args()

    check_ffmpeg_available()

    if not args.input.exists():
        parser.error(f"input not found: {args.input}")

    sources = discover_inputs(args.input, recursive=args.recursive)
    if not sources:
        print(f"No audio files found under {args.input} "
              f"(looked for: {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))})")
        return

    print(f"Found {len(sources)} file(s) to process.")
    if args.dry_run:
        print("(dry run: no files will be written)")

    results: list[ConversionResult] = []
    for i, source in enumerate(sources, 1):
        dest = args.output_dir / f"{source.stem}.wav"
        print(f"  [{i}/{len(sources)}] {source.name} -> {dest.name}", end="")
        result = convert_one(
            source, dest,
            sample_rate=args.rate,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        results.append(result)
        tag = "OK" if result.ok else "SKIP/FAIL"
        detail = ""
        if result.source_sample_rate is not None:
            detail = (
                f" (src: {result.source_sample_rate} Hz, "
                f"{result.source_channels}ch, {result.source_codec})"
            )
        print(f" -> {tag}: {result.message}{detail}")

    ok_count = sum(1 for r in results if r.ok)
    print(f"\n{ok_count}/{len(results)} succeeded.")
    failed = [r for r in results if not r.ok]
    if failed:
        print(f"{len(failed)} failed or skipped:")
        for r in failed:
            print(f"  - {r.source.name}: {r.message}")
        if not args.dry_run and any("ffmpeg failed" in r.message for r in failed):
            sys.exit(1)


if __name__ == "__main__":
    main()
