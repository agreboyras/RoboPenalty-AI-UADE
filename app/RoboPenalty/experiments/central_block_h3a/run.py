"""Reuse an isolated H1 driver instance, adding read-only contact instrumentation."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import mujoco
from phase2.scene import RobotIndex
from phase4a.evaluation import classify
from experiments.free_keeper_stadium_h1.run import crossing
from experiments.free_keeper_stadium_h1.presentation import FreeKeeperPresenter

PROJECT=bootstrap.PROJECT
# Declared before execution; unchanged standing guards are still enforced by H1.
CRITERIA=dict(duration_s=14.,steps=7000,max_joint_speed_rad_s=20.,max_penetration_m=.02,
    max_joint_excess_rad=.03,torque_tolerance_nm=1e-6,trajectory_change_floor_mps=1e-6)

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,
        default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item())+'\n',encoding='utf8')

def verdict(e,reference):
    if not e['has_keeper_contact']:return 'SIN CONTACTO'
    if (e['physical_valid'] and reference and reference['physical_valid'] and reference['goal_detected']
            and not e['goal_detected'] and e['trajectory_changed']):return 'ATAJADA DEMOSTRADA'
    return 'CONTACTO SIN ATAJADA'

class Recorder:
    def __init__(self,output):
        self.output=output;self.rows=[];self.events=[];self.crossings=[];self.ready=False
        self.min_gap=10.;self.closest=None;self.capture_pending=False;self.max_speed=0.;self.max_excess=0.
        self.peak_torque=np.zeros(29);self.other_contacts=[]

    def bind(self,m,d):
        self.m=m;self.k=RobotIndex.resolve(m,'gk/');self.s=RobotIndex.resolve(m,'')
        self.bg=m.geom('ball_geom').id;self.ball=m.body('ball').id
        j=int(m.body_jntadr[self.ball]);self.bq=int(m.jnt_qposadr[j]);self.bv=int(m.jnt_dofadr[j])
        self.physical=[g for g in self.k.geoms if m.geom_contype[g] or m.geom_conaffinity[g]]
        self.caps=np.array(json.loads((self.output/'composition.json').read_text())['keeper_effective_caps_nm'])
        self.ready=True

    def step(self,m,d,original,*args,**kwargs):
        if not self.ready:self.bind(m,d)
        t=float(d.time);p=d.qpos[self.bq:self.bq+3].copy();v=d.qvel[self.bv:self.bv+3].copy()
        result=original(m,d,*args,**kwargs)
        after=d.qpos[self.bq:self.bq+3].copy();va=d.qvel[self.bv:self.bv+3].copy()
        impulse=np.zeros(3);peak=0.
        for i,c in enumerate(d.contact):
            a,b=map(int,c.geom);force=np.zeros(6);mujoco.mj_contactForce(m,d,i,force)
            if force[0]<=.001:continue
            if a in self.k.geoms or b in self.k.geoms:
                kg=a if a in self.k.geoms else b;other=b if kg==a else a
                if other!=self.bg and not (m.geom(other).name=='floor' and kg in self.k.foot_geoms):
                    self.other_contacts.append(dict(solver_s=t,geoms=[m.geom(a).name,m.geom(b).name],force_n=float(force[0])))
            if self.bg not in (a,b):continue
            other=b if a==self.bg else a
            if other not in self.k.geoms:continue
            fw=c.frame.reshape(3,3).T@force[:3]*(1 if b==self.bg else -1)
            impulse+=fw*.002;peak=max(peak,float(force[0]))
            self.events.append(dict(solver_s=t,after_step_s=float(d.time),geoms=[m.geom(a).name,m.geom(b).name],
                keeper_body=m.body(int(m.geom_bodyid[other])).name,contact_position_w=c.pos.copy(),
                gap_m=float(c.dist),normal_force_n=float(force[0]),force_on_ball_w=fw,step_impulse_on_ball_Ns=fw*.002,
                ball_position_before_w=p.copy(),ball_position_after_w=after.copy(),
                ball_velocity_before_w=v.copy(),ball_velocity_after_w=va.copy()))
            if len(self.events)==1:self.capture_pending=True
        # mj_step leaves derived geometry and solver contacts at this solver time.
        gaps=[(float(mujoco.mj_geomDistance(m,d,self.bg,g,10.,None)),g) for g in self.physical]
        gap,g=min(gaps)
        if gap<self.min_gap:
            self.min_gap=gap;self.closest=dict(solver_s=t,surface_gap_m=gap,body=m.body(int(m.geom_bodyid[g])).name)
        for plane in (4.,4.2,5.):
            point=crossing(p,after,plane)
            if point is not None:
                u=(plane-p[0])/(after[0]-p[0])
                self.crossings.append(dict(plane_x=plane,time_s=t+u*.002,position_w=point,
                    velocity_interpolated_w=v+u*(va-v),inside_goal=bool(plane==5 and abs(point[1])<=1.5 and 0<=point[2]<=1.8)))
        self.max_speed=max(self.max_speed,float(abs(d.qvel[self.k.dofs]).max()))
        q=d.qpos[self.k.qpos];limits=m.jnt_range[self.k.joints]
        self.max_excess=max(self.max_excess,float(np.maximum(limits[:,0]-q,q-limits[:,1]).max()))
        self.peak_torque=np.maximum(self.peak_torque,abs(d.qfrc_actuator[self.k.dofs]))
        self.rows.append(np.r_[t,p,v,after,va,impulse,peak,gap])
        return result

    def finish(self,report,reference):
        goal=any(c['inside_goal'] for c in self.crossings)
        inherited=('complete','finite','no_external_forces','foot_ball','no_file_changes','no_warnings',
            'shooter_no_fall','single_keeper_pd','standing','no_persistent_saturation','normalizer_frozen')
        checks={n:bool(report['checks'].get(n,False)) for n in inherited}
        checks.update(no_unexpected_keeper_contacts=not self.other_contacts,
            joint_speed=self.max_speed<=CRITERIA['max_joint_speed_rad_s'],joint_excess=self.max_excess<=CRITERIA['max_joint_excess_rad'],
            penetration=report['max_keeper_penetration_m']<=CRITERIA['max_penetration_m'],
            torques=bool(np.all(self.peak_torque<=self.caps+CRITERIA['torque_tolerance_nm'])))
        physical_valid=all(checks.values()) and report['failure'] is None
        delta=max((float(np.linalg.norm(e['ball_velocity_after_w']-e['ball_velocity_before_w'])) for e in self.events),default=0.)
        e=dict(physical_valid=physical_valid,has_keeper_contact=bool(self.events),goal_detected=goal,
            trajectory_changed=delta>CRITERIA['trajectory_change_floor_mps'])
        # Same scoring function as the existing experiments, with full-window goal evidence.
        trial=dict(evaluation=dict(first_foot_ball=report['first_foot_ball'],foot_peak_force_n=report['first_foot_ball']['force_contact'][0] if report['first_foot_ball'] else 0,
            goal_detected=goal,first_keeper_ball=self.events[0] if self.events else None,
            keeper_peak_contact_force_n=max((x['normal_force_n'] for x in self.events),default=0.)))
        probe=dict(evaluation=dict(goal_detected=bool(reference and reference['goal_detected']),goal_crossing_measured=reference.get('goal_crossings') if reference else None))
        score=classify(trial,probe)
        out=e|dict(status=verdict(e,reference),official_classifier=score,
            official_result='GOAL' if goal else 'SAVE' if physical_valid and score=='save_with_contact_and_goal_counterfactual' and e['trajectory_changed'] else 'UNRESOLVED',
            checks=checks,criteria=CRITERIA,placement=report['placement'],steps=report['steps'],simulated_s=report['simulated_s'],
            first_foot_ball=report['first_foot_ball'],plane_crossings=self.crossings,goal_crossings=[c for c in self.crossings if c['plane_x']==5],
            first_keeper_ball=self.events[0] if self.events else None,contact_samples=len(self.events),
            peak_normal_contact_force_n=max((x['normal_force_n'] for x in self.events),default=0.),
            total_impulse_on_ball_w_Ns=sum((x['step_impulse_on_ball_Ns'] for x in self.events),np.zeros(3)),
            max_contact_step_velocity_change_mps=delta,minimum_ball_keeper_distance=self.closest,
            max_joint_speed_rad_s=self.max_speed,max_joint_excess_rad=self.max_excess,
            actual_torque_peak_nm=self.peak_torque,torque_caps_nm=self.caps,unexpected_contacts=self.other_contacts,
            failure=report['failure'],loop_wall_s=report['loop_wall_s'],total_wall_s=report['total_wall_s'],
            note='Trajectory change at contact is measured, not an isolated impulse estimate; includes simultaneous floor forces. Full window required.')
        return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('deploy','loco-deploy','policy-python','output'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--placement',choices=('aside','center'),default='center');p.add_argument('--reference',type=Path)
    p.add_argument('--viewer',action='store_true');p.add_argument('--capture',action='store_true')
    p.add_argument('--camera',choices=('behind','execution','overview','goal','follow'),default='goal')
    a=p.parse_args();a.output=a.output.resolve()
    reference=json.loads(a.reference.read_text()) if a.reference else None
    original=PROJECT/'experiments/free_keeper_stadium_h1/run.py'
    spec=importlib.util.spec_from_file_location('experiments.free_keeper_stadium_h1.private_h3a',original)
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    recorder=Recorder(a.output)
    class Observer:
        def __getattr__(self,name):return getattr(mujoco,name)
        def mj_step(self,m,d,*args,**kwargs):return recorder.step(m,d,mujoco.mj_step,*args,**kwargs)
    class Presenter(FreeKeeperPresenter):
        def overlay(self):
            s=self.status
            left='HITO 3A CENTRAL\nEstado\nContacto arquero\nTiempo simulado'
            right=f'EQUILIBRIO SIN MANIOBRA\n{s.get("phase","READY")}\n{"SI" if recorder.events else "NO"}\n{self.runtime.data.time:.2f} s'
            self.handle.set_texts((self.mj.mjtFontScale.mjFONTSCALE_100,self.mj.mjtGridPos.mjGRID_TOPLEFT,left,right))
        def after_step(self):
            super().after_step()
            if a.capture and recorder.capture_pending:
                recorder.capture_pending=False;self.render_views('first_keeper_contact')
    # Presentation is imported inside H1.main: replace only the private import target temporarily.
    import experiments.free_keeper_stadium_h1.presentation as presentation
    old=presentation.FreeKeeperPresenter;presentation.FreeKeeperPresenter=Presenter
    engine.mujoco=Observer();argv=sys.argv
    sys.argv=[str(original),'--deploy',str(a.deploy),'--loco-deploy',str(a.loco_deploy),
        '--policy-python',str(a.policy_python),'--output',str(a.output),'--placement',a.placement,'--action','center','--camera',a.camera]
    if a.viewer:sys.argv.append('--viewer')
    if a.capture:sys.argv.append('--capture')
    try:engine.main()
    finally:sys.argv=argv;presentation.FreeKeeperPresenter=old
    r=json.loads((a.output/'report.json').read_text())
    if not recorder.ready:
        dump(a.output/'interception.json',dict(physical_valid=False,status='SIN CONTACTO',failure=r['failure']));return 2
    result=recorder.finish(r,reference)
    dump(a.output/'interception.json',result);dump(a.output/'ball_keeper_contacts.json',recorder.events)
    dump(a.output/'h3a_sources.json',{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('run.py',)})
    np.savez_compressed(a.output/'interception_trace.npz',samples=np.asarray(recorder.rows))
    print(json.dumps({k:result[k] for k in ('status','official_result','physical_valid','contact_samples','peak_normal_contact_force_n','failure')},indent=2))
    return 0 if result['physical_valid'] else 2

if __name__=='__main__':raise SystemExit(main())
