import math
import unittest

from voice_signals.dynamics import modified_rs_hurst
from voice_signals.schemas import SegmentRecord
from voice_signals.vad import EnergyVad, EnergyVadConfig


class VadTests(unittest.TestCase):
    def test_speech_tone_is_segmented_and_silence_is_not(self) -> None:
        sample_rate = 8_000
        audio = [0.0] * sample_rate + [
            0.4 * math.sin(2 * math.pi * 220 * index / sample_rate)
            for index in range(sample_rate)
        ] + [0.0] * sample_rate
        segments = EnergyVad().process_array(audio, sample_rate)
        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0].start_sec, 1.0, delta=0.02)
        self.assertAlmostEqual(segments[0].end_sec, 2.0, delta=0.02)

    def test_short_speech_is_removed(self) -> None:
        audio = [0.5] * 40 + [0.0] * 7_960
        segments = EnergyVad(EnergyVadConfig(min_speech_ms=100)).process_array(audio, 8_000)
        self.assertEqual(segments, [])

    def test_contract_rejects_overlap_and_bad_label(self) -> None:
        with self.assertRaises(ValueError):
            SegmentRecord("x", None, "vad", 1.0, 0.5, "speech", None, "test")
        with self.assertRaises(ValueError):
            SegmentRecord("x", None, "vad", 0.0, 1.0, "other", None, "test")

    def test_hurst_result_is_deterministic(self) -> None:
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(10_000)]
        first = modified_rs_hurst(values, 8_000)
        second = modified_rs_hurst(values, 8_000)
        self.assertEqual(first, second)
        self.assertTrue(first.valid)


if __name__ == "__main__":
    unittest.main()
