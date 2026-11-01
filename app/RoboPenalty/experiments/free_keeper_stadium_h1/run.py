"""Hito 1 only. One 14 s penalty, no new save movement or predictive controller."""
from . import bootstrap
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import mujoco
import yaml
from phase2.freekick_adapter import FreeKickAdapter
from phase4a.scenarios import initialize
from experiments.free_keeper4b.policy import JOINTS
from .scene import build
from .policy_client import PolicyClient

PROJECT=bootstrap.PROJECT
# Declared before execution; reference clipping is inherited from 4B.1.
CRITERIA=dict(duration_s=14.,physics_steps=7000,decision_hz=50,
    max_tilt_deg=15.,max_horizontal_drift_m=.10,min_height_m=.50,
    persistent_saturation_s=.10,max_keeper_penetration_m=.01,joint_tolerance_rad=1e-6)


def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,default=lambda x:x.item())+'\n',encoding='utf-8')


def validate_resources(deploy,unitree):
    profile=json.loads((PROJECT/'portability/runtime_profile.json').read_text())
    before={};errors=[]
    for row in profile['files']:
        base=deploy if row['root']=='RoboNaldo_Deploy' else unitree
        p=(base/row['path']).resolve()
        if not p.is_relative_to(base.resolve()):raise ValueError('Unsafe resource path')
        h=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        if h!=row['sha256']:errors.append(row['root']+'/'+row['path'])
        else:before[p]=h
    if errors:raise ValueError('Missing/different exact resources: '+str(errors))
    return before


def actuator_caps(model,index,software):
    result=np.asarray(software,dtype=float).copy()
    for i,(a,j) in enumerate(zip(index.actuators,index.joints)):
        for flag,limits in ((model.actuator_ctrllimited[a],model.actuator_ctrlrange[a]),
                (model.actuator_forcelimited[a],model.actuator_forcerange[a]),
                (model.jnt_actfrclimited[j],model.jnt_actfrcrange[j])):
            if flag:result[i]=min(result[i],*abs(limits))
    return result


def root_addresses(model,index):
    j=int(model.body_jntadr[index.pelvis])
    if model.jnt_type[j]!=mujoco.mjtJoint.mjJNT_FREE:raise ValueError('Keeper root must be free')
    return int(model.jnt_qposadr[j]),int(model.jnt_dofadr[j])


