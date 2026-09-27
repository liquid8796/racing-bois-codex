"""Synthetic raw-data negative controls; never native measurement evidence."""
import copy
import unittest
from verify import measurements


class MeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = []
        previous = 0
        for index in range(36001):
            seconds = index / 60 + .0001
            cls.frames.append({key: str(value) for key, value in dict(index=index, seconds=seconds, frame_ms=(seconds-previous)*1000,
                unity_frame=index+1000, tick=index+600, cycle=0, measured_ticks=index, width=1920, height=1080, quality=1, target_frame_rate=-1, vsync_count=0,
                riders=8, traffic=4, pedestrians=2, focused=1, timing_timestamp=index, cpu_ms='', gpu_ms='', gc_bytes='').items()})
            previous = seconds
        cls.memory = [dict(seconds=str(index+.0001), working_set_bytes='100000000', private_bytes='120000000', unity_allocated_bytes='50000000', managed_bytes='30000000', graphics_driver_bytes='') for index in range(600)]
        cls.workload = dict(status='completed', editor=False, requestedSampleSeconds=600, warmupSeconds=10, frames=36000,
            measuredSimulationTicks=36000, worldRestarts=0, measuredSeconds=600, measurementCoverageValid=True, requiredDensityPresentEverySample=True, targetFrameRate=-1, vSyncCount=0)

    def values(self):
        return [dict(row) for row in self.frames], [dict(row) for row in self.memory], dict(self.workload), {'stress': False}

    def test_complete_fixture_window_with_partial_first_sample(self):
        result = measurements(*self.values())
        self.assertTrue(result['workloadCoveragePassed'])
        self.assertTrue(result['timingBudgetPassed'])
        self.assertTrue(result['memoryBudgetPassed'])
        self.assertEqual(0, result['gpuTimingFrames'])

    def test_interval_tampering_rejected(self):
        values = self.values(); values[0][500]['frame_ms'] = '0'
        with self.assertRaises(ValueError): measurements(*values)

    def test_dropped_unity_frame_rejected(self):
        values = self.values(); values[0][500]['unity_frame'] = '1502'
        with self.assertRaises(ValueError): measurements(*values)

    def test_nonfinite_frame_rejected(self):
        values = self.values(); values[0][500]['seconds'] = 'NaN'
        with self.assertRaises(ValueError): measurements(*values)

    def test_unexplained_tick_reset_rejected(self):
        values = self.values(); values[0][500]['tick'] = '0'
        with self.assertRaises(ValueError): measurements(*values)

    def test_observed_world_cycle_can_reset_world_tick(self):
        frames, memory, workload, binding = self.values()
        for index in range(18000, len(frames)):
            frames[index]['cycle'] = '1'; frames[index]['tick'] = str(index-18000)
        workload['worldRestarts'] = 1
        self.assertTrue(measurements(frames, memory, workload, binding)['workloadCoveragePassed'])

    def test_measured_simulation_counter_cannot_reset(self):
        values = self.values(); values[0][500]['measured_ticks'] = '1'
        with self.assertRaises(ValueError): measurements(*values)

    def test_incomplete_window_rejected(self):
        values = self.values(); values[0].pop()
        with self.assertRaises(ValueError): measurements(*values)

    def test_changed_resolution_is_observed_failure(self):
        values = self.values(); values[0][500]['width'] = '1280'
        self.assertFalse(measurements(*values)['workloadCoveragePassed'])

    def test_missing_memory_cannot_be_zero_or_pass(self):
        values = self.values()
        for row in values[1]: row['working_set_bytes'] = row['private_bytes'] = ''
        result = measurements(*values)
        self.assertFalse(result['memoryBudgetPassed'])
        self.assertEqual(0, result['processMemorySamples'])

    def test_zero_process_counter_is_unavailable_not_zero_memory_use(self):
        values = self.values(); values[1][0]['working_set_bytes'] = values[1][0]['private_bytes'] = '0'
        with self.assertRaises(ValueError): measurements(*values)

    def test_repeated_memory_sample_rejected(self):
        values = self.values(); values[1][2]['seconds'] = values[1][1]['seconds']
        with self.assertRaises(ValueError): measurements(*values)

    def test_partial_process_memory_sample_rejected(self):
        values = self.values(); values[1][2]['private_bytes'] = ''
        with self.assertRaises(ValueError): measurements(*values)

    def test_background_window_is_not_graphics_coverage(self):
        values = self.values()
        for row in values[0]: row['focused'] = '0'
        self.assertFalse(measurements(*values)['workloadCoveragePassed'])

    def test_unsampled_memory_tail_cannot_pass_budget(self):
        values = self.values(); del values[1][590:]
        self.assertFalse(measurements(*values)['memoryBudgetPassed'])

    def test_memory_sample_must_match_observed_frame(self):
        values = self.values(); values[1][10]['seconds'] = '10.0123'
        with self.assertRaises(ValueError): measurements(*values)

    def test_reintroduced_frame_cap_fails_workload_coverage(self):
        values = self.values(); values[0][500]['target_frame_rate'] = '60'
        self.assertFalse(measurements(*values)['workloadCoveragePassed'])

    def test_summary_ticks_cannot_be_fabricated(self):
        values = self.values(); values[2]['measuredSimulationTicks'] += 50
        with self.assertRaises(ValueError): measurements(*values)

    def test_editor_fixture_cannot_be_native(self):
        values = self.values(); values[2]['editor'] = True
        with self.assertRaises(ValueError): measurements(*values)

    def test_measured_ticks_cannot_start_with_invented_work(self):
        values = self.values()
        for row in values[0]: row['measured_ticks'] = str(int(row['measured_ticks']) + 36000)
        values[2]['measuredSimulationTicks'] += 36000
        with self.assertRaises(ValueError): measurements(*values)

    def test_measured_tick_jump_cannot_exceed_real_update_step_cap(self):
        values = self.values()
        for row in values[0][500:]: row['measured_ticks'] = str(int(row['measured_ticks']) + 7)
        values[2]['measuredSimulationTicks'] += 7
        with self.assertRaises(ValueError): measurements(*values)


if __name__ == '__main__': unittest.main()
