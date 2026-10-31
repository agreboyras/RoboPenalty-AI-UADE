"""Synthetic protocol tests, not evidence of physical execution."""
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch
import numpy as np
from .protocol import AMPLITUDE, ACTIVE, KNEES, residual, safety_reason, compare
from .run import main


class ProtocolTests(unittest.TestCase):
    def test_exact_authorized_amplitude(self):
        self.assertEqual(len(ACTIVE), 6)
        np.testing.assert_array_equal(AMPLITUDE[KNEES], [0.02, 0.02])
        self.assertEqual(sorted(AMPLITUDE[ACTIVE].tolist()), [-0.01]*4+[0.02]*2)
        self.assertFalse(AMPLITUDE.flags.writeable)

    def test_profile_is_bounded_and_recovers(self):
        for t in (0, 2, 3, 8, 9, 10):
            np.testing.assert_array_equal(residual(t), np.zeros(29))
        for t in (5, 5.5, 6):
            np.testing.assert_array_equal(residual(t), AMPLITUDE)
        weights = np.array([residual(t)[KNEES[0]] for t in np.linspace(3, 5, 1001)])
        self.assertTrue(np.all(np.diff(weights) >= 0))
        self.assertLessEqual(np.abs(np.diff(weights)/0.002).max(), 0.018751)
        for t in np.linspace(3, 5, 101):
            np.testing.assert_allclose(residual(t), residual(11-t), atol=1e-15)

    def test_safety_guards(self):
        base = dict(height=0.77, tilt=np.zeros(2), drift=0, q=np.zeros(29),
            joint_ranges=np.tile([-1, 1], (29, 1)), dq=np.zeros(29),
            applied=np.zeros(29), torque_limits=np.full(29, 5), saturation_steps=0,
            improper=False, penetration=0.00434, external=False, warnings=False)
        self.assertIsNone(safety_reason(**base))
        cases = [('height', 0.49), ('tilt', [15, 0]), ('drift', 0.1),
                 ('q', np.full(29, 2)), ('dq', np.full(29, 8.01)),
                 ('applied', np.full(29, 5.01)), ('saturation_steps', 50),
                 ('improper', True), ('penetration', 0.00501), ('external', True),
                 ('warnings', True), ('height', float('nan'))]
        for key, value in cases:
            self.assertIsNotNone(safety_reason(**dict(base, **{key: value})), key)

    def fixture(self):
        q = np.zeros((5001, 36)); q[:, 2] = 0.77; q[:, 3] = 1
        return q

    def test_standing_alone_is_not_success(self):
        baseline = self.fixture()
        result = compare(baseline.copy(), baseline)
        self.assertFalse(result['success'])
        self.assertFalse(result['checks']['knees_each'])
        self.assertFalse(result['checks']['pelvis_lowered'])

    def test_measured_motion_and_recovery_required(self):
        baseline = self.fixture(); q = baseline.copy()
        q[2750:3000, 2] -= 0.001
        q[2750:3000, np.array(KNEES)+7] += 0.01
        self.assertTrue(compare(q, baseline)['success'])
        q[4500:, np.array(ACTIVE)+7] += 0.01
        self.assertFalse(compare(q, baseline)['checks']['joints_recovered'])

    def test_incomplete_never_passes(self):
        self.assertFalse(compare(self.fixture()[:2000], self.fixture())['success'])

    def test_viewer_rejects_failed_headless_report_before_loading_policy(self):
        scratch = Path(__file__).resolve().parents[4]/'validation/keeper_residual4b2'
        with tempfile.TemporaryDirectory(dir=scratch) as d:
            root = Path(d)
            (root/'report.json').write_text(json.dumps(dict(viewer_enabled=False)), encoding='utf-8')
            with patch('sys.argv', ['residual', '--deploy', 'unused', '--output', str(root/'out'),
                                   '--viewer', '--validated-run', str(root)]), patch(
                    'experiments.keeper_residual4b2.run.Locomotion') as policy:
                with self.assertRaises(SystemExit) as raised:
                    main()
                self.assertEqual(raised.exception.code, 2)
                policy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