def crossing(before,after,plane=5.):
    if not before[0]<plane<=after[0]:return None
    return before+(after-before)*(plane-before[0])/(after[0]-before[0])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deploy',required=True,type=Path)
    p.add_argument('--loco-deploy',required=True,type=Path)
    p.add_argument('--policy-python',required=True,type=Path)
    p.add_argument('--unitree',type=Path,default=PROJECT.parent/'unitree_mujoco')
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--placement',choices=('aside','center','absent'),default='aside')
    p.add_argument('--action',default='right_inter_m080')
    p.add_argument('--viewer',action='store_true');p.add_argument('--capture',action='store_true')
    p.add_argument('--camera',choices=('behind','execution','overview','goal','follow'),default='overview')
    a=p.parse_args();start=time.perf_counter();a.output=a.output.resolve()
    if not a.output.is_relative_to(PROJECT.parents[1]/'validation') or a.output.exists():
        p.error('Output must be NEW, inside this bundle validation/')
    a.deploy=a.deploy.resolve();a.unitree=a.unitree.resolve()
    before=validate_resources(a.deploy,a.unitree)
    catpath=PROJECT/'phase8c/catalog_v1.json';cat=json.loads(catpath.read_text())
    if a.action not in cat['actions']:p.error('Use an existing 8C action')
    entry=cat['actions'][a.action];calpath=catpath.parent/entry['probe']
    if hashlib.sha256(calpath.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Calibration changed')
    a.output.mkdir(parents=True);client=None;presenter=None;failure=None;interrupted=False;keeper=None
    frames=[];decisions=[];contacts=[];ball_rows=[];shooter_rows=[]
    foot=None;keeper_contact=None;goal_cross=None;completed=0;finite=True;no_forces=True
    max_tilt=drift=penetration=keeper_penetration=saturation=0.;min_height=999.;improper=joint_bad=clips=0
    satrun=np.zeros(29,dtype=int);metrics_rows=[];warnings={};min_prep_height=999.
    prep_tilt=prep_drift=0.
    try:
        meta=None
        if a.placement!='absent':
            client=PolicyClient(a.policy_python.resolve(),a.loco_deploy.resolve(),a.output,PROJECT)
            meta=client.metadata
            if tuple(meta['joints'])!=JOINTS or meta['recurrent_reset_max']!=0 or meta['physical_velocity_command']!=[0,0,0]:
                raise ValueError('Locomotion contract rejected')
        home=np.asarray(meta['home']) if meta else np.zeros(29)
        y={'aside':4.,'center':0.,'absent':None}[a.placement]
        model,data,shooter,keeper,checks=build(a.deploy,a.unitree,home,y)
        if keeper and tuple(model.joint(int(j)).name.removeprefix('gk/') for j in keeper.joints)!=JOINTS:
            raise ValueError('Policy/model joint ordering differs')
        kick=FreeKickAdapter(a.deploy,model,shooter)
        initialize(dict(translate_x=-2.,target_bias=entry['bias']),model,data,kick,None,False)
        mujoco.mj_forward(model,data)
        shooter_limits=np.asarray(yaml.safe_load((a.deploy/'deploy_mujoco/config/mujoco_freekick.yaml').read_text())['tau_limit'])
        if keeper:
            kq,kv=root_addresses(model,keeper);caps=actuator_caps(model,keeper,meta['limits'])
            target=home.copy();origin=data.qpos[kq:kq+3].copy();kp=np.asarray(meta['kp']);kd=np.asarray(meta['kd'])
        ball=model.body('ball').id;bj=int(model.body_jntadr[ball]);bq=int(model.jnt_qposadr[bj]);bv=int(model.jnt_dofadr[bj])
        bg=model.geom('ball_geom').id;floor=model.geom('floor').id
        initial=data.qpos.copy();previous=data.qpos[bq:bq+3].copy()
        signature=mujoco.mjtState.mjSTATE_INTEGRATION
        class View:
            engine=SimpleNamespace(mujoco=mujoco,np=np)
            def integration_state(self,d):
                v=np.empty(mujoco.mj_stateSize(model,signature));mujoco.mj_getState(model,d,v,signature);return v
        runtime=View();runtime.model=model;runtime.data=data
        from .presentation import FreeKeeperPresenter
        from phase6a.presentation import PresentationConfig,ViewerClosed
        presenter=FreeKeeperPresenter(runtime,PresentationConfig(enabled=a.viewer,fps=30.,realtime=True),a.output,'long',camera=a.camera)
        presenter.set_status(dict(penalty=1,total=1,phase='PREPARING',action=a.action,goals=0,saves=0,misses=0))
        if a.capture:presenter.render_views('initial')
        presenter.pause('ready',1.);presenter.begin_episode()
        dump(a.output/'composition.json',dict(checks=checks,criteria=CRITERIA,
            placement=a.placement,keeper=keeper.describe(model) if keeper else None,
            shooter=shooter.describe(model),initial_qpos=initial.tolist(),
            free_roots=[model.joint(i).name for i in range(model.njnt) if model.jnt_type[i]==mujoco.mjtJoint.mjJNT_FREE],
            neq=model.neq,policy=meta,physical_dt=model.opt.timestep,
            keeper_effective_caps_nm=caps.tolist() if keeper else None,
            ball_radius_m=float(model.geom_size[bg,0]),ball_mass_kg=float(model.body_mass[ball]),
            floor_friction=model.geom_friction[floor].tolist()))
        loop_start=time.perf_counter();writes=0
        for step in range(CRITERIA['physics_steps']):
            now=float(data.time)
            if np.any(data.xfrc_applied) or np.any(data.qfrc_applied):
                no_forces=False;raise RuntimeError('External force detected')
            if keeper and step%10==0:
                response=client.request('observe',q=data.qpos[keeper.qpos].tolist(),dq=data.qvel[keeper.dofs].tolist(),
                    quaternion=data.qpos[kq+3:kq+7].tolist(),omega=data.qvel[kv+3:kv+6].tolist())
                raw=np.asarray(response['target']);target=np.clip(raw,model.jnt_range[keeper.joints,0],model.jnt_range[keeper.joints,1])
                if raw.shape!=(29,) or not np.isfinite(raw).all():raise ValueError('Invalid policy target')
                clips+=int(np.count_nonzero(raw!=target))
                decisions.append(np.r_[now,response['observation'],raw,target])
            kick.command_before_step(step*.002)
            data.ctrl[shooter.actuators]=kick.torque(data,shooter_limits)
            if keeper:
                requested=kp*(target-data.qpos[keeper.qpos])-kd*data.qvel[keeper.dofs]
                data.ctrl[keeper.actuators]=np.clip(requested,-caps,caps);writes+=1
                satrun=np.where(abs(requested)>=caps,satrun+1,0);saturation=max(saturation,float(satrun.max()*.002))
            mujoco.mj_step(model,data);completed+=1
            t=float(data.time);position=data.qpos[bq:bq+3].copy()
            cross=crossing(previous,position)
            if cross is not None and goal_cross is None:
                fraction=(5.-previous[0])/(position[0]-previous[0])
                goal_cross=dict(time_s=now+fraction*.002,position_w=cross.tolist(),inside=bool(abs(cross[1])<=1.5 and 0<=cross[2]<=1.8))
            for i in range(data.ncon):
                c=data.contact[i];ga,gb=map(int,c.geom);penetration=max(penetration,float(max(0,-c.dist)))
                force=np.zeros(6);mujoco.mj_contactForce(model,data,i,force)
                if force[0]<=.001:continue
                event=dict(solver_time_s=now,sampled_time_s=t,geoms=[model.geom(ga).name,model.geom(gb).name],
                    distance_m=float(c.dist),position_w=c.pos.tolist(),force_contact=force.tolist())
                if bg in (ga,gb):
                    contacts.append(event);other=gb if ga==bg else ga
                    if other in shooter.foot_geoms and foot is None:
                        foot=event|dict(ball_velocity_after_step_w=data.qvel[bv:bv+3].tolist())
                    if keeper and other in keeper.geoms and keeper_contact is None:keeper_contact=event
                if keeper and (ga in keeper.geoms or gb in keeper.geoms):
                    keeper_penetration=max(keeper_penetration,float(max(0,-c.dist)))
                    contacts.append(event)
                    other=gb if ga in keeper.geoms else ga;kg=ga if ga in keeper.geoms else gb
                    if other!=floor or kg not in keeper.foot_geoms:improper+=1
            if keeper:
                w,x,yq,z=data.qpos[kq+3:kq+7]
                tilt=float(np.degrees(np.arccos(np.clip(1-2*(x*x+yq*yq),-1,1))))
                max_tilt=max(max_tilt,tilt);drift=max(drift,float(np.linalg.norm(data.qpos[kq:kq+2]-origin[:2])))
                height=float(data.qpos[kq+2]);min_height=min(min_height,height)
                if foot is None:
                    min_prep_height=min(min_prep_height,height)
                    prep_tilt=max(prep_tilt,tilt)
                    prep_drift=max(prep_drift,float(np.linalg.norm(data.qpos[kq:kq+2]-origin[:2])))
                qk=data.qpos[keeper.qpos];ranges=model.jnt_range[keeper.joints]
                joint_bad+=int(np.any(qk<ranges[:,0]-1e-6) or np.any(qk>ranges[:,1]+1e-6))
                metrics_rows.append(np.r_[t,height,tilt,data.qpos[kq:kq+2]-origin[:2]])
                frames.append(np.r_[t,data.qpos[kq:kq+7],data.qvel[kv:kv+6],qk,data.qvel[keeper.dofs],target,
                    data.ctrl[keeper.actuators],data.qfrc_actuator[keeper.dofs]])
                if height<.50 or tilt>=15 or drift>=.10:raise RuntimeError('Keeper standing safety criterion exceeded')
            if step%10==0:
                kick.update(data,data.xpos[ball].copy(),data.qvel[bv:bv+3].copy(),step*.002)
            ball_rows.append(np.r_[t,position,data.qvel[bv:bv+3]])
            shooter_rows.append(np.r_[data.qpos[shooter.qpos],data.qvel[shooter.dofs],data.ctrl[shooter.actuators],
                data.qpos[kick.root_q:kick.root_q+7],data.qvel[kick.root_v:kick.root_v+6]])
            finite=bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all() and np.isfinite(data.ctrl).all())
            if not finite:raise FloatingPointError('Nonfinite world state')
            previous=position
            if foot and presenter.status.get('phase')=='PREPARING':
                presenter.set_status(dict(penalty=1,total=1,phase='SHOOTING',action=a.action,goals=0,saves=0,misses=0))
            presenter.after_step()
        loop_wall=time.perf_counter()-loop_start
        outcome='GOAL' if goal_cross and goal_cross['inside'] else 'MISS' if goal_cross else 'UNRESOLVED'
        presenter.set_status(dict(penalty=1,total=1,phase='FINISHED',action=a.action,last_result=outcome,
            goals=int(outcome=='GOAL'),saves=0,misses=int(outcome=='MISS')))
        if a.capture:presenter.render_views('final')
        presenter.pause('finished',2.)
    except KeyboardInterrupt:
        interrupted=True;failure='KeyboardInterrupt'
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        import traceback
        (a.output/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        if presenter:presenter.close()
        if client:client.close(force=failure is not None)
    np.savez_compressed(a.output/'trace.npz',keeper=np.asarray(frames),decisions=np.asarray(decisions),
        ball=np.asarray(ball_rows),shooter=np.asarray(shooter_rows),stability=np.asarray(metrics_rows))
    dump(a.output/'contacts.json',contacts)
    changed=[str(p) for p,h in before.items() if hashlib.sha256(p.read_bytes()).hexdigest()!=h]
    if 'data' in locals():warnings={str(i):w.number for i,w in enumerate(data.warning) if w.number}
    sarray=np.asarray(shooter_rows)
    if len(sarray):
        sq=sarray[:,90:94];shooter_tilt=float(np.degrees(np.arccos(np.clip(1-2*(sq[:,1]**2+sq[:,2]**2),-1,1))).max())
        shooter_height=float(sarray[:,89].min())
    else:shooter_tilt=shooter_height=None
    tests=dict(complete=completed==7000,finite=finite,no_external_forces=no_forces,
        foot_ball=foot is not None,no_file_changes=not changed,no_warnings=not warnings,
        shooter_no_fall=shooter_height is not None and shooter_height>.15 and shooter_tilt<70,
        single_keeper_pd=not keeper or writes==completed,standing=not keeper or (max_tilt<15 and drift<.10 and min_height>=.50),
        feet_only=improper==0,no_persistent_saturation=saturation<.10,joints=joint_bad==0,
        keeper_penetration=keeper_penetration<=.01,normalizer_frozen=not client or getattr(client,'final',{}).get('normalizer_unchanged',False)) if 'keeper' in locals() else {}
    report=dict(success=bool(tests and all(tests.values()) and failure is None),failure=failure,checks=tests,
        steps=completed,simulated_s=completed*.002,loop_wall_s=locals().get('loop_wall'),total_wall_s=time.perf_counter()-start,
        placement=a.placement,action=a.action,first_foot_ball=foot,first_keeper_ball=keeper_contact,goal_crossing=goal_cross,
        result='GOAL' if goal_cross and goal_cross['inside'] else 'MISS' if goal_cross else 'UNRESOLVED',
        max_keeper_tilt_deg=max_tilt if keeper else None,max_keeper_horizontal_drift_m=drift if keeper else None,
        min_keeper_height_m=min_height if keeper else None,min_preparation_height_m=min_prep_height if keeper else None,
        max_preparation_tilt_deg=prep_tilt if keeper else None,max_preparation_drift_m=prep_drift if keeper else None,
        shooter_max_root_tilt_deg=shooter_tilt,shooter_min_root_height_m=shooter_height,
        max_penetration_m=penetration,max_keeper_penetration_m=keeper_penetration,max_saturation_run_s=saturation,
        joint_violation_steps=joint_bad,improper_keeper_contact_events=improper,reference_clips=clips,warnings=warnings,
        external_files_changed=changed,policy_rpc_max_s=max(client.latencies,default=0.) if client else None,
        presentation=presenter.summary() if presenter else None,
        note='Hito 1 only: standing, no save maneuver. Contact time uses original solver pre-step state.')
    dump(a.output/'report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='presentation'},indent=2),flush=True)
    return 0 if report['success'] else 2


if __name__=='__main__':raise SystemExit(main())
