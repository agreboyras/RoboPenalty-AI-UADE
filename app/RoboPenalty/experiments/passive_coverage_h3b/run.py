"""H1 physical driver + unchanged H3A contact recorder, for the five 8C actions."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
import mujoco
from experiments.central_block_h3a.run import Recorder,dump
from experiments.free_keeper_stadium_h1.presentation import FreeKeeperPresenter

PROJECT=bootstrap.PROJECT
ACTIONS=('center','left_near_b060','right_inter_m080','right_open_m100','right_corner_m140')

def category(e,reference):
    if not e['physical_valid']:return 'RESULTADO NO CONCLUYENTE'
    if not e['has_keeper_contact']:return 'SIN CONTACTO'
    if e['goal_detected']:return 'CONTACTO SIN ATAJADA'
    if reference and reference['physical_valid'] and reference['goal_detected'] and e['trajectory_changed']:
        return 'ATAJADA'
    return 'RESULTADO NO CONCLUYENTE'

def validate_reference(ref,action,calibration):
    if ref.get('action')!=action or ref.get('placement')!='aside' or ref.get('calibration_sha256')!=calibration:
        raise ValueError('La referencia debe ser apartada, de la misma accion y calibracion exacta.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('deploy','loco-deploy','policy-python','output'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--action',choices=ACTIONS,required=True);p.add_argument('--placement',choices=('aside','center'),default='center')
    p.add_argument('--reference',type=Path);p.add_argument('--viewer',action='store_true');p.add_argument('--capture',action='store_true')
    p.add_argument('--camera',choices=('behind','execution','overview','goal','follow'),default='goal')
    a=p.parse_args();a.output=a.output.resolve()
    catalog=json.loads((PROJECT/'phase8c/catalog_v1.json').read_text());calibration=catalog['actions'][a.action]['sha256']
    reference=json.loads(a.reference.read_text()) if a.reference else None
    if reference:validate_reference(reference,a.action,calibration)
    path=PROJECT/'experiments/free_keeper_stadium_h1/run.py'
    spec=importlib.util.spec_from_file_location('experiments.free_keeper_stadium_h1.private_h3b',path)
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    recorder=Recorder(a.output)
    class Observer:
        def __getattr__(self,name):return getattr(mujoco,name)
        def mj_step(self,m,d,*args,**kwargs):return recorder.step(m,d,mujoco.mj_step,*args,**kwargs)
    class Presenter(FreeKeeperPresenter):
        def overlay(self):
            s=self.status
            left='HITO 3B COBERTURA PASIVA\nTiro\nEstado\nContacto\nTiempo'
            right=f'SIN MANIOBRA\n{a.action}\n{s.get("phase","READY")}\n{"SI" if recorder.events else "NO"}\n{self.runtime.data.time:.2f} s'
            self.handle.set_texts((self.mj.mjtFontScale.mjFONTSCALE_100,self.mj.mjtGridPos.mjGRID_TOPLEFT,left,right))
        def after_step(self):
            super().after_step()
            if a.capture and recorder.capture_pending:
                recorder.capture_pending=False;self.render_views('first_keeper_contact')
    import experiments.free_keeper_stadium_h1.presentation as presentation
    old=presentation.FreeKeeperPresenter;presentation.FreeKeeperPresenter=Presenter;engine.mujoco=Observer();argv=sys.argv
    sys.argv=[str(path),'--deploy',str(a.deploy),'--loco-deploy',str(a.loco_deploy),'--policy-python',str(a.policy_python),
        '--output',str(a.output),'--placement',a.placement,'--action',a.action,'--camera',a.camera]
    if a.viewer:sys.argv.append('--viewer')
    if a.capture:sys.argv.append('--capture')
    try:engine.main()
    finally:sys.argv=argv;presentation.FreeKeeperPresenter=old
    r=json.loads((a.output/'report.json').read_text())
    if not recorder.ready:
        dump(a.output/'interception.json',dict(action=a.action,physical_valid=False,category='RESULTADO NO CONCLUYENTE',failure=r['failure']));return 2
    result=recorder.finish(r,reference)
    result.update(action=a.action,calibration_sha256=calibration,category=category(result,reference),
        verification_scope='Single nominal trial, repetitions/paired traces verified separately; no intelligent action selection')
    # Incoming distance excludes later rebounds from the existing box behind goal.
    samples=np.asarray(recorder.rows);foot=r['first_foot_ball']
    end=min((c['time_s'] for c in recorder.crossings if c['plane_x']==5.),default=14.)
    mask=(samples[:,0]>=(foot['solver_time_s'] if foot else 0))&(samples[:,0]<=end)&(samples[:,4]>.05)
    if mask.any():
        indices=np.flatnonzero(mask);i=int(indices[np.argmin(samples[mask,-1])])
        result['incoming_min_surface_gap_m']=float(samples[i,-1]);result['incoming_min_solver_s']=float(samples[i,0])
    else:result['incoming_min_surface_gap_m']=None
    dump(a.output/'interception.json',result);dump(a.output/'ball_keeper_contacts.json',recorder.events)
    dump(a.output/'h3b_sources.json',{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('run.py',)})
    np.savez_compressed(a.output/'interception_trace.npz',samples=samples)
    print(json.dumps({k:result[k] for k in ('action','category','official_result','physical_valid','contact_samples','incoming_min_surface_gap_m','failure')},indent=2))
    return 0 if result['physical_valid'] else 2

if __name__=='__main__':raise SystemExit(main())
