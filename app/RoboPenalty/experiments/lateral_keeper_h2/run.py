"""Isolated manual maneuver, original H1 world, original shot, no agent decisions."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import mujoco
import yaml
from experiments.free_keeper_stadium_h1.scene import build
from experiments.free_keeper_stadium_h1.policy_client import PolicyClient
from experiments.free_keeper_stadium_h1.run import validate_resources,actuator_caps,root_addresses,dump
from phase2.freekick_adapter import FreeKickAdapter
from phase4a.scenarios import initialize
from .maneuver import Maneuver,PROTOCOL
from .presentation import ManeuverPresenter
from phase6a.presentation import PresentationConfig

PROJECT=bootstrap.PROJECT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('deploy','loco-deploy','policy-python','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('balance','transfer','maneuver'),default='transfer')
    p.add_argument('--side',choices=('LEFT','RIGHT'),default='LEFT')
    p.add_argument('--viewer',action='store_true');p.add_argument('--capture',action='store_true')
    a=p.parse_args();started=time.perf_counter();a.output=a.output.resolve()
    if a.output.exists() or not a.output.is_relative_to(PROJECT.parents[1]/'validation'):p.error('New validation/ directory required')
    resources=validate_resources(a.deploy.resolve(),PROJECT.parent/'unitree_mujoco')
    a.output.mkdir(parents=True);client=None;presenter=None;failure=None
    rows=[];policy_rows=[];contacts=[];poses=[];ball_rows=[];control_writes=0
    maxpen=maxexcess=maxspeed=maxtilt=0.;sat=np.zeros(29,int);maxsat=np.zeros(29,int)
    max_ref_speed=max_ref_accel=0.;last_ref=None;last_dref=np.zeros(29)
    reference=None;handoff=None;ground_bodies=set();foot_impulse=np.zeros(3);external=False
    phases_saved=set();foot_ball=False;warnings={};loop_wall=None;metadata=None
    duration=3. if a.mode=='transfer' else 6.;count=round(duration/.002)
    try:
        client=PolicyClient(a.policy_python.resolve(),a.loco_deploy.resolve(),a.output,PROJECT)
        metadata=client.metadata;home=np.array(metadata['home']);kp=np.array(metadata['kp']);kd=np.array(metadata['kd'])
        if metadata['recurrent_reset_max']!=0:raise ValueError('Recurrent reset failed')
        model,data,shooter,keeper,checks=build(a.deploy.resolve(),PROJECT.parent/'unitree_mujoco',home,4.)
        kq,kv=root_addresses(model,keeper);caps=actuator_caps(model,keeper,metadata['limits'])
        names=[model.joint(int(j)).name.removeprefix('gk/') for j in keeper.joints]
        if names!=metadata['joints']:raise ValueError('Joint mapping mismatch')
        kick=FreeKickAdapter(a.deploy.resolve(),model,shooter)
        # Same physical right_inter_m080 as H1; keeper Y=4 avoids ball influence.
        catalog=json.loads((PROJECT/'phase8c/catalog_v1.json').read_text())
        action=catalog['actions']['right_inter_m080'];calibration=PROJECT/'phase8c'/action['probe']
        if hashlib.sha256(calibration.read_bytes()).hexdigest()!=action['sha256']:raise ValueError('Calibration mismatch')
        initialize(dict(translate_x=-2.,target_bias=action['bias']),model,data,kick,None,False)
        mujoco.mj_forward(model,data)
        floor=model.geom('floor').id;bg=model.geom('ball_geom').id;ball=model.body('ball').id
        bj=int(model.body_jntadr[ball]);bq=int(model.jnt_qposadr[bj]);bv=int(model.jnt_dofadr[bj])
        slim=np.array(yaml.safe_load((a.deploy/'deploy_mujoco/config/mujoco_freekick.yaml').read_text())['tau_limit'])
        wrists=[model.body('gk/'+s+'_wrist_yaw_link').id for s in ('left','right')]
        shoulders=[model.body('gk/'+s+'_shoulder_roll_link').id for s in ('left','right')]
        initial_positions=np.vstack([data.xpos[keeper.pelvis],data.xpos[wrists],data.xpos[shoulders]])
        target=home.copy();ref=target.copy();planner=Maneuver(names,a.side,a.mode,model.jnt_range[keeper.joints])
        signature=mujoco.mjtState.mjSTATE_INTEGRATION
        class World:
            engine=SimpleNamespace(mujoco=mujoco,np=np)
            def integration_state(self,d):
                state=np.empty(mujoco.mj_stateSize(model,signature));mujoco.mj_getState(model,d,state,signature);return state
        runtime=World();runtime.model=model;runtime.data=data
        presenter=ManeuverPresenter(runtime,PresentationConfig(enabled=a.viewer),a.output,'long',camera='keeper')
        presenter.set_status(dict(penalty=0,total=0,phase='BALANCE',side=a.side,owner='policy',goals=0,saves=0,misses=0))
        presenter.pause('ready',1.);presenter.begin_episode()
        dump(a.output/'configuration.json',dict(protocol=PROTOCOL,mode=a.mode,side=a.side,initial_positions=initial_positions.tolist(),
            checks=checks,metadata=metadata,caps=caps.tolist(),names=names,duration_s=duration))
        loop_start=time.perf_counter()
        for step in range(count):
            t=step*.002
            policy_owns=a.mode=='balance' or t<2.
            if np.any(data.xfrc_applied) or np.any(data.qfrc_applied):external=True;raise RuntimeError('External force')
            if policy_owns and step%10==0:
                reply=client.request('observe',q=data.qpos[keeper.qpos].tolist(),dq=data.qvel[keeper.dofs].tolist(),
                    quaternion=data.qpos[kq+3:kq+7].tolist(),omega=data.qvel[kv+3:kv+6].tolist())
                raw=np.array(reply['target']);target=np.clip(raw,model.jnt_range[keeper.joints,0],model.jnt_range[keeper.joints,1])
                policy_rows.append(np.r_[t,reply['observation'],raw,target])
            ref=planner.reference(t,target,data.qpos[keeper.qpos])
            if step==1000 and a.mode!='balance':
                handoff=dict(time_s=t,last_policy_reference=target.tolist(),first_owned_reference=ref.tolist())
                if a.mode=='maneuver':
                    dump(a.output/'trajectory_targets.json',dict(start=planner.start.tolist(),
                        prepare=planner.prepare.tolist(),push=planner.push.tolist(),extend=planner.extend.tolist(),names=names))
            if t>=2. and last_ref is not None and a.mode=='maneuver':
                dref=(ref-last_ref)/.002;acc=(dref-last_dref)/.002
                max_ref_speed=max(max_ref_speed,float(abs(dref).max()));max_ref_accel=max(max_ref_accel,float(abs(acc).max()))
                last_dref=dref.copy()
            last_ref=ref.copy()
            if presenter.status.get('phase')!=planner.state:
                presenter.set_status(dict(penalty=0,total=0,phase=planner.state,side=a.side,
                    owner='policy' if policy_owns else 'own references',goals=0,saves=0,misses=0))
            preq=data.qpos.copy();prev=data.qvel.copy()
            kick.command_before_step(t);data.ctrl[shooter.actuators]=kick.torque(data,slim)
            requested=kp*(ref-data.qpos[keeper.qpos])-kd*data.qvel[keeper.dofs]
            data.ctrl[keeper.actuators]=np.clip(requested,-caps,caps);control_writes+=1
            sat=np.where(abs(requested)>=caps,sat+1,0);maxsat=np.maximum(maxsat,sat)
            mujoco.mj_step(model,data)
            # Native positions and solver contacts describe this pre-integration t.
            positions=np.vstack([data.xpos[keeper.pelvis],data.xpos[wrists],data.xpos[shoulders]])
            if step==0:initial_positions=positions.copy()
            if step==1000:reference=positions.copy()
            q=preq[keeper.qpos];v=prev[keeper.dofs];ranges=model.jnt_range[keeper.joints]
            excess=float(max(0,np.max(ranges[:,0]-q),np.max(q-ranges[:,1])));maxexcess=max(maxexcess,excess)
            speed=float(abs(v).max());maxspeed=max(maxspeed,speed)
            w,x,y,z=preq[kq+3:kq+7];tilt=float(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y),-1,1))));maxtilt=max(maxtilt,tilt)
            for ci in range(data.ncon):
                c=data.contact[ci];ga,gb=map(int,c.geom)
                force=np.zeros(6);mujoco.mj_contactForce(model,data,ci,force)
                if bg in (ga,gb) and (ga in shooter.foot_geoms or gb in shooter.foot_geoms) and force[0]>.001:foot_ball=True
                if ga not in keeper.geoms and gb not in keeper.geoms:continue
                maxpen=max(maxpen,float(max(0,-c.dist)))
                if force[0]<=.001:continue
                kg=ga if ga in keeper.geoms else gb;other=gb if kg==ga else ga
                body=model.body(int(model.geom_bodyid[kg])).name
                if other==floor:
                    ground_bodies.add(body)
                    event_force=c.frame.reshape(3,3).T@force[:3]*(1 if kg==gb else -1)
                    if kg in keeper.foot_geoms:
                        foot_impulse+=event_force*.002
                contacts.append(dict(time_s=t,geoms=[model.geom(ga).name,model.geom(gb).name],
                    floor=other==floor,body=body,distance_m=float(c.dist),normal_force_n=float(force[0]),
                    ground_force_w=event_force.tolist() if other==floor else None))
            rows.append(np.r_[t,positions.reshape(-1),tilt,q,v,ref,requested,data.ctrl[keeper.actuators],data.qfrc_actuator[keeper.dofs]])
            poses.append(np.r_[t,preq,prev,data.ctrl]);ball_rows.append(np.r_[t,preq[bq:bq+3],prev[bv:bv+3]])
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():raise FloatingPointError('Nonfinite state')
            if maxpen>.03:raise RuntimeError('Keeper penetration > 3 cm')
            if excess>.10 or speed>40.:raise RuntimeError('Joint safety stop')
            if a.capture:
                for ct,label in [(1.9,'balance'),(2.99,'preparation'),(3.54,'push'),(4.19,'extension'),(5.9,'final')]:
                    if t>=ct and label not in phases_saved:
                        presenter.capture_keeper(label);phases_saved.add(label)
            if step%10==0:kick.update(data,data.xpos[ball].copy(),data.qvel[bv:bv+3].copy(),t)
            presenter.after_step()
        loop_wall=time.perf_counter()-loop_start
        presenter.pause('finished',2.)
    except (Exception,KeyboardInterrupt) as exc:
        failure=f'{type(exc).__name__}: {exc}'
        import traceback
        (a.output/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        if presenter:presenter.close()
        if client:client.close(force=failure is not None)
    data_rows=np.asarray(rows);np.savez_compressed(a.output/'trace.npz',frames=data_rows,world=np.asarray(poses),
        policy=np.asarray(policy_rows),ball=np.asarray(ball_rows))
    dump(a.output/'contacts.json',contacts)
    metrics={}
    if len(rows):
        pos=data_rows[:,1:16].reshape(-1,5,3);origin=reference if reference is not None else initial_positions
        sign=1 if a.side=='LEFT' else -1;arm=2 if a.side=='LEFT' else 1;shoulder=4 if a.side=='LEFT' else 3
        active=data_rows[:,0]>=2.
        if not active.any():active=np.ones(len(rows),bool)
        delta=pos-origin
        relative=(pos[:,arm,1]-pos[:,shoulder,1])-(origin[arm,1]-origin[shoulder,1])
        metrics=dict(max_pelvis_toward_m=float(np.max(sign*delta[active,0,1])),
            max_wrist_toward_m=float(np.max(sign*delta[active,arm,1])),
            max_arm_relative_extension_m=float(np.max(sign*relative[active])),
            final_pelvis_delta_m=(pos[-1,0]-origin[0]).tolist(),min_pelvis_height_m=float(pos[:,0,2].min()),
            final_pelvis_height_m=float(pos[-1,0,2]),max_tilt_deg=maxtilt,
            max_absolute_wrist_displacement_m=[float(np.linalg.norm(delta[:,k],axis=1).max()) for k in (1,2)],
            max_penetration_m=maxpen,max_joint_excess_rad=maxexcess,max_joint_speed_rad_s=maxspeed,
            reference_speed_rad_s=max_ref_speed,reference_acceleration_rad_s2=max_ref_accel,
            saturation_longest_s=(maxsat*.002).tolist(),foot_ground_impulse_w_Ns=foot_impulse.tolist())
    changed=[str(p) for p,h in resources.items() if hashlib.sha256(p.read_bytes()).hexdigest()!=h]
    if 'data' in locals():warnings={str(i):w.number for i,w in enumerate(data.warning) if w.number}
    checks=dict(complete=len(rows)==count,finite=failure is None or not str(failure).startswith('FloatingPointError'),
        no_external_forces=not external,one_pd=control_writes==len(rows),resources_unchanged=not changed,
        no_warnings=not warnings,penetration=maxpen<=.02,joints=maxexcess<=.03,joint_speed=maxspeed<=20.,
        normalizer_frozen=bool(client and getattr(client,'final',{}).get('normalizer_unchanged',False)),
        handoff_continuous=handoff is None and a.mode=='balance' or bool(handoff and planner.handoff_reference_jump==0))
    if a.mode=='maneuver':
        checks.update(body_moved=metrics.get('max_pelvis_toward_m',0)>=.20,
            wrist_moved=metrics.get('max_wrist_toward_m',0)>=.30,
            arm_extended=metrics.get('max_arm_relative_extension_m',0)>=.10,
            references_bounded=max_ref_speed<=3. and max_ref_accel<=20.)
    else:checks['standing']=maxtilt<15 and metrics.get('min_pelvis_height_m',0)>=.5
    report=dict(success=all(checks.values()) and failure is None,checks=checks,failure=failure,
        mode=a.mode,side=a.side,steps=len(rows),simulated_s=len(rows)*.002,loop_wall_s=loop_wall,
        total_wall_s=time.perf_counter()-started,metrics=metrics,transitions=planner.transitions if 'planner' in locals() else [],
        handoff=handoff,policy_decisions=len(policy_rows),last_policy_time_s=policy_rows[-1][0] if policy_rows else None,
        first_foot_ball_detected=foot_ball,ground_contact_bodies=sorted(ground_bodies),warnings=warnings,
        note='No agent or save result. Falls allowed; no reset/recovery.',
        source_sha256={n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('run.py','maneuver.py','presentation.py')},
        presentation=presenter.summary() if presenter else None)
    dump(a.output/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('presentation','handoff')},indent=2))
    return 0 if report['success'] else 2


if __name__=='__main__':raise SystemExit(main())
