"""Ten seconds of genuine free-base dynamics, with optional live passive viewer."""
import argparse
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import time
import mujoco
import numpy as np
from .policy import Locomotion, POLICY_SHA
from .scene import build

# Frozen before any physical trial. No CLI overrides for acceptance thresholds.
CRITERIA = dict(duration_s=10.0, steps=5000, decisions=500,
                max_tilt_deg=15.0, max_drift_m=0.10, fall_height_m=0.50,
                persistent_saturation_s=0.10, joint_tolerance_rad=1e-6)


def evaluate(metrics):
    return dict(complete=metrics['steps'] == 5000 and metrics['decisions'] == 500,
        no_fall=metrics['min_pelvis_height_m'] >= CRITERIA['fall_height_m'],
        tilt=metrics['max_tilt_deg'] < 15.0, drift=metrics['max_drift_m'] < 0.10,
        feet_only=metrics['improper_contact_steps'] == 0,
        no_persistent_saturation=metrics['max_saturation_run_s'] < 0.10,
        joint_limits=metrics['joint_limit_violation_steps'] == 0,
        finite=metrics['finite'], no_external_forces=metrics['no_external_forces'],
        normalizer_frozen=metrics['normalizer_unchanged'])


def angles(q):
    w, x, y, z = q
    return np.degrees([np.arctan2(2*(w*x+y*z), 1-2*(x*x+y*y)),
                       np.arcsin(np.clip(2*(w*y-z*x), -1, 1))])


