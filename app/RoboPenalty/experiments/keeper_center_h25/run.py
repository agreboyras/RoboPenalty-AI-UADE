"""Private H2 driver instance: center placement, FIXEDPOSE striker, timed variant."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import mujoco
from experiments.free_keeper_stadium_h1.scene import build as original_build
from experiments.free_keeper_stadium_h1.run import dump
from phase2.freekick_adapter import FreeKickAdapter
from .trajectory import TimedManeuver,FAST_REAL,FAST_V1,ORIGINAL_CLOCK
from .presentation import CenterPresenter

PROJECT=bootstrap.PROJECT


class NoShotAdapter(FreeKickAdapter):
    def command_before_step(self,sim_time):
        if not self.fixed_requested and self.fsm.cur_policy.name==self.names.PASSIVE:
            self.state.skill_cmd=self.commands.POS_RESET;self.fixed_requested=True
        # Do not request CMD_FREEKICK. No policy, gain or physical parameter changes.


class GeometryProbe:
    def __init__(self):self.count=0;self.contacts=[];self.positions=[];self.min_gaps={};self.unmodified=True

    def bind(self,m,k,s):
        self.model=m;self.keeper=k;self.shooter=s
        self.physical=[g for g in k.geoms if m.geom_contype[g] or m.geom_conaffinity[g]]
        self.goal=[g for g in range(m.ngeom) if m.geom(g).name.startswith('goal_')]
        self.goal_description=[dict(name=m.geom(g).name,body=m.body(int(m.geom_bodyid[g])).name,
            contype=int(m.geom_contype[g]),conaffinity=int(m.geom_conaffinity[g]),size=m.geom_size[g].tolist()) for g in self.goal]
        self.other_physical=[dict(name=m.geom(g).name,body=m.body(int(m.geom_bodyid[g])).name,
            contype=int(m.geom_contype[g]),conaffinity=int(m.geom_conaffinity[g])) for g in range(m.ngeom)
            if g not in k.geoms and g not in s.geoms and (m.geom_contype[g] or m.geom_conaffinity[g])]

    def sample(self,d):
        m=self.model;before=np.r_[d.qpos,d.qvel,d.ctrl,d.qfrc_applied,d.xfrc_applied.reshape(-1)]
        for ci in range(d.ncon):
            c=d.contact[ci];a,b=map(int,c.geom)
            if a not in self.keeper.geoms and b not in self.keeper.geoms:continue
            f=np.zeros(6);mujoco.mj_contactForce(m,d,ci,f)
            if f[0]>.001:
                self.contacts.append(dict(time_s=float(d.time)-.002,geoms=[m.geom(a).name,m.geom(b).name],distance_m=float(c.dist),normal_force_n=float(f[0])))
        if self.count%10==0 or self.count==2999:
            lower=[];upper=[]
            for g in self.physical:
                rot=d.geom_xmat[g].reshape(3,3);center=d.geom_xpos[g]+rot@m.geom_aabb[g,:3]
                extent=abs(rot)@m.geom_aabb[g,3:];lower.append(center-extent);upper.append(center+extent)
            self.positions.append(dict(time_s=float(d.time)-.002,pelvis=d.xpos[self.keeper.pelvis].tolist(),
                collision_envelope_min=np.min(lower,axis=0).tolist(),collision_envelope_max=np.max(upper,axis=0).tolist()))
            for goal in self.goal:
                gap=min(float(mujoco.mj_geomDistance(m,d,g,goal,2.,None)) for g in self.physical)
                name=m.geom(goal).name;self.min_gaps[name]=min(self.min_gaps.get(name,2.),gap)
        self.count+=1
        self.unmodified &= bool(np.array_equal(before,np.r_[d.qpos,d.qvel,d.ctrl,d.qfrc_applied,d.xfrc_applied.reshape(-1)]))

    def report(self):
        final=self.positions[-1] if self.positions else None
        if final:
            x,y,z=final['pelvis'];final.update(pelvis_side_of_goal='BEHIND_LINE' if x>=5 else 'FIELD_SIDE',
                pelvis_between_posts=abs(y)<=1.5,body_envelope_crosses_goal_plane=final['collision_envelope_max'][0]>5,
                body_envelope_outside_posts=final['collision_envelope_min'][1]<-1.5 or final['collision_envelope_max'][1]>1.5)
        return dict(goal_geometries=self.goal_description,other_physical=self.other_physical,
            contacts=self.contacts,minimum_distance_to_visual_goal_m=self.min_gaps,final=final,
            samples=self.positions,observer_did_not_modify_integration_arrays=self.unmodified,
            warning='Negative distance to a noncollidable goal is VISUAL overlap, not a solver contact. Envelopes are conservative.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('deploy','loco-deploy','policy-python','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--variant',choices=('original','fast','fast_v1','fast_v2'),default='original')
    p.add_argument('--side',choices=('LEFT','RIGHT'),default='LEFT')
    p.add_argument('--component',choices=('full','legs_torso','arms'),default='full')
    p.add_argument('--viewer',action='store_true');p.add_argument('--capture',action='store_true')
    a=p.parse_args();a.output=a.output.resolve()
    original_path=PROJECT/'experiments/lateral_keeper_h2/run.py'
    spec=importlib.util.spec_from_file_location('experiments.lateral_keeper_h2.private_center_h25',original_path)
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    probe=GeometryProbe();state={}
    def centered(deploy,unitree,home,ignored_y):
        m,d,s,k,checks=original_build(deploy,unitree,home,0.)
        probe.bind(m,k,s)
        forward=d.xmat[k.pelvis].reshape(3,3)[:,0]
        if not np.allclose(forward,[-1,0,0],atol=1e-12):raise ValueError('Keeper not facing the shooter')
        state.update(initial_pelvis=d.xpos[k.pelvis].tolist(),forward=forward.tolist())
        return m,d,s,k,checks
    class NoShot(NoShotAdapter):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);state['kick']=self
    class MjObserver:
        def __getattr__(self,key):return getattr(mujoco,key)
        def mj_step(self,m,d,*args,**kwargs):
            result=mujoco.mj_step(m,d,*args,**kwargs);probe.sample(d);return result
    class Presenter(CenterPresenter):record_phases=a.capture
    engine.build=centered;engine.FreeKickAdapter=NoShot;engine.mujoco=MjObserver()
    def planner(*v):
        obj=TimedManeuver(*v,variant=a.variant,component=a.component);state['planner']=obj;return obj
    engine.Maneuver=planner
    engine.ManeuverPresenter=Presenter
    engine.PROTOCOL=dict(engine.PROTOCOL,variant=a.variant,component=a.component)
    knots=FAST_V1 if a.variant=='fast_v1' else FAST_REAL
    if a.variant!='original':engine.PROTOCOL.update(takeover_end_s=2.,preparation_end_s=float(knots[1]),
        push_end_s=float(knots[2]),extension_end_s=float(knots[3]),final_blend_end_s=float(knots[4]))
    argv=sys.argv
    sys.argv=[str(original_path),'--deploy',str(a.deploy),'--loco-deploy',str(a.loco_deploy),
        '--policy-python',str(a.policy_python),'--output',str(a.output),'--mode','maneuver','--side',a.side]
    if a.viewer:sys.argv.append('--viewer')
    if a.capture:sys.argv.append('--capture')
    try:code=engine.main()
    finally:sys.argv=argv
    if a.output.is_dir():
        kick=state.pop('kick',None)
        plan=state.pop('planner',None)
        dump(a.output/'geometry.json',probe.report())
        dump(a.output/'variant.json',dict(variant=a.variant,side=a.side,component=a.component,
            initial=state,commanded_shot=False,
            ball_note='No CMD_FREEKICK; dynamic ball may move through incidental physical contact. Not an immobilized ball test.',
            shooter_fixedpose=bool(kick and kick.fsm.cur_policy.name==kick.names.FIXEDPOSE),
            freekick_requested=bool(kick and kick.kick_requested),
            real_knots=(ORIGINAL_CLOCK if a.variant=='original' else knots).tolist(),reference_knots=ORIGINAL_CLOCK.tolist(),
            landing_elbow_rad=1.0 if a.variant=='fast' else None,
            final_joint_reference=plan.original.final.tolist() if plan is not None and plan.original.final is not None else None,
            changes='Only instance-local driver bindings: centered build, no kick command, reference timing, diagnostics and camera.',
            source_sha256={n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('run.py','trajectory.py','presentation.py')}))
    return code


if __name__=='__main__':raise SystemExit(main())
