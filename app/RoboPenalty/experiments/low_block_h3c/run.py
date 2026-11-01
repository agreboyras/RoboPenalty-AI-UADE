"""H1-derived private loop, same physics/PD with a single final reference."""
from experiments.free_keeper_stadium_h1 import bootstrap
import argparse,hashlib,json,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import mujoco,yaml
from phase2.freekick_adapter import FreeKickAdapter
from phase4a.scenarios import initialize
from phase4a.evaluation import classify
from experiments.free_keeper_stadium_h1.scene import build
from experiments.free_keeper_stadium_h1.run import validate_resources,actuator_caps,root_addresses
from experiments.free_keeper_stadium_h1.policy_client import PolicyClient
from experiments.free_keeper_stadium_h1.presentation import FreeKeeperPresenter
from experiments.central_block_h3a.run import Recorder,dump
from phase6a.presentation import PresentationConfig
from .maneuver import LowBlock,PROTOCOL

PROJECT=bootstrap.PROJECT
# Predeclared impact limits, same as H3A. Falling itself is not an invalid state.
LIMITS=dict(steps=7000,dt=.002,max_joint_speed=20.,abort_joint_speed=40.,max_penetration=.02,
    abort_penetration=.03,max_joint_excess=.03,abort_joint_excess=.10,max_saturation_s=.10,abort_saturation_s=.50)