def run(policy, xml, output, viewer=False):
    output.mkdir(parents=True, exist_ok=False)
    policy.reset()
    reset_max = policy.recurrent_max()
    model, data, qa, va, jid, torque_limits, feet = build(xml, policy.home, policy.source_torque_limits)
    floor = model.geom('balance_floor').id
    root = model.body('pelvis').id
    root_joint = int(np.flatnonzero(model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)[0])
    root_qa = int(model.jnt_qposadr[root_joint])
    root_va = int(model.jnt_dofadr[root_joint])
    initial = data.qpos.copy()
    target = policy.home.copy()
    sat_run = np.zeros(29, dtype=int)
    max_sat_run = 0
    frames, decisions = [], []
    improper, joint_bad, clips = 0, 0, 0
    max_penetration = 0.0
    finite, no_external = True, True
    completed, stopped = 0, 'completed'
    if viewer:
        from mujoco import viewer as mjviewer
        context = mjviewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False)
    else:
        context = nullcontext(None)
    started = time.perf_counter()
    with context as handle, (output/'contacts.jsonl').open('w', encoding='utf-8') as contacts:
        if handle:
            handle.cam.lookat[:] = [0, 0, 0.8]
            handle.cam.distance = 2.8
            handle.cam.azimuth = 135
            handle.cam.elevation = -15
        wall_start = time.perf_counter()
        for step in range(5000):
            if handle and not handle.is_running():
                stopped = 'viewer_closed_early'
                break
            if np.any(data.xfrc_applied) or np.any(data.qfrc_applied):
                no_external, stopped = False, 'external_force_detected'
                break
            if step % 10 == 0:
                obs = policy.observe(data.qpos[qa], data.qvel[va],
                    data.qpos[root_qa+3:root_qa+7], data.qvel[root_va+3:root_va+6])
                raw_target = policy.decide(obs)
                target = np.clip(raw_target, model.jnt_range[jid, 0], model.jnt_range[jid, 1])
                clips += int(np.count_nonzero(raw_target != target))
                decisions.append(np.concatenate(([data.time], obs, raw_target, target)))
            requested = policy.kp*(target-data.qpos[qa]) - policy.kd*data.qvel[va]
            data.ctrl[:] = np.clip(requested, -torque_limits, torque_limits)
            saturated = np.abs(requested) >= torque_limits
            sat_run = np.where(saturated, sat_run+1, 0)
            max_sat_run = max(max_sat_run, int(sat_run.max()))
            # Forward once so contacts/forces correspond to this exact pre-step state/control.
            mujoco.mj_forward(model, data)
            contact_rows, bad = [], False
            for i in range(data.ncon):
                c = data.contact[i]
                a, b = int(c.geom1), int(c.geom2)
                force = np.zeros(6)
                mujoco.mj_contactForce(model, data, i, force)
                body = int(model.geom_bodyid[b if a == floor else a])
                allowed = (a == floor or b == floor) and body in feet
                # Include self contacts too; no filtering of unfavorable evidence.
                bad |= not allowed
                max_penetration = max(max_penetration, float(max(0, -c.dist)))
                contact_rows.append(dict(geoms=[a, b], position=c.pos.tolist(),
                                         distance=float(c.dist), force=force.tolist(), allowed=allowed))
            improper += int(bad)
            q = data.qpos[qa]
            joint_bad += int(np.any(q < model.jnt_range[jid, 0]-1e-6) or
                             np.any(q > model.jnt_range[jid, 1]+1e-6))
            contacts.write(json.dumps(dict(step=step, time=float(data.time), contacts=contact_rows))+'\n')
            # qpos/qvel and force arrays are all from the same pre-integration state.
            frames.append(np.concatenate(([data.time], data.qpos, data.qvel, requested,
                data.ctrl, data.qfrc_actuator[va], target, angles(data.qpos[root_qa+3:root_qa+7]),
                [data.ncon])))
            mujoco.mj_step(model, data)
            completed += 1
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                finite, stopped = False, 'nonfinite_state'
                break
            if handle:
                if step % 16 == 0:
                    handle.sync()
                time.sleep(max(0.0, wall_start+completed*0.002-time.perf_counter()))
        if handle:
            handle.sync()
    wall = time.perf_counter()-started
    trace = np.asarray(frames, dtype=float).reshape((-1, 191))
    qposes = np.vstack((trace[:, 1:37], data.qpos)) if len(trace) else data.qpos[None]
    tilts = np.asarray([angles(q[root_qa+3:root_qa+7]) for q in qposes])
    warnings = {str(i): int(w.number) for i, w in enumerate(data.warning) if w.number}
    metrics = dict(steps=completed, decisions=len(decisions), simulated_s=float(data.time), wall_s=wall,
        initial_pelvis_height_m=float(initial[root_qa+2]), min_pelvis_height_m=float(qposes[:, root_qa+2].min()),
        final_pelvis_height_m=float(data.qpos[root_qa+2]),
        max_tilt_deg=float(np.abs(tilts).max()),
        max_drift_m=float(np.linalg.norm(qposes[:, root_qa:root_qa+2]-initial[root_qa:root_qa+2], axis=1).max()),
        improper_contact_steps=improper, joint_limit_violation_steps=joint_bad,
        max_saturation_run_s=max_sat_run*0.002, reference_clip_count=clips,
        max_penetration_m=max_penetration, finite=finite, no_external_forces=no_external,
        recurrent_max_after_reset=reset_max, normalizer_unchanged=policy.normalizer_unchanged(),
        warnings=warnings, stopped=stopped)
    checks = evaluate(metrics)
    checks['no_warnings'] = not warnings
    summary = dict(criteria=CRITERIA, metrics=metrics, checks=checks,
        success=all(checks.values()), policy_sha256=POLICY_SHA,
        model_xml_sha256=hashlib.sha256(Path(xml).read_bytes()).hexdigest(),
        command_m_s_rad_s=[0, 0, 0], torque_limits_nm=torque_limits.tolist(),
        versions=dict(mujoco=mujoco.__version__, numpy=np.__version__, torch=policy.torch.__version__),
        trace_columns=dict(time=[0,1], qpos=[1,37], qvel=[37,72], requested_torque=[72,101],
            control=[101,130], actual_joint_actuator_torque=[130,159], target=[159,188],
            roll_pitch_deg=[188,190], ncon=[190,191]),
        decision_columns=dict(time=[0,1], observation=[1,97], raw_target=[97,126], safe_target=[126,155]))
    np.savez_compressed(output/'trace.npz', trace=trace, decisions=np.asarray(decisions).reshape((-1, 155)),
                        initial_qpos=initial, final_qpos=data.qpos.copy(), final_qvel=data.qvel.copy())
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deploy', type=Path, required=True, help='External Deploy; read only')
    parser.add_argument('--xml', type=Path, default=Path(__file__).resolve().parents[3]/'unitree_mujoco/unitree_robots/g1/g1_29dof.xml')
    parser.add_argument('--output', type=Path, required=True, help='New directory; never overwrite trials')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--viewer', action='store_true')
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    policy = Locomotion(args.deploy)
    args.output.mkdir(parents=True, exist_ok=False)
    summaries = []
    hashes = []
    for i in range(args.repeats):
        directory = args.output/f'trial_{i+1:02d}'
        summary = run(policy, args.xml, directory, args.viewer)
        summaries.append(summary)
        with np.load(directory/'trace.npz') as t:
            hashes.append(hashlib.sha256(t['trace'].tobytes()+t['decisions'].tobytes()+
                t['final_qpos'].tobytes()+t['final_qvel'].tobytes()).hexdigest())
        print(json.dumps(dict(trial=i+1, **summary['metrics'], success=summary['success']), indent=2), flush=True)
        if summary['metrics']['stopped'] != 'completed':
            break
    report = dict(success=all(s['success'] for s in summaries), repeats=len(summaries),
                  physical_trace_hashes=hashes, exactly_reproducible=len(set(hashes)) == 1)
    (args.output/'comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
