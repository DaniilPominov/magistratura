import math
import unittest

from voice_signals.dynamics import modified_rs_hurst, modified_rs_hurst_full_record
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

    def test_segment_scope_is_marked_not_comparable(self) -> None:
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(10_000)]
        result = modified_rs_hurst(values, 8_000)
        self.assertEqual(result.scope, "segment")
        self.assertFalse(result.comparable_to_reference)
        self.assertAlmostEqual(result.input_length_sec, 10_000 / 8_000)

    def test_full_record_scope_is_marked_comparable(self) -> None:
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(20_000)]
        result = modified_rs_hurst_full_record(values, 8_000)
        self.assertEqual(result.scope, "full_record")
        self.assertTrue(result.comparable_to_reference)
        self.assertEqual(result.tau_scale, "geometric")
        self.assertTrue(result.valid)

    def test_full_record_upper_tau_bound_is_not_halved(self) -> None:
        # Variant A must scale tau up to N (envelope length), not N/2.
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(40_000)]
        result = modified_rs_hurst_full_record(values, 8_000, max_tau=None)
        self.assertTrue(result.valid)
        envelope_len = len(values) // round(0.1 * 8_000)
        self.assertLessEqual(max(result.tau_values), envelope_len)
        self.assertGreater(max(result.tau_values), envelope_len // 2)

    def test_geometric_tau_scale_is_deterministic_and_bounded(self) -> None:
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(10_000)]
        first = modified_rs_hurst(values, 8_000, tau_scale="geometric", min_tau=4)
        second = modified_rs_hurst(values, 8_000, tau_scale="geometric", min_tau=4)
        self.assertEqual(first, second)
        self.assertTrue(first.valid)
        self.assertEqual(first.tau_scale, "geometric")
        self.assertGreaterEqual(min(first.tau_values), 4)

    def test_r_squared_threshold_parameter_controls_warning(self) -> None:
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(10_000)]
        strict = modified_rs_hurst(values, 8_000, r_squared_threshold=0.999999)
        lenient = modified_rs_hurst(values, 8_000, r_squared_threshold=0.0)
        self.assertTrue(strict.valid)
        self.assertTrue(lenient.valid)
        self.assertIn("weak_log_log_fit", strict.warnings)
        self.assertNotIn("weak_log_log_fit", lenient.warnings)

    def test_explicit_max_tau_zero_is_not_treated_as_auto(self) -> None:
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(10_000)]
        result = modified_rs_hurst(values, 8_000, max_tau=0)
        self.assertFalse(result.valid)
        self.assertIn("insufficient_rs_scales", result.warnings)

    def test_arithmetic_scale_on_full_record_length_input_is_rejected(self) -> None:
        # Regression: calling the per-segment function (arithmetic default)
        # on whole-recording-length audio used to silently run an O(N^2)
        # sweep (~27s on a 124s/8kHz file). It must now fail fast instead.
        # 90_000 samples at 8kHz / 25ms envelope window -> 450 envelope
        # points -> natural_upper (N//2) = 225 > the 200-tau guard.
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(90_000)]
        with self.assertRaises(ValueError):
            modified_rs_hurst(values, 8_000)

    def test_arithmetic_scale_on_normal_segment_length_is_unaffected(self) -> None:
        # Ordinary short-segment usage must not trip the guard.
        values = [math.sin(index / 7) + 0.1 * math.sin(index / 3) for index in range(5_000)]
        result = modified_rs_hurst(values, 8_000)
        self.assertTrue(result.valid)


if __name__ == "__main__":
    unittest.main()
