"""Isolated residual trial, with strict post-episode comparison and viewer gate."""
import argparse
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import time
import mujoco
import numpy as np
from experiments.free_keeper4b.policy import Locomotion, POLICY_SHA
from experiments.free_keeper4b.scene import build
from experiments.free_keeper4b.run_trial import run as baseline_run, angles
from .protocol import DT, STEPS, LIMITS, ACCEPTANCE, ACTIVE, residual, safety_reason, compare

BASELINE_HASH = '9262984851026d428ebb4841ea5dfeb6adea49cd206b736059e201a8f9cbfcf4'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def code_hash():
    here = Path(__file__).resolve().parent
    paths = [here/'run.py', here/'protocol.py'] + [here.parent/'free_keeper4b'/name
                for name in ('policy.py', 'scene.py', 'run_trial.py')]
    return hashlib.sha256(b''.join(p.read_bytes() for p in paths)).hexdigest()


def old_trace(path):
    with np.load(path) as f:
        hashed = hashlib.sha256(f['trace'].tobytes()+f['decisions'].tobytes()+
                               f['final_qpos'].tobytes()+f['final_qvel'].tobytes()).hexdigest()
        qpos = np.vstack((f['trace'][:, 1:37], f['final_qpos']))
    return qpos, hashed


def check_contacts(model, data, floor, feet):
    rows, bad, penetration = [], False, 0.0
    for i in range(data.ncon):
        c = data.contact[i]
        a, b = int(c.geom1), int(c.geom2)
        body = int(model.geom_bodyid[b if a == floor else a])
        allowed = (a == floor or b == floor) and body in feet
        force = np.zeros(6)
        mujoco.mj_contactForce(model, data, i, force)
        bad |= not allowed
        penetration = max(penetration, float(max(0, -c.dist)))
        rows.append(dict(geoms=[a, b], distance=float(c.dist), position=c.pos.tolist(),
                         force=force.tolist(), allowed=allowed))
    return rows, bad, penetration


