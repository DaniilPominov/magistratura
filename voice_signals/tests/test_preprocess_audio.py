"""Tests for scripts/preprocess_audio.py.

These tests spawn real ffmpeg/ffprobe processes, so they are skipped on any
machine without ffmpeg on PATH rather than failing the suite.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "preprocess_audio.py"
TEST_WAV = PROJECT_ROOT / "tests" / "test_data" / "Ru-Vegetables.wav"

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _load_preprocess_module():
    spec = importlib.util.spec_from_file_location("preprocess_audio", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    # dataclasses needs the module registered in sys.modules before
    # exec_module runs (it resolves type hints via sys.modules[__module__]).
    sys.modules["preprocess_audio"] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(FFMPEG_AVAILABLE, "ffmpeg/ffprobe not found on PATH")
@unittest.skipUnless(TEST_WAV.is_file(), "reference test WAV not present")
class PreprocessAudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_preprocess_module()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _make_fixture(self, name: str, *, args: list[str]) -> Path:
        dest = self.tmp_path / name
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(TEST_WAV), *args, str(dest)],
            check=True, capture_output=True,
        )
        return dest

    def test_converts_hires_stereo_wav_to_mono_16bit(self) -> None:
        fixture = self._make_fixture(
            "hires_stereo.wav",
            args=["-ar", "44100", "-ac", "2", "-c:a", "pcm_s24le"],
        )
        out_dir = self.tmp_path / "out"
        result = self.module.convert_one(
            fixture, out_dir / "hires_stereo.wav",
            sample_rate=16_000, overwrite=False, dry_run=False,
        )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.source_sample_rate, 44_100)
        self.assertEqual(result.source_channels, 2)

        with wave.open(str(out_dir / "hires_stereo.wav"), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 16_000)

    def test_converts_mp3_to_mono_16bit_wav(self) -> None:
        fixture = self._make_fixture("sample.mp3", args=["-b:a", "192k"])
        out_dir = self.tmp_path / "out"
        result = self.module.convert_one(
            fixture, out_dir / "sample.wav",
            sample_rate=16_000, overwrite=False, dry_run=False,
        )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.source_codec, "mp3")

        with wave.open(str(out_dir / "sample.wav"), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 16_000)

    def test_respects_custom_target_rate(self) -> None:
        fixture = self._make_fixture(
            "hires.wav", args=["-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le"],
        )
        out_dir = self.tmp_path / "out"
        result = self.module.convert_one(
            fixture, out_dir / "hires.wav",
            sample_rate=8_000, overwrite=False, dry_run=False,
        )
        self.assertTrue(result.ok, result.message)
        with wave.open(str(out_dir / "hires.wav"), "rb") as wf:
            self.assertEqual(wf.getframerate(), 8_000)

    def test_does_not_overwrite_existing_output_by_default(self) -> None:
        fixture = self._make_fixture("sample2.mp3", args=["-b:a", "128k"])
        out_dir = self.tmp_path / "out"
        dest = out_dir / "sample2.wav"
        first = self.module.convert_one(
            fixture, dest, sample_rate=16_000, overwrite=False, dry_run=False,
        )
        self.assertTrue(first.ok)

        second = self.module.convert_one(
            fixture, dest, sample_rate=16_000, overwrite=False, dry_run=False,
        )
        self.assertFalse(second.ok)
        self.assertIn("exists", second.message)

    def test_dry_run_does_not_write_file(self) -> None:
        fixture = self._make_fixture("sample3.mp3", args=["-b:a", "128k"])
        out_dir = self.tmp_path / "out"
        dest = out_dir / "sample3.wav"
        result = self.module.convert_one(
            fixture, dest, sample_rate=16_000, overwrite=False, dry_run=True,
        )
        self.assertTrue(result.ok)
        self.assertFalse(dest.exists())

    def test_discover_inputs_filters_by_known_extensions(self) -> None:
        (self.tmp_path / "a.wav").write_bytes(b"")
        (self.tmp_path / "b.mp3").write_bytes(b"")
        (self.tmp_path / "c.txt").write_bytes(b"")
        (self.tmp_path / "sub").mkdir()
        (self.tmp_path / "sub" / "d.flac").write_bytes(b"")

        flat = self.module.discover_inputs(self.tmp_path, recursive=False)
        self.assertEqual({p.name for p in flat}, {"a.wav", "b.mp3"})

        recursive = self.module.discover_inputs(self.tmp_path, recursive=True)
        self.assertEqual(
            {p.name for p in recursive}, {"a.wav", "b.mp3", "d.flac"}
        )


if __name__ == "__main__":
    unittest.main()
