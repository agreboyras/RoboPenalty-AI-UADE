"""Private H3B/H1 driver with read-only 50 Hz shadow instrumentation."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import mujoco
from experiments.central_block_h3a.run import Recorder, dump
from experiments.passive_coverage_h3b.run import ACTIONS, category, validate_reference
from experiments.free_keeper_stadium_h1.presentation import FreeKeeperPresenter
from .agent import Agent, Observation

PROJECT = bootstrap.PROJECT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('deploy','loco-deploy','policy-python','output','reference','baseline'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--action',choices=ACTIONS,required=True)
    p.add_argument('--viewer',action='store_true')
    p.add_argument('--camera',choices=('behind','execution','overview','goal','follow'),default='goal')
    a=p.parse_args(); a.output=a.output.resolve()
    calibration=json.loads((PROJECT/'phase8c/catalog_v1.json').read_text())['actions'][a.action]['sha256']
    reference=json.loads(a.reference.read_text());validate_reference(reference,a.action,calibration)
    baseline=json.loads((a.baseline/'interception.json').read_text())
    if baseline['action']!=a.action or baseline['placement']!='center' or baseline['calibration_sha256']!=calibration:
        raise ValueError('Baseline must be centered, identical action/calibration')
    path=PROJECT/'experiments/free_keeper_stadium_h1/run.py'
    spec=importlib.util.spec_from_file_location('experiments.free_keeper_stadium_h1.private_h4a',path)
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    recorder=Recorder(a.output);agent=Agent();sample_count=0;readonly=True
    class Observer:
        resolved=False
        def __getattr__(self,name): return getattr(mujoco,name)
        def mj_step(self,m,d,*args,**kwargs):
            nonlocal sample_count,readonly
            if not recorder.ready:recorder.bind(m,d)
            if sample_count%10==0:
                k=recorder.k;j=int(m.body_jntadr[k.pelvis]);q=int(m.jnt_qposadr[j])
                pos=tuple(float(v) for v in d.qpos[recorder.bq:recorder.bq+3])
                vel=tuple(float(v) for v in d.qvel[recorder.bv:recorder.bv+3])
                phase='PREPARING' if agent.detected_s is None and vel[0]<=.5 else 'SHOOTING'
                # Current/past events only; latch so rebounds are not new penalties.
                if agent.detected_s is not None and (recorder.events or pos[0]>=4.2 or vel[0]<=.05):self.resolved=True
                if self.resolved:phase='RESOLVING'
                obs=Observation(float(d.time),pos,vel,tuple(d.qpos[q:q+3]),tuple(d.qpos[q+3:q+7]),phase)
                flag=mujoco.mjtState.mjSTATE_INTEGRATION
                before=np.empty(mujoco.mj_stateSize(m,flag));mujoco.mj_getState(m,d,before,flag)
                agent.observe(obs)
                after=np.empty_like(before);mujoco.mj_getState(m,d,after,flag)
                readonly=readonly and np.array_equal(before,after)
                if not readonly:raise RuntimeError('Shadow agent modified integration state')
            sample_count+=1
            return recorder.step(m,d,mujoco.mj_step,*args,**kwargs)
    class Presenter(FreeKeeperPresenter):
        def overlay(self):
            row=agent.history[-1] if agent.history else None
            prediction=row['prediction'] if row else {}
            left='H4A SHADOW: NO CONTROL\nFase observada\nRecomendacion\nY prevista\nETA\nMotivo'
            right='SOLO OBSERVACION\n'+(row['observation']['phase'] if row else 'READY')+'\n'+(row['action'] if row else '-')
            right+='\n'+str(prediction.get('y_w'))+'\n'+str(prediction.get('eta_s'))+'\n'+('Sin capacidad lateral validada' if row and row['action']=='SIN_ACCION_VIABLE' else 'Similitud central nominal, sin garantia')
            self.handle.set_texts((self.mj.mjtFontScale.mjFONTSCALE_100,self.mj.mjtGridPos.mjGRID_TOPLEFT,left,right))
    import experiments.free_keeper_stadium_h1.presentation as presentation
    old=presentation.FreeKeeperPresenter;presentation.FreeKeeperPresenter=Presenter
    engine.mujoco=Observer();argv=sys.argv
    sys.argv=[str(path),'--deploy',str(a.deploy),'--loco-deploy',str(a.loco_deploy),'--policy-python',str(a.policy_python),
        '--output',str(a.output),'--placement','center','--action',a.action,'--camera',a.camera]
    if a.viewer:sys.argv.append('--viewer')
    try:engine.main()
    finally:sys.argv=argv;presentation.FreeKeeperPresenter=old
    dump(a.output/'shadow_decisions.json',agent.history)
    report=json.loads((a.output/'report.json').read_text())
    if not recorder.ready:return 2
    result=recorder.finish(report,reference)
    result.update(action=a.action,calibration_sha256=calibration,category=category(result,reference))
    dump(a.output/'interception.json',result);dump(a.output/'ball_keeper_contacts.json',recorder.events)
    np.savez_compressed(a.output/'interception_trace.npz',samples=np.asarray(recorder.rows))
    with np.load(a.baseline/'trace.npz') as b,np.load(a.output/'trace.npz') as s:
        exact={k:bool(np.array_equal(b[k],s[k])) for k in b.files}
    with np.load(a.baseline/'interception_trace.npz') as b:
        exact['contact_geometry_samples']=bool(np.array_equal(b['samples'],np.asarray(recorder.rows)))
    # Full contact JSON includes forces, identities, positions and solver timestamps.
    baseline_contacts=json.loads((a.baseline/'ball_keeper_contacts.json').read_text())
    exact['keeper_contacts']=baseline_contacts==json.loads((a.output/'ball_keeper_contacts.json').read_text())
    exact['result']=baseline['official_result']==result['official_result'] and baseline['category']==result['category']
    valid=[r for r in agent.history if r['prediction']['valid'] and r['observation']['phase']=='SHOOTING']
    # Latest causal decision before contact/plane; hindsight only selects reporting row.
    end=min([e['solver_s'] for e in recorder.events]+[c['time_s'] for c in recorder.crossings if c['plane_x']==4.2]+[14.])
    incoming=[r for r in valid if r['observation']['time_s']<end]
    chosen=incoming[-1] if incoming else None
    crossing=next((c for c in recorder.crossings if c['plane_x']==4.2),None)
    untouched=next((c for c in reference['plane_crossings'] if c['plane_x']==4.2),None)
    def errors(target):
        if target is None:return None
        rows=[]
        for r in incoming:
            pr=r['prediction'];t=r['observation']['time_s']
            rows.append(dict(observation_s=t,y_error_m=pr['y_w']-target['position_w'][1],
                z_error_m=None if pr['z_w'] is None else pr['z_w']-target['position_w'][2],
                arrival_error_s=t+pr['eta_s']-target['time_s']))
        return rows
    crossed_before_contact=crossing is not None and (not recorder.events or crossing['time_s']<recorder.events[0]['solver_s'])
    summary=dict(action=a.action,detected_s=agent.detected_s,
        detection_latency_s=None if agent.detected_s is None else agent.detected_s-report['first_foot_ball']['solver_time_s'],
        latest_incoming=chosen,physical_result=result['official_result'],category=result['category'],
        physical_valid=result['physical_valid'],readonly_state=readonly,exact_baseline=exact,
        # Contacts can prevent a crossing or change the target: never call this model error.
        actual_unobstructed_errors=errors(crossing) if crossed_before_contact else None,
        actual_error_limitation=None if crossed_before_contact else 'Contact before plane: unobstructed prediction cannot be scored against deflected or absent crossing',
        counterfactual_aside_errors=errors(untouched),
        counterfactual_note='Historical paired aside trajectory, used AFTER episode only; never supplied to agent',
        first_valid=incoming[0] if incoming else None,decisions=len(agent.history),steps=report['steps'])
    dump(a.output/'summary.json',summary)
    print(json.dumps(dict(action=a.action,recommendation=chosen['action'] if chosen else None,exact=exact,physical_valid=result['physical_valid']),indent=2))
    return 0 if result['physical_valid'] and readonly and all(exact.values()) else 2


if __name__=='__main__':raise SystemExit(main())
