"""Contract/safety tests, kept outside the public game test entry points."""
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
from types import SimpleNamespace
import numpy as np
from .policy import Locomotion, gravity_body, digest, read_config, JOINTS
from .run_trial import evaluate, CRITERIA, run
from .scene import build


class ContractTests(unittest.TestCase):
    def test_gravity_identity_and_yaw(self):
        np.testing.assert_allclose(gravity_body([1, 0, 0, 0]), [0, 0, -1])
        np.testing.assert_allclose(gravity_body([0, 0, 0, 1]), [0, 0, -1])

    def test_observation_order_and_zero_command(self):
        p = Locomotion.__new__(Locomotion)
        p.mapping = np.arange(29)[::-1]
        p.default = np.ones(29)
        p.last_action = np.full(29, 0.3)
        p.cfg = dict(ang_vel_scale=1, dof_pos_scale=1, dof_vel_scale=1)
        obs = p.observe(np.arange(29), np.arange(29)*2, [1, 0, 0, 0], [1, 2, 3])
        self.assertEqual(obs.shape, (96,))
        np.testing.assert_array_equal(obs[6:9], [0, 0, 0])
        np.testing.assert_array_equal(obs[9:38], np.arange(29)[::-1]-1)
        np.testing.assert_array_equal(obs[38:67], np.arange(29)[::-1]*2)
        np.testing.assert_allclose(obs[67:], 0.3)

    def test_inverse_joint_permutation(self):
        p = Locomotion.__new__(Locomotion)
        p.mapping = np.arange(29)[::-1]
        np.testing.assert_array_equal(p.to_motor(np.arange(29)), np.arange(29)[::-1])
        self.assertEqual(len(set(JOINTS)), 29)

    def test_config_changes_fail(self):
        f = Path('config.yaml')
        with patch.object(Path, 'read_bytes', return_value=b'a: 1\r\n'):
            self.assertEqual(read_config(f, digest(b'a: 1\n')), {'a': 1})
        with patch.object(Path, 'read_bytes', return_value=b'a: 2\n'):
            with self.assertRaises(ValueError):
                read_config(f, digest(b'a: 1\n'))

    def test_frozen_criteria_and_rejections(self):
        m = dict(steps=5000, decisions=500, min_pelvis_height_m=0.79,
                 max_tilt_deg=0, max_drift_m=0, improper_contact_steps=0,
                 max_saturation_run_s=0, joint_limit_violation_steps=0,
                 finite=True, no_external_forces=True, normalizer_unchanged=True)
        self.assertTrue(all(evaluate(m).values()))
        for field, value in [('steps', 4999), ('decisions', 499), ('max_tilt_deg', 15),
                             ('max_drift_m', 0.1), ('max_saturation_run_s', 0.1),
                             ('improper_contact_steps', 1), ('joint_limit_violation_steps', 1),
                             ('no_external_forces', False)]:
            self.assertFalse(all(evaluate(dict(m, **{field: value})).values()), field)
        self.assertEqual(CRITERIA['steps'], 5000)

    def test_free_scene_and_effective_limits(self):
        xml = Path(__file__).resolve().parents[3]/'unitree_mujoco/unitree_robots/g1/g1_29dof.xml'
        before = digest(xml.read_bytes())
        m, d, qa, va, jid, limits, feet = build(xml, np.zeros(29), np.full(29, 1000))
        self.assertEqual((m.nq, m.nv, m.nu, m.neq), (36, 35, 29, 0))
        self.assertEqual(limits[1], 88)
        self.assertEqual(limits[20], 5)
        self.assertFalse(np.any(d.xfrc_applied))
        self.assertFalse(np.any(d.qfrc_applied))
        self.assertEqual(digest(xml.read_bytes()), before)
        self.assertEqual(len(feet), 2)

    def test_early_viewer_close_is_incomplete_and_releases_context(self):
        class ClosedViewer:
            cam = SimpleNamespace(lookat=np.zeros(3))
            closed = False

            def __enter__(self): return self
            def __exit__(self, *args): self.closed = True
            def is_running(self): return False
            def sync(self): pass

        view = ClosedViewer()
        policy = SimpleNamespace(reset=lambda: None, recurrent_max=lambda: 0,
            home=np.zeros(29), source_torque_limits=np.full(29, 1000),
            normalizer_unchanged=lambda: True, torch=SimpleNamespace(__version__='mock'))
        root = Path(__file__).resolve().parents[4]
        scratch = root/'validation/keeper_balance4b'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as d, patch(
                'mujoco.viewer.launch_passive', return_value=view):
            summary = run(policy, root/'app/unitree_mujoco/unitree_robots/g1/g1_29dof.xml',
                          Path(d)/'trial', viewer=True)
        self.assertTrue(view.closed)
        self.assertFalse(summary['success'])
        self.assertEqual(summary['metrics']['steps'], 0)
        self.assertEqual(summary['metrics']['stopped'], 'viewer_closed_early')


if __name__ == '__main__':
    unittest.main()
