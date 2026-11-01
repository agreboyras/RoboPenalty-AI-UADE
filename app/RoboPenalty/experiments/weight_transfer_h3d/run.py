"""Only one free G1 and the original physical floor. No penalty is executable."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import mujoco
from experiments.free_keeper_stadium_h1.run import validate_resources
from experiments.free_keeper_stadium_h1.policy_client import PolicyClient
from experiments.low_block_h3c.run import policy_target
from experiments.central_block_h3a.run import dump
from .scene import build
from .support import Support

PROJECT=bootstrap.PROJECT
# Frozen before the first trial. Deadline uses H3B contact 0.914 s minus 0.040 s detection.
LIMITS=dict(duration_s=6.,steps=3000,dt=.002,settle_s=2.,deadline_after_start_s=.874,
    max_speed_rad_s=20.,abort_speed_rad_s=40.,max_penetration_m=.02,abort_penetration_m=.03,
    max_joint_excess_rad=.03,abort_joint_excess_rad=.10,max_saturation_s=.10,abort_saturation_s=.50,
    fall_height_m=.50,fall_tilt_deg=45.,partial_share=.30,partial_fraction_of_baseline_right=.65,
    minimum_left_weight_fraction=.55,sustained_s=.04,reference_speed_rad_s=1.5,reference_acc_rad_s2=20.)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('deploy','loco-deploy','policy-python','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mode',choices=('baseline','transfer'),default='baseline');p.add_argument('--viewer',action='store_true')
    a=p.parse_args();a.output=a.output.resolve();started=time.perf_counter()
    if a.output.exists() or not a.output.is_relative_to(PROJECT.parents[1]/'validation'):p.error('Use a NEW output in validation/')
    a.deploy=a.deploy.resolve();unitree=PROJECT.parent/'unitree_mujoco';before=validate_resources(a.deploy,unitree)
    a.output.mkdir(parents=True);client=handle=None;failure=None;fall=None;plan=None;completed=0;loop_wall=None
    arrays={n:[] for n in ('time','qpos','qvel','requested','sent','actual_torque','base','residual','target','pelvis','root_velocity','tilt','com','cop','margin','load','clearance','point','knee','ankle')}
    events=[];unexpected_events=[];decisions=[];sat=np.zeros(29,dtype=int);longest=0.;maxpen=speed=excess=0.;pre_ok=True;external=False;clips=0
    try:
        client=PolicyClient(a.policy_python.resolve(),a.loco_deploy.resolve(),a.output,PROJECT);meta=client.metadata
        m,d,k,qa,va,caps,checks=build(a.deploy,unitree,np.array(meta['home']),meta['limits'])
        names=[m.joint(int(j)).name.removeprefix('gk/') for j in k.joints]
        if names!=list(meta['joints']) or meta['recurrent_reset_max']!=0 or meta['physical_velocity_command']!=[0,0,0]:raise ValueError('Policy contract mismatch')
        measure=Support(m,k);base=np.array(meta['home']);kp=np.array(meta['kp']);kd=np.array(meta['kd']);origin=d.qpos[qa:qa+3].copy()
        if a.mode!='baseline':
            from .maneuver import Transfer
            plan=Transfer(names,a.mode,measure.weight)
        dump(a.output/'configuration.json',dict(mode=a.mode,limits=LIMITS,scene_checks=checks,policy=meta,caps_nm=caps,initial_qpos=d.qpos.copy(),
            mass_kg=measure.mass,weight_n=measure.weight,removed='striker, ball, goal, rear box; their original files are unchanged',
            floor_friction=m.geom_friction[m.geom('floor').id],floor_solref=m.geom_solref[m.geom('floor').id],floor_solimp=m.geom_solimp[m.geom('floor').id]))
        if a.viewer:
            from mujoco import viewer
            handle=viewer.launch_passive(m,d,show_left_ui=False,show_right_ui=False)
            with handle.lock():
                handle.cam.lookat[:]=[4.2,0,.6];handle.cam.distance=2.5;handle.cam.azimuth=180;handle.cam.elevation=-15
        last=None;loopstart=time.perf_counter()
        for step in range(LIMITS['steps']):
            t=float(d.time)
            if handle and not handle.is_running():raise RuntimeError('Viewer closed early')
            if np.any(d.xfrc_applied) or np.any(d.qfrc_applied):external=True;raise RuntimeError('External force')
            if step%10==0:
                reply=client.request('observe',q=d.qpos[k.qpos].tolist(),dq=d.qvel[k.dofs].tolist(),quaternion=d.qpos[qa+3:qa+7].tolist(),omega=d.qvel[va+3:va+6].tolist())
                raw,base=policy_target(reply['target'],m.jnt_range[k.joints]);clips+=int(np.count_nonzero(raw!=base));decisions.append(np.r_[t,reply['observation'],raw,base])
                if plan is not None:
                    plan.observe(t,last,arrays)
            residual=plan.residual(t) if plan is not None else np.zeros(29);target=base+residual
            if np.any(target<m.jnt_range[k.joints,0]) or np.any(target>m.jnt_range[k.joints,1]):raise RuntimeError('Reference outside native joint range')
            requested=kp*(target-d.qpos[k.qpos])-kd*d.qvel[k.dofs];d.ctrl[k.actuators]=np.clip(requested,-caps,caps)
            sat=np.where(abs(requested)>=caps,sat+1,0);longest=max(longest,float(sat.max()*.002))
            q=d.qpos.copy();v=d.qvel.copy();sent=d.ctrl[k.actuators].copy();mujoco.mj_step(m,d);completed+=1
            info=measure.sample(d,t);last=info;events.extend(info['contacts']);unexpected_events.extend(info['unexpected']);maxpen=max(maxpen,info['maxpen'])
            speed=max(speed,float(abs(d.qvel[k.dofs]).max()));limits=m.jnt_range[k.joints]
            excess=max(excess,float(np.maximum(limits[:,0]-d.qpos[k.qpos],d.qpos[k.qpos]-limits[:,1]).max()))
            qw,qx,qy,qz=q[qa+3:qa+7];tilt=float(np.degrees(np.arccos(np.clip(1-2*(qx*qx+qy*qy),-1,1))))
            if fall is None and (q[qa+2]<.5 or tilt>=45.):fall=t
            if plan is None or plan.start is None:
                pre_ok &= q[qa+2]>=.5 and tilt<15 and np.linalg.norm(q[qa:qa+2]-origin[:2])<.1
                if not pre_ok:raise RuntimeError('Initial standing criterion failed')
            values=dict(time=t,qpos=q,qvel=v,requested=requested.copy(),sent=sent,actual_torque=d.qfrc_actuator[k.dofs].copy(),
                base=base.copy(),residual=residual,target=target.copy(),pelvis=q[qa:qa+3],root_velocity=v[va:va+3],tilt=tilt,
                com=info['com'],cop=info['cop'],margin=info['com_margin_m'] if info['com_margin_m'] is not None else np.nan,
                load=info['load'],clearance=info['clearance'],point=info['point'],knee=info['knee'],ankle=info['ankle'])
            for key,value in values.items():arrays[key].append(value)
            if not np.isfinite(d.qpos).all() or not np.isfinite(d.qvel).all():raise FloatingPointError('Nonfinite state')
            if maxpen>.03 or speed>40. or excess>.10 or longest>=.5:raise RuntimeError('Physical safety interruption')
            if handle and step%16==0:
                state=plan.state if plan is not None else 'BALANCE'
                left='HITO 3D SIN PELOTA\nEstado\nPie izq N\nPie der N\nTiempo'
                right=f'BASE LIBRE\n{state}\n{info["load"][0]:.1f}\n{info["load"][1]:.1f}\n{t:.2f} s'
                handle.set_texts((mujoco.mjtFontScale.mjFONTSCALE_100,mujoco.mjtGridPos.mjGRID_TOPLEFT,left,right));handle.sync()
            if handle:time.sleep(max(0.,loopstart+completed*.002-time.perf_counter()))
        loop_wall=time.perf_counter()-loopstart
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        import traceback
        (a.output/'error.txt').write_text(traceback.format_exc(),encoding='utf8')
    finally:
        if handle:handle.close()
        if client:client.close(force=failure is not None)
    ar={n:np.asarray(v) for n,v in arrays.items()};np.savez_compressed(a.output/'trace.npz',**ar,decisions=np.asarray(decisions))
    dump(a.output/'contacts.json',events)
    if plan is not None:dump(a.output/'planner.json',dict(events=plan.events,start=plan.start,baseline=plan.baseline,protocol=plan.protocol))
    if not len(ar['time']):
        dump(a.output/'report.json',dict(mode=a.mode,physical_valid=False,steps=completed,failure=failure));return 2
    finite=bool(np.isfinite(ar['qpos']).all() and np.isfinite(ar['qvel']).all());warn={str(i):x.number for i,x in enumerate(d.warning) if x.number}
    torque_ok=bool(np.all(abs(ar['actual_torque'])<=caps+1e-6))
    clean=all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in before.items())
    invalid_contacts=[e for e in unexpected_events if not (plan is not None and plan.start is not None and e['t']>=plan.start and 'floor' in e['geoms'])]
    valid=completed==3000 and finite and not external and not warn and clean and torque_ok and speed<=20 and excess<=.03 and maxpen<=.02 and longest<.1 and pre_ok and not invalid_contacts and failure is None
    stable=(ar['time']>=1.5)&(ar['time']<2.);fz=ar['load'][stable];share=fz[:,1]/np.maximum(fz.sum(axis=1),1.)
    summary=dict(mode=a.mode,physical_valid=bool(valid),steps=completed,simulated_s=completed*.002,failure=failure,pre_standing=bool(pre_ok),
        baseline_left_n_mean=float(fz[:,0].mean()),baseline_right_n_mean=float(fz[:,1].mean()),baseline_right_share_mean=float(share.mean()),
        baseline_com_mean=ar['com'][stable].mean(axis=0),baseline_cop_mean=ar['cop'][stable].mean(axis=0),baseline_min_com_margin_m=float(np.nanmin(ar['margin'][stable])),
        max_tilt_deg=float(ar['tilt'].max()),min_pelvis_height_m=float(ar['pelvis'][:,2].min()),max_pelvis_drift_m=float(np.linalg.norm(ar['pelvis'][:,:2]-origin[:2],axis=1).max()),
        max_penetration_m=maxpen,max_joint_speed_rad_s=speed,max_joint_excess_rad=excess,max_saturation_s=longest,fall_time_s=fall,
        torques_within_caps=torque_ok,normalizer_frozen=bool(getattr(client,'final',{}).get('normalizer_unchanged',False)),source_files_unchanged=clean,
        warnings=warn,reference_clips=clips,invalid_contacts=invalid_contacts,nonfoot_contact_events=len(unexpected_events),loop_wall_s=loop_wall,total_wall_s=time.perf_counter()-started,
        timing_note='All array states, COM and solver contacts are pre-integration at time t. Control feedback uses preceding force sample.',
        support_warning='COM inside the contact hull is a geometric diagnostic, not proof of dynamic stability.')
    summary['physical_valid'] &= summary['normalizer_frozen']
    dump(a.output/'report.json',summary);print(json.dumps(summary,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item()))
    return 0 if summary['physical_valid'] else 2

if __name__=='__main__':raise SystemExit(main())
