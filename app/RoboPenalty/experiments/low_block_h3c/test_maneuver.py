import unittest
import numpy as np
from .maneuver import LowBlock,PROTOCOL

NAMES=['left_hip_pitch_joint','left_hip_roll_joint','left_hip_yaw_joint','left_knee_joint','left_ankle_pitch_joint','left_ankle_roll_joint',
'right_hip_pitch_joint','right_hip_roll_joint','right_hip_yaw_joint','right_knee_joint','right_ankle_pitch_joint','right_ankle_roll_joint']+[f'other_{i}' for i in range(17)]

class ManeuverTests(unittest.TestCase):
    def test_two_observations_required(self):
        b=LowBlock(NAMES);b.observe(10.,[-1,0,.115],[5,.3,0]);self.assertIsNone(b.trigger)
        b.observe(10.02,[-.9,.006,.115],[5,.3,0]);self.assertEqual(b.trigger,10.02)
    def test_center_does_not_trigger(self):
        b=LowBlock(NAMES)
        for t in np.arange(0,1,.02):b.observe(t,[0,-.1,.115],[5,0,0])
        self.assertIsNone(b.trigger)
    def test_disabled_is_exact_zero(self):
        b=LowBlock(NAMES,enabled=False)
        for t in (0,1,2,5):b.observe(t,[0,.3,.115],[5,0,0]);np.testing.assert_array_equal(b.residual(t),np.zeros(29))
    def test_shifted_clock_has_same_residual(self):
        a,b=LowBlock(NAMES),LowBlock(NAMES)
        for x in (0,.02):a.observe(x,[0,.3,.115],[5,0,0]);b.observe(x+100,[0,.3,.115],[5,0,0])
        np.testing.assert_allclose(a.residual(.17),b.residual(100.17),atol=1e-13)
    def test_only_two_joints_and_smooth_bounds(self):
        b=LowBlock(NAMES,.08);b.trigger=0.
        rows=np.array([b.residual(t) for t in np.arange(0,.5,.002)])
        self.assertEqual(np.flatnonzero(abs(rows).max(axis=0)).tolist(),[7,11])
        self.assertLessEqual(abs(rows).max(),.08)
        self.assertLess(abs(np.diff(rows,axis=0)/.002).max(),PROTOCOL['max_reference_residual_speed_rad_s'])
        self.assertLess(abs(np.diff(rows,n=2,axis=0)/.002**2).max(),PROTOCOL['max_reference_residual_acceleration_rad_s2'])
    def test_recovery_has_no_jump(self):
        b=LowBlock(NAMES);b.trigger=0.;a=b.residual(.16)
        b.observe(.16,[4.5,.3,.115],[5,0,0]);np.testing.assert_allclose(a,b.residual(.16))
        np.testing.assert_array_equal(b.residual(1.),np.zeros(29))
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):LowBlock(NAMES).observe(0,[0,np.nan,0],[1,0,0])
    def test_unapproved_amplitude_rejected(self):
        with self.assertRaises(ValueError):LowBlock(NAMES,.2)
    def test_bad_policy_target_rejected_before_pd(self):
        from .run import policy_target
        ranges=np.tile([-1.,1.],(29,1))
        for v in (0.,[0.]*28,[np.nan]*29):
            with self.assertRaises(ValueError):policy_target(v,ranges)
    def test_policy_limit_clipping_matches_h1(self):
        from .run import policy_target
        ranges=np.tile([-1.,1.],(29,1));raw,clipped=policy_target([2.]*29,ranges)
        np.testing.assert_array_equal(raw,np.full(29,2.));np.testing.assert_array_equal(clipped,np.ones(29))

if __name__=='__main__':unittest.main()