def trial(policy, xml, directory, baseline, viewer=False):
    directory.mkdir(parents=True, exist_ok=False)
    policy.reset()
    reset_max = policy.recurrent_max()
    m, d, qa, va, jid, caps, feet = build(xml, policy.home, policy.source_torque_limits)
    if not np.array_equal(qa, np.arange(7, 36)):
        raise ValueError('Unexpected joint ordering for comparison')
    floor = m.geom('balance_floor').id
    initial = d.qpos.copy()
    states, speeds, times = [initial], [d.qvel.copy()], [0.0]
    records = {k: [] for k in ('policy_target', 'residual', 'final_target', 'requested_torque',
                              'control', 'actual_torque', 'decision_observation', 'policy_action')}
    sat = np.zeros(29, dtype=int)
    max_sat, clips, improper_steps, decisions = 0, 0, 0, 0
    max_penetration, min_height, max_tilt, max_drift, max_speed = 0.0, initial[2], 0.0, 0.0, 0.0
    raw = target = policy.home.copy()
    offset = np.zeros(29)
    stopped = None
    if viewer:
        from mujoco import viewer as mjviewer
        context = mjviewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False)
    else:
        context = nullcontext(None)
    started = time.perf_counter()
    with context as handle, (directory/'contacts.jsonl').open('w', encoding='utf-8') as contact_file:
        if handle:
            handle.cam.lookat[:] = [0, 0, 0.8]
            handle.cam.distance, handle.cam.azimuth, handle.cam.elevation = 2.8, 135, -15
        wall_start = time.perf_counter()
        for step in range(STEPS):
            if handle and not handle.is_running():
                stopped = 'viewer_closed'
                break
            if step % 10 == 0:
                obs = policy.observe(d.qpos[qa], d.qvel[va], d.qpos[3:7], d.qvel[3:6])
                raw = policy.decide(obs)  # updates only original raw-action history
                offset = residual(step*DT)
                target = np.clip(raw+offset, m.jnt_range[jid, 0], m.jnt_range[jid, 1])
                clips += int(np.count_nonzero(raw+offset != target))
                records['decision_observation'].append(obs.copy())
                records['policy_action'].append(policy.last_action.copy())
                decisions += 1
            requested = policy.kp*(target-d.qpos[qa])-policy.kd*d.qvel[va]
            d.ctrl[:] = np.clip(requested, -caps, caps)  # sole actuator writer
            sat = np.where(np.abs(requested) >= caps, sat+1, 0)
            max_sat = max(max_sat, int(sat.max()))
            mujoco.mj_forward(m, d)
            rows, bad, penetration = check_contacts(m, d, floor, feet)
            improper_steps += int(bad)
            max_penetration = max(max_penetration, penetration)
            contact_file.write(json.dumps(dict(step=step, time=float(d.time), contacts=rows))+'\n')
            warning = any(w.number for w in d.warning)
            reason = safety_reason(float(d.qpos[2]), angles(d.qpos[3:7]),
                float(np.linalg.norm(d.qpos[:2]-initial[:2])), d.qpos[qa], m.jnt_range[jid],
                d.qvel[va], d.qfrc_actuator[va], caps, int(sat.max()), bad, penetration,
                bool(np.any(d.xfrc_applied) or np.any(d.qfrc_applied)), warning)
            if reason:
                stopped = reason
                break
            for key, value in [('policy_target', raw), ('residual', offset), ('final_target', target),
                               ('requested_torque', requested), ('control', d.ctrl),
                               ('actual_torque', d.qfrc_actuator[va])]:
                records[key].append(value.copy())
            mujoco.mj_step(m, d)
            states.append(d.qpos.copy()); speeds.append(d.qvel.copy()); times.append(float(d.time))
            tilt = float(np.abs(angles(d.qpos[3:7])).max())
            drift = float(np.linalg.norm(d.qpos[:2]-initial[:2]))
            min_height = min(min_height, float(d.qpos[2]))
            max_tilt, max_drift = max(max_tilt, tilt), max(max_drift, drift)
            max_speed = max(max_speed, float(np.abs(d.qvel[va]).max()))
            # Check the integrated state immediately, including the final step.
            stopped = safety_reason(float(d.qpos[2]), angles(d.qpos[3:7]), drift,
                d.qpos[qa], m.jnt_range[jid], d.qvel[va], d.qfrc_actuator[va], caps,
                int(sat.max()), False, 0.0,
                bool(np.any(d.xfrc_applied) or np.any(d.qfrc_applied)), any(w.number for w in d.warning))
            if stopped:
                break
            if handle:
                if step % 16 == 0:
                    handle.sync()
                time.sleep(max(0.0, wall_start+(step+1)*DT-time.perf_counter()))
        if handle:
            handle.sync()
    wall_s = time.perf_counter()-started
    # Final contact check, no further integration or recovery action.
    if stopped is None:
        mujoco.mj_forward(m, d)
        rows, bad, penetration = check_contacts(m, d, floor, feet)
        max_penetration = max(max_penetration, penetration)
        if bad or penetration > LIMITS['penetration_m']:
            stopped = 'final_contact_or_penetration'
    arrays = {k: np.asarray(v) for k, v in records.items()}
    arrays.update(qpos=np.asarray(states), qvel=np.asarray(speeds), time=np.asarray(times))
    np.savez_compressed(directory/'trace.npz', **arrays)
    motion = compare(arrays['qpos'], baseline)
    safe = stopped is None and len(states) == STEPS+1 and decisions == 500 and policy.normalizer_unchanged()
    measured = dict(steps=len(states)-1, decisions=decisions, simulated_s=float(d.time), wall_s=wall_s,
        min_height_m=float(min_height), max_roll_pitch_deg=max_tilt, max_drift_m=max_drift,
        max_joint_speed_rad_s=max_speed, max_penetration_m=max_penetration,
        max_saturation_s=max_sat*DT, reference_clips=clips, improper_contact_steps=improper_steps,
        max_requested_torque_nm=float(np.abs(arrays['requested_torque']).max()) if len(records['control']) else 0,
        max_applied_torque_nm=float(np.abs(arrays['actual_torque']).max()) if len(records['control']) else 0,
        recurrent_reset_max=reset_max, normalizer_unchanged=policy.normalizer_unchanged(), stopped=stopped)
    digest = hashlib.sha256(b''.join(arrays[k].tobytes() for k in sorted(arrays))).hexdigest()
    summary = dict(safe=safe, success=safe and motion['success'], metrics=measured, motion=motion,
        physical_trace_sha256=digest, policy_sha256=POLICY_SHA,
        model_sha256=hashlib.sha256(Path(xml).read_bytes()).hexdigest(),
        safety_limits=LIMITS, motion_acceptance=ACCEPTANCE, torque_limits_nm=caps.tolist())
    write_json(directory/'summary.json', summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deploy', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--viewer', action='store_true')
    p.add_argument('--validated-run', type=Path)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[4]
    xml = root/'app/unitree_mujoco/unitree_robots/g1/g1_29dof.xml'
    if a.viewer:
        if not a.validated_run:
            p.error('Viewer requires --validated-run with three accepted headless repetitions')
        report = json.loads((a.validated_run/'report.json').read_text(encoding='utf-8'))
        if not report['viewer_enabled'] or report['code_sha256'] != code_hash():
            p.error('Viewer disabled: headless motion/recovery criteria failed or code changed')
        baseline, hashed = old_trace(a.validated_run/'baseline/trace.npz')
    a.output.mkdir(parents=True, exist_ok=False)
    policy = Locomotion(a.deploy)
    if not a.viewer:
        summary = baseline_run(policy, xml, a.output/'baseline')
        baseline, hashed = old_trace(a.output/'baseline/trace.npz')
        if not summary['success'] or hashed != BASELINE_HASH:
            write_json(a.output/'report.json', dict(viewer_enabled=False, reason='baseline_diverged', baseline_hash=hashed))
            raise SystemExit('Reference 4B.1 diverged; no residual trials executed')
    if hashed != BASELINE_HASH:
        raise ValueError('Unverified baseline')
    results = []
    for i in range(1 if a.viewer else 3):
        result = trial(policy, xml, a.output/f'trial_{i+1:02d}', baseline, a.viewer)
        results.append(result)
        print(json.dumps(dict(trial=i+1, **result), indent=2), flush=True)
        if not result['safe']:
            break  # do not repeat an unsafe physical maneuver
    reproducible = len(results) == 3 and len({r['physical_trace_sha256'] for r in results}) == 1
    report = dict(viewer_enabled=not a.viewer and reproducible and all(r['success'] for r in results),
        all_safe=all(r['safe'] for r in results), all_success=all(r['success'] for r in results),
        repetitions=len(results), exactly_reproducible=reproducible, code_sha256=code_hash(),
        baseline_hash=hashed)
    write_json(a.output/'report.json', report)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['all_success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
