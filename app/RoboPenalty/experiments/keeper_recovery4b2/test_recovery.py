"""Synthetic evaluation and immutable-protocol checks, not physical results."""
import unittest
from pathlib import Path
import tempfile
import json
import numpy as np
from experiments.keeper_residual4b2 import protocol as original
from . import protocol as extended
from .run import require_prefix, viewer_gate
from .analyze import describe


class RecoveryTests(unittest.TestCase):
    def fixture(self):
        b = np.zeros((10001, 36)); b[:, 2] = 0.77; b[:, 3] = 1
        q = b.copy()
        q[2750:3000, 2] -= 0.001
        q[2750:3000, np.asarray(extended.KNEES)+7] += 0.01
        return b, q

    def test_original_duration_and_functions_untouched(self):
        self.assertEqual(original.STEPS, 5000)
        self.assertEqual(extended.STEPS, 10000)
        self.assertIs(extended.residual, original.residual)
        self.assertIs(extended.safety_reason, original.safety_reason)
        self.assertIs(extended.LIMITS, original.LIMITS)
        for t in [8, 10, 15, 20]:
            np.testing.assert_array_equal(extended.residual(t), np.zeros(29))

    def test_late_recovery_does_not_reclassify_original_failure(self):
        b, q = self.fixture()
        q[4500:5001, 7+extended.KNEES[0]] += 0.007
        result = extended.compare(q, b)
        self.assertTrue(result['success'])
        self.assertFalse(result['original_joint_recovery_pass'])

    def test_persistent_deviation_fails(self):
        b, q = self.fixture()
        q[4500:, 7+extended.KNEES[0]] += 0.007
        result = extended.compare(q, b)
        self.assertFalse(result['success'])
        self.assertFalse(result['checks']['joints_recovered_mean'])

    def test_peak_catches_oscillation_hidden_by_mean(self):
        b, q = self.fixture()
        q[9990:10001, 7+extended.KNEES[0]] += 0.006
        result = extended.compare(q, b)
        self.assertTrue(result['checks']['joints_recovered_mean'])
        self.assertFalse(result['checks']['joints_recovered_peak'])

    def test_fixed_posture_is_not_used_as_baseline(self):
        b, q = self.fixture()
        drift = np.arange(10001)*0.000001
        b[:, 7:36] += drift[:, None]
        q[:, 7:36] += drift[:, None]
        self.assertTrue(extended.compare(q, b)['success'])
        self.assertEqual(len(extended.compare(q, b)['history']), 12)

    def test_incomplete_is_rejected(self):
        b, q = self.fixture()
        self.assertFalse(extended.compare(q[:5001], b)['success'])

    def test_partial_postmortem_never_claims_full_window(self):
        b, q = self.fixture()
        result = describe(q[:9939], b)
        self.assertFalse(result['complete_20s'])
        self.assertFalse(result['evaluation_window_complete'])
        self.assertFalse(result['intervals'][-1]['complete_interval'])
        self.assertAlmostEqual(result['observed_until_s'], 19.876)

    def test_prefix_change_and_failed_viewer_report_rejected(self):
        scratch = Path(__file__).resolve().parents[4]/'validation/keeper_recovery4b2'
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            r = Path(folder)
            np.savez(r/'old.npz', qpos=np.ones((2, 3)))
            np.savez(r/'new.npz', qpos=np.ones((4, 3)))
            self.assertEqual(require_prefix(r/'new.npz', r/'old.npz'), ['qpos'])
            np.savez(r/'new.npz', qpos=np.zeros((4, 3)))
            with self.assertRaises(ValueError): require_prefix(r/'new.npz', r/'old.npz')
            (r/'report.json').write_text(json.dumps(dict(viewer_enabled=False)), encoding='utf-8')
            with self.assertRaises(ValueError): viewer_gate(r)


if __name__ == '__main__':
    unittest.main()
