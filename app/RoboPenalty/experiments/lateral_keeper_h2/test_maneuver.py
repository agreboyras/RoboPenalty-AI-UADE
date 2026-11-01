"""Trajectory contracts; physical success must be measured separately."""
import unittest
import numpy as np
from experiments.free_keeper4b.policy import JOINTS
from .maneuver import Maneuver,smooth,targets,PROTOCOL


class ManeuverTests(unittest.TestCase):
    def setUp(self):
        self.q=np.zeros(29);self.ranges=np.tile([-3.,3.],(29,1))

    def test_smooth_endpoints(self):
        self.assertEqual(smooth(0),0);self.assertEqual(smooth(1),1)
        self.assertLess(smooth(.0001),1e-10)
        self.assertLess(1-smooth(.9999),1e-10)

    def test_handoff_has_no_reference_jump(self):
        m=Maneuver(JOINTS,'LEFT','transfer',self.ranges)
        q=np.linspace(-.1,.1,29)
        np.testing.assert_array_equal(m.reference(2.,q,self.q),q)
        np.testing.assert_array_equal(m.reference(2.9,q+1,self.q),q)
        self.assertEqual(m.handoff_reference_jump,0.)

    def test_no_changes_to_input_state(self):
        m=Maneuver(JOINTS,'LEFT','maneuver',self.ranges);q=self.q.copy()
        m.reference(2.,q,q);m.reference(3.3,q,q);m.reference(4.3,q,q)
        np.testing.assert_array_equal(q,self.q)

    def test_symmetric_targets(self):
        l=targets(self.q,list(JOINTS),'LEFT')[-1];r=targets(self.q,list(JOINTS),'RIGHT')[-1]
        for name in ('hip_roll','ankle_roll'):
            for side in ('left','right'):
                i=JOINTS.index(side+'_'+name+'_joint');self.assertEqual(l[i],-r[i])
        self.assertEqual(l[JOINTS.index('right_shoulder_roll_joint')],-r[JOINTS.index('left_shoulder_roll_joint')])
        self.assertEqual(l[JOINTS.index('waist_roll_joint')],-r[JOINTS.index('waist_roll_joint')])

    def test_smooth_at_phase_boundary(self):
        m=Maneuver(JOINTS,'LEFT','maneuver',self.ranges);m.reference(2.,self.q,self.q)
        for t in (2.2,3.,3.55,4.2,4.8):
            before=m.reference(t-1e-6,self.q,self.q)
            at=m.reference(t,self.q,self.q)
            after=m.reference(t+1e-6,self.q,self.q)
            self.assertLess(float(np.max(abs(before-at))),1e-7)
            self.assertLess(float(np.max(abs(after-at))),1e-7)

    def test_unsafe_target_is_rejected(self):
        m=Maneuver(JOINTS,'LEFT','maneuver',np.tile([-.01,.01],(29,1)))
        m.reference(2.,self.q,self.q)
        with self.assertRaisesRegex(ValueError,'joint limits'):m.reference(3.,self.q,self.q)

    def test_protocol_declares_body_motion_not_only_joint_change(self):
        self.assertEqual(PROTOCOL['minimum_pelvis_toward_m'],.20)
        self.assertEqual(PROTOCOL['minimum_wrist_toward_m'],.30)
        self.assertLess(PROTOCOL['max_penetration_m'],PROTOCOL['abort_penetration_m'])


if __name__=='__main__':unittest.main()
