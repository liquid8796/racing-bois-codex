"""Negative raw-evidence verifier tests; fixtures never count as player acceptance."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("player_qa", Path(__file__).with_name("verify-player-qa.py"))
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def rows(count=600):
    # Deliberately slow 1 FPS fixture: valid measurement structure, never a budget PASS.
    return [{"seconds": str(i + 1), "unity_frame": str(i + 10), "frame_ms": "1000", "online": "0", "live_race": "1", "content_ready": "1",
             "content_loading": "0", "input_blocked": "0", "ui_present": "1", "focused": "1", "cinematic": "0", "memory_sample": "1", "screenshot_requested": "0",
             "speed_m_s": "20", "tick": str((i + 1) * 60), "width": "1920", "height": "1080", "quality": "1", "cpu_ms": "", "gpu_ms": "", "gc_bytes": "",
             "working_set_bytes": "1000000", "private_bytes": "900000", "unity_allocated_bytes": "800000", "managed_bytes": "200000", "graphics_driver_bytes": ""} for i in range(count)]


class RawEvidenceTests(unittest.TestCase):
    def test_observed_slow_frames_cannot_be_converted_to_sixty_fps(self):
        result = qa.calculate(rows(), 0)
        self.assertEqual(1, result["meanFps"])
        self.assertEqual(1000, result["frameP95Ms"])

    def test_missing_counters_have_no_samples(self):
        result = qa.calculate(rows(), 0)
        self.assertEqual(0, result["cpuTimingFrames"])
        self.assertEqual(0, result["gpuTimingFrames"])
        self.assertEqual(0, result["gcFrames"])

    def test_menu_or_stationary_workload_is_visible_in_coverage(self):
        sample = rows()
        for row in sample: row["live_race"], row["speed_m_s"] = "0", "0"
        result = qa.calculate(sample, 0)
        self.assertEqual(0, result["raceCoverage"])
        self.assertEqual(0, result["movingCoverage"])

    def test_duplicate_or_missing_unity_frame_is_rejected(self):
        for value in ("10", "12"):
            sample = rows(); sample[1]["unity_frame"] = value
            with self.assertRaises(ValueError): qa.calculate(sample, 0)

    def test_short_duration_cannot_pass(self):
        with self.assertRaises(ValueError): qa.calculate(rows(599), 0)

    def test_nonfinite_or_tampered_duration_rejected(self):
        for value in ("NaN", "Infinity", "0", "16"):
            sample = rows(); sample[4]["frame_ms"] = value
            with self.assertRaises(ValueError): qa.calculate(sample, 0)

    def test_claimed_race_without_loaded_content_rejected(self):
        sample = rows(); sample[99]["content_ready"] = "0"
        with self.assertRaises(ValueError): qa.calculate(sample, 0)

    def test_focus_quality_and_motion_are_time_weighted(self):
        sample = rows()
        for row in sample[:300]: row["focused"], row["quality"], row["speed_m_s"] = "0", "0", "0"
        result = qa.calculate(sample, 0)
        self.assertEqual(.5, result["focusCoverage"])
        self.assertEqual(.5, result["expectedDisplayCoverage"])
        self.assertEqual(.5, result["movingCoverage"])


if __name__ == "__main__": unittest.main()
