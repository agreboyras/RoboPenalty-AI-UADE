"""Physical regression for the location and latency of the manual dive."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.free_keeper_stadium_h1 import bootstrap
from .dive_demo import run


DEPLOY = bootstrap.PROJECT.parent / 'RoboNaldo_Deploy'
G1_MESH = bootstrap.PROJECT.parent / 'unitree_mujoco/unitree_robots/g1/meshes/pelvis.STL'


@unittest.skipUnless(G1_MESH.is_file(), 'Requires the installed G1 meshes')
class DiveTests(unittest.TestCase):
    def test_both_sides_start_centered_and_land_between_the_posts(self):
        for side, sign in (('LEFT', 1), ('RIGHT', -1)):
            with self.subTest(side=side), TemporaryDirectory() as output:
                report = run(DEPLOY, Path(output), side, viewer=False, captures=False)
                self.assertTrue(report['success'], report)
                self.assertAlmostEqual(report['start_pelvis_w_m'][1], 0.)
                self.assertGreater(sign * report['final_pelvis_w_m'][1], .20)
                self.assertLess(report['max_lateral_collision_envelope_m'], report['goal_clear_half_span_m'])
                self.assertLess(report['pelvis_20_cm_after_command_s'], .65)


if __name__ == '__main__':
    unittest.main()