def policy_target(raw,ranges):
    raw=np.asarray(raw,dtype=float)
    if raw.shape!=(29,) or not np.isfinite(raw).all():raise ValueError('Invalid locomotion target')
    return raw,np.clip(raw,ranges[:,0],ranges[:,1])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('deploy','loco-deploy','policy-python','output','reference'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--action',choices=('left_near_b060','center'),default='left_near_b060')
    p.add_argument('--mode',choices=('passive','active'),default='active');p.add_argument('--amplitude',type=float,choices=(.04,.08),default=.04)
    p.add_argument('--viewer',action='store_true');p.add_argument('--camera',choices=('goal','behind','execution','overview'),default='goal')
    a=p.parse_args();start=time.perf_counter();a.output=a.output.resolve()
    if a.output.exists() or not a.output.is_relative_to(PROJECT.parents[1]/'validation'):p.error('Use a NEW output inside validation/')
    a.deploy=a.deploy.resolve();unitree=PROJECT.parent/'unitree_mujoco';before=validate_resources(a.deploy,unitree)
    catalog=json.loads((PROJECT/'phase8c/catalog_v1.json').read_text());entry=catalog['actions'][a.action]
    cal=PROJECT/'phase8c'/entry['probe']
    if hashlib.sha256(cal.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Calibration changed')
    reference=json.loads(a.reference.read_text())
    if reference.get('action')!=a.action or reference.get('placement')!='aside' or reference.get('calibration_sha256')!=entry['sha256']:raise ValueError('Wrong reference')
    a.output.mkdir(parents=True);client=presenter=None;failure=None;rec=Recorder(a.output)
    frames=[];decisions=[];balls=[];shooters=[];stability=[];commands=[];points=[];world=[]
    foot=None;completed=0;sat=np.zeros(29,dtype=int);longest=0.;clips=0;pre_ok=True;maxpen=0.;finite=True;external=False;loopwall=None
    max_tilt=drift=0.;min_height=999.;box_contacts=[]
    try:
        client=PolicyClient(a.policy_python.resolve(),a.loco_deploy.resolve(),a.output,PROJECT);meta=client.metadata
        if meta['recurrent_reset_max']!=0 or meta['physical_velocity_command']!=[0,0,0]:raise ValueError('Policy contract mismatch')
        model,data,shooter,keeper,checks=build(a.deploy,unitree,np.array(meta['home']),0.)
        names=[model.joint(int(j)).name.removeprefix('gk/') for j in keeper.joints]
        if names!=list(meta['joints']):raise ValueError('Joint order mismatch')
        block=LowBlock(names,a.amplitude,a.mode=='active')
        kick=FreeKickAdapter(a.deploy,model,shooter);initialize(dict(translate_x=-2.,target_bias=entry['bias']),model,data,kick,None,False)
        mujoco.mj_forward(model,data);kq,kv=root_addresses(model,keeper);origin=data.qpos[kq:kq+3].copy()
        caps=actuator_caps(model,keeper,meta['limits']);kp=np.array(meta['kp']);kd=np.array(meta['kd']);base=np.array(meta['home'])
        sl=np.array(yaml.safe_load((a.deploy/'deploy_mujoco/config/mujoco_freekick.yaml').read_text())['tau_limit'])
        bg=model.geom('ball_geom').id;bid=model.body('ball').id;bj=int(model.body_jntadr[bid]);bq=int(model.jnt_qposadr[bj]);bv=int(model.jnt_dofadr[bj])
        dump(a.output/'composition.json',dict(checks=checks,initial_qpos=data.qpos.copy(),policy=meta,keeper_effective_caps_nm=caps,
            action=a.action,bias=entry['bias'],protocol=PROTOCOL,limits=LIMITS,mode=a.mode,amplitude=a.amplitude))
        signature=mujoco.mjtState.mjSTATE_INTEGRATION
        class View:
            engine=SimpleNamespace(mujoco=mujoco,np=np)
            def integration_state(self,d):
                out=np.empty(mujoco.mj_stateSize(model,signature));mujoco.mj_getState(model,d,out,signature);return out
        runtime=View();runtime.model=model;runtime.data=data
        class Presenter(FreeKeeperPresenter):
            def overlay(self):
                left='HITO 3C BLOQUEO BAJO\nEstado\nContacto\nTiempo'
                right=f'{a.mode.upper()} / {block.state}\n{self.status.get("phase","READY")}\n{"SI" if rec.events else "NO"}\n{data.time:.2f} s'
                self.handle.set_texts((mujoco.mjtFontScale.mjFONTSCALE_100,mujoco.mjtGridPos.mjGRID_TOPLEFT,left,right))
        presenter=Presenter(runtime,PresentationConfig(enabled=a.viewer,fps=30.,realtime=True),a.output,'long',camera=a.camera)
        presenter.set_status(dict(penalty=1,total=1,phase='PREPARING',action=a.action,goals=0,saves=0,misses=0));presenter.pause('ready',1.);presenter.begin_episode()
        loopstart=time.perf_counter()
        for step in range(LIMITS['steps']):
            now=float(data.time)
            if np.any(data.xfrc_applied) or np.any(data.qfrc_applied):external=True;raise RuntimeError('External force')
            if step%10==0:
                reply=client.request('observe',q=data.qpos[keeper.qpos].tolist(),dq=data.qvel[keeper.dofs].tolist(),quaternion=data.qpos[kq+3:kq+7].tolist(),omega=data.qvel[kv+3:kv+6].tolist())
                raw,base=policy_target(reply['target'],model.jnt_range[keeper.joints]);clips+=int(np.count_nonzero(raw!=base))
                decisions.append(np.r_[now,reply['observation'],raw,base])
                block.observe(now,data.qpos[bq:bq+3].copy(),data.qvel[bv:bv+3].copy())
            residual=block.residual(now);target=base+residual
            if np.any(target<model.jnt_range[keeper.joints,0]) or np.any(target>model.jnt_range[keeper.joints,1]):raise RuntimeError('Final reference outside limits')
            commands.append(np.r_[now,base,residual,target,data.qpos[keeper.qpos],data.qvel[keeper.dofs]])
            kick.command_before_step(step*.002);data.ctrl[shooter.actuators]=kick.torque(data,sl)
            requested=kp*(target-data.qpos[keeper.qpos])-kd*data.qvel[keeper.dofs]
            data.ctrl[keeper.actuators]=np.clip(requested,-caps,caps)
            sat=np.where(abs(requested)>=caps,sat+1,0);longest=max(longest,float(sat.max()*.002))
            rec.step(model,data,mujoco.mj_step);completed+=1;t=float(data.time)
            for i,c in enumerate(data.contact):
                ga,gb=map(int,c.geom)
                if ga not in keeper.geoms and gb not in keeper.geoms and bg not in (ga,gb):continue
                force=np.zeros(6);mujoco.mj_contactForce(model,data,i,force)
                if ga in keeper.geoms or gb in keeper.geoms:maxpen=max(maxpen,float(max(0,-c.dist)))
                if bg in (ga,gb) and (gb if ga==bg else ga) in shooter.foot_geoms and force[0]>.001 and foot is None:
                    foot=dict(solver_time_s=now,sampled_time_s=t,force_contact=force.copy(),position_w=c.pos.copy(),geoms=[model.geom(ga).name,model.geom(gb).name])
            w,x,y,z=data.qpos[kq+3:kq+7];tilt=float(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y),-1,1))));height=float(data.qpos[kq+2]);travel=float(np.linalg.norm(data.qpos[kq:kq+2]-origin[:2]))
            max_tilt=max(max_tilt,tilt);min_height=min(min_height,height);drift=max(drift,travel)
            if block.trigger is None:
                pre_ok &= height>=.5 and tilt<15 and travel<.1
                if not pre_ok:raise RuntimeError('Pre-maneuver standing limit')
            if maxpen>LIMITS['abort_penetration'] or rec.max_speed>LIMITS['abort_joint_speed'] or rec.max_excess>LIMITS['abort_joint_excess'] or longest>=LIMITS['abort_saturation_s']:raise RuntimeError('Physical safety interruption')
            finite=bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all() and np.isfinite(data.ctrl).all())
            if not finite:raise FloatingPointError('Nonfinite state')
            stability.append(np.r_[t,height,tilt,data.qpos[kq:kq+2]-origin[:2]])
            frames.append(np.r_[t,data.qpos[kq:kq+7],data.qvel[kv:kv+6],data.qpos[keeper.qpos],data.qvel[keeper.dofs],target,data.ctrl[keeper.actuators],data.qfrc_actuator[keeper.dofs]])
            points.append(np.r_[now,*[data.xpos[model.body('gk/'+n).id] for n in ('pelvis','right_knee_link','right_ankle_roll_link')]])
            world.append(np.r_[t,data.qpos,data.qvel,data.ctrl])
            if step%10==0:kick.update(data,data.xpos[bid].copy(),data.qvel[bv:bv+3].copy(),step*.002)
            balls.append(np.r_[t,data.qpos[bq:bq+3],data.qvel[bv:bv+3]])
            shooters.append(np.r_[data.qpos[shooter.qpos],data.qvel[shooter.dofs],data.ctrl[shooter.actuators],data.qpos[kick.root_q:kick.root_q+7],data.qvel[kick.root_v:kick.root_v+6]])
            if foot and presenter.status.get('phase')=='PREPARING':presenter.set_status(dict(penalty=1,total=1,phase='SHOOTING',action=a.action,goals=0,saves=0,misses=0))
            presenter.after_step()
        loopwall=time.perf_counter()-loopstart
        presenter.set_status(dict(penalty=1,total=1,phase='FINISHED',action=a.action,goals=int(any(c['inside_goal'] for c in rec.crossings)),saves=0,misses=0));presenter.pause('finished',2.)
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        import traceback
        (a.output/'error.txt').write_text(traceback.format_exc(),encoding='utf8')
    finally:
        if presenter:presenter.close()
        if client:client.close(force=failure is not None)
    np.savez_compressed(a.output/'trace.npz',keeper=np.asarray(frames),decisions=np.asarray(decisions),ball=np.asarray(balls),shooter=np.asarray(shooters),stability=np.asarray(stability))
    np.savez_compressed(a.output/'maneuver.npz',commands=np.asarray(commands),points=np.asarray(points),world=np.asarray(world))
    if not rec.ready:
        dump(a.output/'interception.json',dict(physical_valid=False,status='BLOQUEADO',failure=failure));return 2
    warnings={str(i):v.number for i,v in enumerate(data.warning) if v.number}
    unexpected=[e for e in rec.other_contacts if not (e['solver_s']>=(block.trigger if block.trigger is not None else 999.) and 'floor' in e['geoms'])]
    checks=dict(complete=completed==7000,finite=finite,no_external_forces=not external,foot_ball=foot is not None,
        unchanged_resources=all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in before.items()),no_warnings=not warnings,
        pre_standing=bool(pre_ok),no_unexpected_contacts=not unexpected,joint_speed=rec.max_speed<=20.,joint_excess=rec.max_excess<=.03,
        penetration=maxpen<=.02,no_persistent_saturation=longest<.1,torques=bool(np.all(rec.peak_torque<=caps+1e-6)),
        normalizer_frozen=bool(getattr(client,'final',{}).get('normalizer_unchanged',False)))
    valid=all(checks.values()) and failure is None;goal=any(c['inside_goal'] for c in rec.crossings)
    payload=dict(evaluation=dict(first_foot_ball=foot,foot_peak_force_n=float(foot['force_contact'][0]) if foot else 0.,goal_detected=goal,first_keeper_ball=rec.events[0] if rec.events else None,keeper_peak_contact_force_n=max((e['normal_force_n'] for e in rec.events),default=0.)))
    score=classify(payload,dict(evaluation=dict(goal_detected=reference['goal_detected'],goal_crossing_measured=reference['goal_crossings'])))
    save=valid and reference['physical_valid'] and score=='save_with_contact_and_goal_counterfactual'
    result=dict(status='CANDIDATA A ATAJADA ACTIVA' if save and block.trigger is not None else 'ATAJADA PASIVA' if save else 'CONTACTO SIN ATAJADA' if rec.events and goal else 'SIN CONTACTO',
        action=a.action,mode=a.mode,amplitude=a.amplitude,physical_valid=valid,checks=checks,failure=failure,official_result='SAVE' if save else 'GOAL' if goal else 'UNRESOLVED',
        steps=completed,simulated_s=completed*.002,shot_detection_s=block.trigger,maneuver_start_s=next((float(r[0]) for r in commands if abs(r[30:59]).max()>1e-8),None),
        release_s=block.release,first_foot_ball=foot,first_keeper_ball=rec.events[0] if rec.events else None,contact_samples=len(rec.events),plane_crossings=rec.crossings,
        peak_force_n=max((e['normal_force_n'] for e in rec.events),default=0.),impulse_on_ball_w_Ns=sum((e['step_impulse_on_ball_Ns'] for e in rec.events),np.zeros(3)),
        min_ball_keeper_gap=rec.closest,max_tilt_deg=max_tilt,max_drift_m=drift,min_height_m=min_height,max_penetration_m=maxpen,
        max_joint_speed_rad_s=rec.max_speed,max_joint_excess_rad=rec.max_excess,max_saturation_s=longest,actual_torque_peaks=rec.peak_torque,torque_caps=caps,
        reference_clips=clips,warnings=warnings,unexpected_contacts=unexpected,loop_wall_s=loopwall,total_wall_s=time.perf_counter()-start,
        note='No fall anchoring or post-trigger standing guard. Final save requires paired causal/movement/repetition checks.')
    if not valid:result['status']='BLOQUEADO'
    dump(a.output/'interception.json',result);dump(a.output/'ball_keeper_contacts.json',rec.events);dump(a.output/'observations.json',block.rows)
    print(json.dumps({k:result[k] for k in ('status','physical_valid','official_result','shot_detection_s','peak_force_n','failure')},indent=2))
    return 0 if valid else 2

if __name__=='__main__':raise SystemExit(main())
