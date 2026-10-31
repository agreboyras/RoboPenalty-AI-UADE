"""Private laboratory entrypoint; no public launcher imports this experiment."""
from . import bootstrap
import argparse,json,time
from pathlib import Path
import numpy as np
import mujoco
from .geometry import world,initial_posture,geometric_map,reach_probe
from .posture_targets import ReachPosturePD,effective_caps
from .metrics import MotorMonitor
from phase8b3.posture import PosturePD
from lateral_control import LateralControl
from lateral_scene import Limits


def no_ball(enabled,side,output,observer=None):
    m,d,s,k,rail,software=world();base=initial_posture(m,k)
    # Initial conditions only. The ball and idle shooter remain >20m away;
    # they are not removed or teleported after stepping begins.
    for name,x in (('ball',-30.),('pelvis',-20.)):
        j=int(m.body_jntadr[m.body(name).id]);q=int(m.jnt_qposadr[j]);d.qpos[q]=x
    d.qpos[k.qpos]=base;mujoco.mj_forward(m,d)
    pd=ReachPosturePD(m,k,rail,fixture_side=side) if enabled else PosturePD(m,k,rail)
    caps=effective_caps(m,k,software);shooter_caps=effective_caps(m,s,software)
    monitor=MotorMonitor(m,k,rail,caps);control=LateralControl(Limits(),rail)
    snapshots={};start=time.perf_counter()
    initial=d.qpos.tolist();initial_v=d.qvel.tolist()
    shoot_ref=d.qpos[s.qpos].copy();targets=(1.98,2.70,3.50,4.98,6.50,9.98)
    if observer is not None:observer.bind(m,d,k,rail,pd)
    for step in range(5000):
        torque=pd.command(d,base,software)
        control.select(0.);control.advance_reference(m.opt.timestep)
        d.ctrl[k.actuators]=torque
        d.ctrl[s.actuators]=np.clip(70*(shoot_ref-d.qpos[s.qpos])-5*d.qvel[s.dofs],-shooter_caps,shooter_caps)
        d.ctrl[rail.actuator]=control.force(float(d.qpos[rail.qpos]),float(d.qvel[rail.dof]))
        mujoco.mj_step(m,d);monitor.sample(d,pd.reference,pd.velocity,torque)
        if observer is not None:observer.after_step()
        for target in targets:
            key=f'{target:.2f}'
            if key not in snapshots and d.time>=target-1e-9:
                snapshots[key]=dict(time_s=float(d.time),qpos=d.qpos.tolist(),qvel=d.qvel.tolist(),
                    ctrl=d.ctrl.tolist(),reference=pd.reference.tolist())
                # Live viewing records states, but does not stop rendering to scan
                # hundreds of auxiliary sphere placements. Offline behavior is unchanged.
                if observer is None:snapshots[key]['reach']=reach_probe(m,d,k)
    measured=monitor.summary();posture=pd.summary()
    final_error=float(abs(d.qpos[k.qpos]-np.array(snapshots['1.98']['qpos'])[k.qpos]).max())
    passed=(posture['passed'] and measured['torques_within_caps'] and not measured['persistent_saturation']
            and measured['peak_speed_rad_s']<=3. and measured['joint_range_violation_rad']<=.02
            and measured['pelvis_error_m']<=.001 and final_error<=.03)
    result=dict(experimental=enabled,side=side,fixture='Timed reference 2..5s; not an autonomous save',
        ball_absent_from_test_zone=True,initial_qpos=initial,initial_qvel=initial_v,steps=5000,simulated_s=float(d.time),
        wall_s=time.perf_counter()-start,posture=posture,motors=measured,snapshots=snapshots,
        recovery_error_vs_pre_maneuver_rad=final_error,passed=passed)
    output.write_text(json.dumps(result),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',choices=('map','no-ball','nominal'),required=True)
    p.add_argument('--experimental',action='store_true',help='Explicit opt-in; never used by public modes')
    p.add_argument('--side',choices=('LEFT','RIGHT'),default='LEFT');p.add_argument('--action',default='right_inter_m080')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(bootstrap.PROJECT) or out.exists():p.error('Choose a NEW output path inside this RoboPenalty copy')
    out.parent.mkdir(parents=True,exist_ok=True)
    if a.case=='map':
        result=geometric_map();out.write_text(json.dumps(result),encoding='utf-8')
    elif a.case=='no-ball':
        result=no_ball(a.experimental,a.side,out)
        if not result['passed']:raise RuntimeError('No-ball trial failed; do not proceed to ball trials')
    else:
        from phase8c.catalog import Catalog
        from .runtime import components
        catalog=Catalog(bootstrap.PROJECT/'phase8c/catalog_v1.json')
        if a.action not in catalog.actions:p.error('Action not in the unchanged 8C catalog')
        Runtime,_=components(catalog,experimental=a.experimental);runtime=Runtime()
        result,selection,wall=runtime.execute('long','agent',out,lambda observation:a.action,lambda:None)
        label,error=runtime.evaluate(result,'long',a.action)
        out.parent.joinpath('trial_outcome.json').write_text(json.dumps(dict(action=a.action,outcome=label,error=error,
            experimental=a.experimental,wall_s=wall)),encoding='utf-8')
    print('Completed',a.case,'experimental',a.experimental,'output',out)


if __name__=='__main__':main()
