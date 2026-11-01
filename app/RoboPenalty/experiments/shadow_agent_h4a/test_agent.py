import inspect
import ast
import math
import unittest
from dataclasses import replace
from .agent import Agent, Observation, CENTRAL_Y, CATALOG


class AgentTests(unittest.TestCase):
    def obs(self,**kw):
        o=Observation(4.4,(0.,CENTRAL_Y,.115),(5.,0.,0.),(4.2,0.,.77),(0.,0.,0.,1.),'SHOOTING')
        return replace(o,**kw)
    def test_nominal_similarity(self):
        self.assertEqual(Agent().observe(self.obs())['action'],'MANTENER_CENTRO')
    def test_lateral_abstention(self):
        for y in (.26,-.75,-.88,-1.24):
            self.assertEqual(Agent().observe(self.obs(ball_position_w=(0.,y,.115)))['action'],'SIN_ACCION_VIABLE')
    def test_experimental_never_selected(self):
        for i in range(-30,31):
            self.assertNotIn(Agent().observe(self.obs(ball_position_w=(0.,i*.05,.115)))['action'],('BLOQUEO_BAJO','CAIDA_LATERAL'))
    def test_stationary_no_detection(self):
        a=Agent();r=a.observe(self.obs(ball_velocity_w=(0.,0.,0.),phase='PREPARING'))
        self.assertIsNone(a.detected_s);self.assertEqual(r['action'],'SIN_ACCION_VIABLE')
    def test_phase_rejection(self):
        for phase in ('READY','PREPARING','RESOLVING','FINISHED'):
            self.assertEqual(Agent().observe(self.obs(phase=phase))['action'],'SIN_ACCION_VIABLE')
    def test_pose_rejection(self):
        for kw in (dict(keeper_position_w=(4.2,.1,.77)),dict(keeper_quaternion_w=(1.,0.,0.,0.)),
                   dict(keeper_quaternion_w=(0.,.3,0.,math.sqrt(.91)))):
            self.assertEqual(Agent().observe(self.obs(**kw))['action'],'SIN_ACCION_VIABLE')
    def test_unknown_height_abstains(self):
        self.assertEqual(Agent().observe(self.obs(ball_position_w=(0.,CENTRAL_Y,1.)))['action'],'SIN_ACCION_VIABLE')
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):Agent().observe(self.obs(time_s=float('nan')))
    def test_no_preset_or_actuator_contract(self):
        self.assertNotIn('action',Observation.__dataclass_fields__)
        tree=ast.parse(inspect.getsource(Agent))
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in ('preset','action','future','ctrl') for n in ast.walk(tree)))
        self.assertNotIn('mujoco',inspect.getsource(Agent))
    def test_observation_immutable(self):
        o=self.obs();before=repr(o);Agent().observe(o);self.assertEqual(before,repr(o))
    def test_causal_prefix(self):
        a,b=Agent(),Agent()
        for t in (4.2,4.22,4.24):self.assertEqual(a.observe(self.obs(time_s=t)),b.observe(self.obs(time_s=t)))
        b.observe(self.obs(time_s=4.26,ball_position_w=(2.,.8,.115)))
        self.assertEqual(a.history,b.history[:-1])
    def test_catalog_honest(self):
        self.assertEqual(CATALOG['BLOQUEO_BAJO']['status'],'experimental_not_validated')
        self.assertEqual(CATALOG['CAIDA_LATERAL']['status'],'experimental_not_validated')


if __name__=='__main__':unittest.main()
