import unittest
import numpy as np
from experiments.free_keeper4b.policy import JOINTS
from experiments.lateral_keeper_h2.maneuver import Maneuver
from .trajectory import TimedManeuver
from .analyze import first_crossing
from .run import NoShotAdapter
from types import SimpleNamespace


class CenterTests(unittest.TestCase):
    def setUp(self):
        self.q=np.zeros(29);self.ranges=np.tile([-3.,3.],(29,1))

    def test_original_reference_is_unchanged(self):
        original=Maneuver(JOINTS,'LEFT','maneuver',self.ranges)
        wrapper=TimedManeuver(JOINTS,'LEFT','maneuver',self.ranges)
        for t in np.arange(0,6,.002):
            np.testing.assert_array_equal(original.reference(t,self.q,self.q),wrapper.reference(t,self.q,self.q))

    def test_fast_handoff_has_no_jump(self):
        q=np.linspace(-.1,.1,29)
        m=TimedManeuver(JOINTS,'RIGHT','maneuver',self.ranges,variant='fast')
        np.testing.assert_array_equal(m.reference(2.,q,self.q),q)
        self.assertEqual(m.handoff_reference_jump,0)
        self.assertEqual(m.state,'PREPARING')

    def test_fast_state_times_are_real_not_reference_clock(self):
        m=TimedManeuver(JOINTS,'LEFT','maneuver',self.ranges,variant='fast')
        for t in [2.,2.5,3.,3.5,4.5]:m.reference(t,self.q,self.q)
        np.testing.assert_allclose([s['time_s'] for s in m.transitions],[2.,2.5,3.,3.5,4.5])

    def test_only_arms_ablation_freezes_legs_and_torso(self):
        m=TimedManeuver(JOINTS,'LEFT','maneuver',self.ranges,variant='fast',component='arms')
        m.reference(2.,self.q,self.q);ref=m.reference(3.,self.q,self.q)
        np.testing.assert_array_equal(ref[:15],self.q[:15])
        self.assertGreater(abs(ref[15:]).max(),.1)

    def test_no_shot_commands_fixedpose_only(self):
        x=NoShotAdapter.__new__(NoShotAdapter);x.fixed_requested=False;x.kick_requested=False
        x.names=SimpleNamespace(PASSIVE='passive',FIXEDPOSE='fixed')
        x.commands=SimpleNamespace(POS_RESET='reset');x.state=SimpleNamespace(skill_cmd=None)
        x.fsm=SimpleNamespace(cur_policy=SimpleNamespace(name='passive'))
        x.command_before_step(0);self.assertEqual(x.state.skill_cmd,'reset')
        x.fsm.cur_policy.name='fixed';x.state.skill_cmd=None;x.command_before_step(5.)
        self.assertIsNone(x.state.skill_cmd);self.assertFalse(x.kick_requested)

    def test_interpolated_arrival_and_missing_threshold(self):
        self.assertAlmostEqual(first_crossing(np.array([2.,3.]),np.array([.1,.3]),.2),2.5)
        self.assertIsNone(first_crossing(np.array([2.,3.]),np.array([.1,.3]),.6))


if __name__=='__main__':unittest.main()
