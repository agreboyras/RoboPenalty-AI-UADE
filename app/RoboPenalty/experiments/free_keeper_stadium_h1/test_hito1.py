"""Control limits, physical composition and reference-result reporting."""
from . import bootstrap
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import mujoco
from .run import actuator_caps, crossing, root_addresses, CRITERIA
from .scene import build
from .policy_client import PolicyClient


class ContractTests(unittest.TestCase):
    def test_caps_use_smallest_effective_limit(self):
        m=SimpleNamespace(actuator_ctrllimited=[True],actuator_ctrlrange=np.array([[-9,8]]),
            actuator_forcelimited=[True],actuator_forcerange=np.array([[-7,6]]),
            jnt_actfrclimited=[True],jnt_actfrcrange=np.array([[-5,4]]))
        self.assertEqual(actuator_caps(m,SimpleNamespace(actuators=[0],joints=[0]),[100])[0],4)

    def test_goal_crossing_is_interpolated_forward_only(self):
        np.testing.assert_allclose(crossing(np.array([4.,1.,.1]),np.array([6.,2.,.2])),[5.,1.5,.15])
        self.assertIsNone(crossing(np.array([6.,0,0]),np.array([4.,0,0])))

    def test_no_silent_old_inference_response(self):
        c=PolicyClient.__new__(PolicyClient);c.seq=0;c.latencies=[]
        from io import StringIO
        c.process=SimpleNamespace(stdin=StringIO())
        c.receive=lambda:dict(seq=0,target=[0]*29)
        with self.assertRaisesRegex(RuntimeError,'Stale'):c.request('observe')

    def test_fixed_protocol(self):
        self.assertEqual(CRITERIA['physics_steps'],7000)
        self.assertEqual(CRITERIA['duration_s'],14.)
        self.assertEqual(CRITERIA['max_tilt_deg'],15.)


class CompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=bootstrap.PROJECT.parents[1]
        cls.deploy=root/'validation/keeper_live_20261030/package/app/RoboNaldo_Deploy'
        if not (cls.deploy/'g1_description/scene_with_ball.xml').exists():
            raise unittest.SkipTest('Requires explicitly installed private FreeKick assets; no download')
        cls.m,cls.d,cls.s,cls.k,cls.checks=build(cls.deploy,bootstrap.PROJECT.parent/'unitree_mujoco',np.zeros(29),4.)

    def test_root_is_physically_free_and_no_slider(self):
        self.assertTrue(all(self.checks.values()));root_addresses(self.m,self.k)
        self.assertEqual(self.m.nu,58)
        self.assertFalse(any('keeper_slide' in self.m.joint(j).name for j in range(self.m.njnt)))

    def test_independent_motor_indices(self):
        self.assertFalse(set(self.s.actuators)&set(self.k.actuators))
        self.assertEqual(len(self.k.actuators),29)

    def test_original_soles_start_one_mm_above_existing_floor(self):
        floor_z=self.d.geom_xpos[self.m.geom('floor').id,2]
        soles=[self.d.geom_xpos[g,2]-self.m.geom_size[g,0] for g in self.k.foot_geoms
            if self.m.geom_type[g]==mujoco.mjtGeom.mjGEOM_SPHERE and self.m.geom_contype[g]]
        self.assertAlmostEqual(min(soles)-floor_z,.001,places=12)


if __name__=='__main__':unittest.main()
