"""Observe the unchanged reference physics; never writes actions or state itself."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch
from .environment import configure_cache
from .audit_checkpoint import probe, EXPECTED_SHA


def contact_geometry_ids(contact):
    """Canonical IDs copied by Warp 3.5; deprecated fields may be stale."""
    return tuple(map(int, contact.geom))


def classify_result(goal, contact, aimed, reversed_after, frame_contact):
    if goal: return 'GOAL'
    if not contact: return 'NO_ROBOT_CONTACT_NO_GOAL'
    if aimed and reversed_after and not frame_contact:
        return 'ROBOT_REBOUND_PRECONTACT_AIM_INSIDE_NO_GOAL_OBSERVED'
    return 'ROBOT_CONTACT_NO_GOAL_SAVE_NOT_PROVEN'


class Observer:
    def __init__(self, env, output):
        import mujoco
        import mujoco_warp as mjw
        self.env, self.output, self.mjw, self.mujoco = env, output, mjw, mujoco
        self.model = env.sim.mj_model
        self.mirror = mujoco.MjData(self.model)
        m = self.model
        ball_geoms = [i for i in range(m.ngeom) if m.geom(i).name.endswith('ball_geom')]
        if len(ball_geoms) != 1: raise ValueError('Cannot identify reference ball')
        self.ball_geom = ball_geoms[0]
        self.ball_body = int(m.geom_bodyid[self.ball_geom])
        self.ball_joint = int(m.body_jntadr[self.ball_body])
        self.bq = int(m.jnt_qposadr[self.ball_joint]); self.bv = int(m.jnt_dofadr[self.ball_joint])
        roots = [i for i in range(m.nbody) if m.body(i).name.endswith('/pelvis')]
        if len(roots) != 1: raise ValueError('Cannot identify robot pelvis')
        self.root = roots[0]
        self.rq = int(m.jnt_qposadr[m.body_jntadr[self.root]])
        self.robot_bodies = set()
        for i in range(m.nbody):
            ancestor = i
            while ancestor:
                if ancestor == self.root: self.robot_bodies.add(i); break
                ancestor = int(m.body_parentid[ancestor])
        self.robot_joints = np.array([j for j in range(m.njnt)
            if m.jnt_bodyid[j] in self.robot_bodies and m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE])
        self.qa = m.jnt_qposadr[self.robot_joints]
        self.active = False; self.summaries = []; self.rows = []; self.actions = []
        self.original_step = env.sim.step
        self.original_reset = env._reset_idx

    def copy(self):
        # This copies actual Warp solver contacts/forces. NO mj_forward on the
        # mirror: native-viewer C contacts are NOT used as physical evidence.
        self.mjw.get_data_into(self.mirror, self.model, self.env.sim.wp_data)
        return self.mirror

    def start(self):
        d = self.copy()
        self.active = True; self.rows = []; self.actions = []; self.contacts = []
        self.initial = d.qpos.copy(); self.previous_ball = d.qpos[self.bq:self.bq+3].copy()
        self.previous_velocity = d.qvel[self.bv:self.bv+3].copy()
        self.robot_contact_bodies = set(); self.goal = False; self.crossings = []
        self.first_contact = None; self.aimed_before_contact = False
        self.reversed_after_contact = False; self.frame_contact = False
        self.max_penetration = 0.; self.max_tilt = 0.; self.min_height = float(d.qpos[self.rq+2])
        self.torque_peak = 0.; self.saturated_frames = 0; self.finite = True
        self.buffer_overflow = False
        self.force_readback_differences = 0
        self.ball_contact_candidates = []
        self.started = time.perf_counter()

    def sample(self):
        d = self.copy(); m = self.model
        wpdata = self.env.sim.wp_data
        self.buffer_overflow |= bool(wpdata.nacon.numpy()[0] > wpdata.naconmax or
                                     wpdata.nefc.numpy()[0] > wpdata.njmax)
        ball = d.qpos[self.bq:self.bq+3].copy()
        velocity = d.qvel[self.bv:self.bv+3].copy()
        import warp as wp
        count = min(int(wpdata.nacon.numpy()[0]), wpdata.naconmax)
        raw_geoms = wpdata.contact.geom.numpy()[:count]
        ids = [i for i,g in enumerate(raw_geoms) if self.ball_geom in g]
        force_by_id = {}
        if ids:
            contact_ids = wp.array(ids, dtype=wp.int32, device='cpu')
            forces = wp.zeros(len(ids), dtype=wp.spatial_vector, device='cpu')
            self.mjw.contact_force(self.env.sim.wp_model, wpdata, contact_ids, False, forces)
            force_by_id = dict(zip(ids, forces.numpy()))
        episode_contacts = []
        for i in range(d.ncon):
            c = d.contact[i]
            self.max_penetration = max(self.max_penetration, float(max(0, -c.dist)))
            # MuJoCo-Warp 3.5 fills contact.geom, not the deprecated geom1/geom2
            # members of the host mirror. Use the canonical IDs actually copied.
            a, b = contact_geometry_ids(c)
            if self.ball_geom not in (a, b): continue
            copied_force = np.zeros(6); self.mujoco.mj_contactForce(m, d, i, copied_force)
            force = force_by_id.get(i, np.zeros(6))
            self.force_readback_differences += int(np.max(np.abs(force-copied_force)) > 1e-3)
            self.ball_contact_candidates.append(dict(time_s=float(d.time), geoms=[a,b],
                names=[m.geom(a).name,m.geom(b).name], distance=float(c.dist),
                native_force=force.tolist(), copied_force=copied_force.tolist()))
            if force[0] <= 1e-3: continue
            other = b if a == self.ball_geom else a
            body = int(m.geom_bodyid[other]); robot = body in self.robot_bodies
            name = m.body(body).name
            event = dict(time_s=float(d.time), body=name, robot=robot,
                         position=c.pos.tolist(), distance=float(c.dist), force=force.tolist())
            episode_contacts.append(event)
            if robot:
                self.robot_contact_bodies.add(name)
                if self.first_contact is None:
                    self.first_contact = event
                    # Conservative pre-contact ballistic check, evaluator only.
                    # Unknown drag/ground bounce means no claimed causal save.
                    v = self.previous_velocity; p = self.previous_ball
                    if v[0] < -0.05 and m.opt.density == 0 and m.opt.viscosity == 0:
                        eta = (-0.5-p[0])/v[0]
                        if eta > 0:
                            y = p[1]+eta*v[1]
                            z = p[2]+eta*v[2]+0.5*m.opt.gravity[2]*eta**2
                            self.aimed_before_contact = bool(abs(y) <= 1.35 and 0.11 <= z <= 1.65)
                    event['pre_ball_velocity'] = self.previous_velocity.tolist()
                    event['post_ball_velocity'] = velocity.tolist()
                if self.previous_velocity[0] < -0.05 and velocity[0] > 0.05:
                    self.reversed_after_contact = True
            if 'post' in name or 'crossbar' in name:
                self.frame_contact = True
        self.contacts.extend(episode_contacts)
        if self.previous_ball[0] > -0.5 >= ball[0]:
            u = (-0.5-self.previous_ball[0])/(ball[0]-self.previous_ball[0])
            crossing = self.previous_ball+u*(ball-self.previous_ball)
            inside = bool(abs(crossing[1]) <= 1.5 and 0 <= crossing[2] <= 1.8)
            self.goal |= inside
            self.crossings.append(dict(time_s=float(d.time), position=crossing.tolist(), inside=inside))
        w, x, y, z = d.qpos[self.rq+3:self.rq+7]
        tilt = float(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y), -1, 1))))
        self.max_tilt = max(self.max_tilt, tilt)
        self.min_height = min(self.min_height, float(d.qpos[self.rq+2]))
        self.torque_peak = max(self.torque_peak, float(np.abs(d.actuator_force).max()))
        caps = np.maximum(np.abs(m.actuator_forcerange[:, 0]), np.abs(m.actuator_forcerange[:, 1]))
        self.saturated_frames += int(np.any(m.actuator_forcelimited & (np.abs(d.actuator_force) >= caps-1e-4)))
        self.finite &= bool(np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all())
        self.rows.append(np.r_[d.time, d.qpos, d.qvel, d.ctrl, d.actuator_force])
        self.previous_ball, self.previous_velocity = ball, velocity

    def finish(self, reason):
        if not self.active: return
        d = self.copy()
        index = len(self.summaries)+1
        folder = self.output/f'episode_{index:02d}'; folder.mkdir()
        np.savez_compressed(folder/'trace.npz', frames=np.asarray(self.rows),
                            actions=np.asarray(self.actions), initial_qpos=self.initial)
        (folder/'ball_contacts.json').write_text(json.dumps(self.contacts, indent=2), encoding='utf-8')
        (folder/'ball_contact_candidates.json').write_text(json.dumps(self.ball_contact_candidates, indent=2), encoding='utf-8')
        outcome = classify_result(self.goal, self.first_contact is not None,
                                  self.aimed_before_contact, self.reversed_after_contact,
                                  self.frame_contact)
        q = np.asarray(self.rows)[:, 1:1+self.model.nq] if self.rows else self.initial[None]
        ranges = np.ptp(q[:, self.qa], axis=0)
        summary = dict(episode=index, result=outcome, end_reason=reason,
            simulated_end_s=float(d.time), substeps=len(self.rows), wall_s=time.perf_counter()-self.started,
            goal=self.goal, physical_robot_contact=self.first_contact is not None,
            contact_bodies=sorted(self.robot_contact_bodies), first_contact=self.first_contact,
            crossings=self.crossings, max_tilt_deg=self.max_tilt, min_pelvis_height_m=self.min_height,
            fall_observed=self.max_tilt > 70, max_penetration_m=self.max_penetration,
            max_actuator_force_nm=self.torque_peak, saturation_substeps=self.saturated_frames,
            finite=self.finite, max_root_displacement_m=float(np.linalg.norm(q[:, self.rq:self.rq+3]-self.initial[self.rq:self.rq+3], axis=1).max()),
            max_lateral_displacement_m=float(np.abs(q[:, self.rq+1]-self.initial[self.rq+1]).max()),
            final_pelvis_height_m=float(d.qpos[self.rq+2]), buffer_overflow=self.buffer_overflow,
            force_readback_difference_subcontacts=self.force_readback_differences,
            joint_motion_range_rad={self.model.joint(int(j)).name:float(v) for j,v in zip(self.robot_joints,ranges)},
            physics_contacts_source='native mujoco_warp.contact_force; no C recomputation',
            contact_time_resolution_s=float(self.model.opt.timestep))
        (folder/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        self.summaries.append(summary); self.active=False
        print(json.dumps(summary, indent=2), flush=True)

    def attach(self):
        def step():
            if not self.active: self.start()
            self.original_step()
            self.sample()
        def reset(ids):
            self.finish('reference_auto_or_manual_reset')
            return self.original_reset(ids)
        self.env.sim.step = step
        self.env._reset_idx = reset

    def detach(self):
        self.env.sim.step = self.original_step
        self.env._reset_idx = self.original_reset


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--cache', required=True, type=Path)
    p.add_argument('--episodes', type=int, default=5)
    p.add_argument('--seed', type=int, default=2810)
    p.add_argument('--viewer', action='store_true')
    a = p.parse_args()
    if a.episodes < 1: p.error('--episodes must be positive')
    a.reference = a.reference.resolve(); output = a.output.resolve(); output.mkdir(parents=True,exist_ok=False)
    configure_cache(a.cache)
    neural = probe(a.reference)
    if not all(neural['checks'].values()): raise ValueError('Neural contract failed')
    sys.path.insert(0,str(a.reference))
    import mjlab.tasks
    import src.tasks
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.utils.torch import configure_torch_backends
    configure_torch_backends()
    spec = importlib.util.spec_from_file_location('original_goalkeeper_eval',a.reference/'scripts/eval_naive_goalkeeper.py')
    original = importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=original; spec.loader.exec_module(original)
    cfg = load_env_cfg('Eval-Goalkeeper',play=False)
    cfg.scene.num_envs=1; cfg.seed=a.seed  # original CLI declared but ignored seed
    raw = ManagerBasedRlEnv(cfg=cfg,device='cpu')
    env = RslRlVecEnvWrapper(raw,clip_actions=100.0)
    monitor = Observer(raw,output)
    policy = original._load_policy(str(a.reference/'src/assets/soccer/weight/goalkeeper.pt'),env,'cpu')
    def observed_policy(obs):
        if not monitor.active: monitor.start()
        with torch.inference_mode(): action=policy(obs)
        monitor.actions.append(action.detach().cpu().numpy().reshape(-1).copy())
        return action
    monitor.attach()
    m=raw.sim.mj_model
    from src.tasks.soccer.mdp.goalkeeper_obs import _GK_JOINT_NAMES
    term = raw.action_manager.get_term('joint_pos')
    action_joint_names = [name.split('/')[-1] for name in term.target_names]
    if action_joint_names != list(_GK_JOINT_NAMES):
        env.close()
        raise ValueError('Action target ordering differs from the checkpoint contract')
    model_report=dict(nq=m.nq,nv=m.nv,nu=m.nu,dt=m.opt.timestep,gravity=m.opt.gravity.tolist(),
        integrator=int(m.opt.integrator), density=m.opt.density, viscosity=m.opt.viscosity,
        joint_names=[m.joint(i).name for i in range(m.njnt)],
        joint_qposadr=m.jnt_qposadr.tolist(),joint_dofadr=m.jnt_dofadr.tolist(),
        joint_ranges=m.jnt_range.tolist(),joint_limited=m.jnt_limited.tolist(),
        body_names=[m.body(i).name for i in range(m.nbody)],
        ball_qposadr=monitor.bq,robot_root_qposadr=monitor.rq,
        action_joint_names=action_joint_names, action_order_verified=True,
        actuator_names=[m.actuator(i).name for i in range(m.nu)],
        gainprm=m.actuator_gainprm.tolist(),biasprm=m.actuator_biasprm.tolist(),
        forcerange=m.actuator_forcerange.tolist(),forcerange_enabled=m.actuator_forcelimited.tolist())
    (output/'model.json').write_text(json.dumps(model_report,indent=2),encoding='utf-8')
    try:
        if a.viewer:
            from mjlab.viewer import NativeMujocoViewer
            viewer=NativeMujocoViewer(env,observed_policy,enable_perturbations=False)
            viewer.run(num_steps=a.episodes*150)
            monitor.finish('viewer_finished_or_closed')
        else:
            for _ in range(a.episodes):
                obs=env.reset()[0]
                # Start explicitly to keep the first action in the episode trace.
                monitor.start()
                for step in range(150):
                    with torch.inference_mode(): action=observed_policy(obs)
                    obs,_,done,_=env.step(action)
                    if bool(done.item()): break
                monitor.finish('evaluation_limit')
    finally:
        monitor.detach(); env.close()
    report=dict(episodes=monitor.summaries,seed=a.seed,viewer=a.viewer,
        requested_episodes=a.episodes,viewer_budget_decisions=a.episodes*150 if a.viewer else None,
        checkpoint_sha256=EXPECTED_SHA,neural_checks=neural['checks'],
        notes=['Reference model/gains/physics unchanged. Instance wrappers only observe steps and resets.',
               'Seed explicitly applied because original script ignores its CLI seed.',
               'No-contact non-goals are NOT saves. Contact alone is NOT proof of a save.'])
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__': main()
