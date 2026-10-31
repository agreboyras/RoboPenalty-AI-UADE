"""Independent 20-second diagnostic. The owned 4B.2 physical loop is preserved,
with only duration, zero-residual reference selection and post-run evaluator
changed. No original module globals are patched or rewritten."""
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
from experiments.free_keeper4b.run_trial import angles
from experiments.keeper_residual4b2.run import check_contacts, write_json, old_trace, BASELINE_HASH
from .protocol import DT, STEPS, LIMITS, ACCEPTANCE, residual, safety_reason, compare

def trial(policy, xml, directory, baseline, viewer=False, residual_enabled=True):
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
                offset = residual(step*DT) if residual_enabled else np.zeros(29)
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
    motion = compare(arrays['qpos'], baseline) if baseline is not None else dict(success=True, reference_only=True)
    safe = stopped is None and len(states) == STEPS+1 and decisions == 1000 and policy.normalizer_unchanged()
    measured = dict(steps=len(states)-1, decisions=decisions, simulated_s=float(d.time), wall_s=wall_s,
        min_height_m=float(min_height), max_roll_pitch_deg=max_tilt, max_drift_m=max_drift,
        max_joint_speed_rad_s=max_speed, max_penetration_m=max_penetration,
        max_saturation_s=max_sat*DT, reference_clips=clips, improper_contact_steps=improper_steps,
        max_requested_torque_nm=float(np.abs(arrays['requested_torque']).max()) if len(records['control']) else 0,
        max_applied_torque_nm=float(np.abs(arrays['actual_torque']).max()) if len(records['control']) else 0,
        recurrent_reset_max=reset_max, normalizer_unchanged=policy.normalizer_unchanged(), stopped=stopped)
    digest = hashlib.sha256(b''.join(arrays[k].tobytes() for k in sorted(arrays))).hexdigest()
    summary = dict(residual_enabled=residual_enabled, safe=safe, success=safe and motion['success'], metrics=measured, motion=motion,
        physical_trace_sha256=digest, policy_sha256=POLICY_SHA,
        model_sha256=hashlib.sha256(Path(xml).read_bytes()).hexdigest(),
        safety_limits=LIMITS, motion_acceptance=ACCEPTANCE, torque_limits_nm=caps.tolist())
    write_json(directory/'summary.json', summary)
    return summary


def fingerprint():
    here = Path(__file__).resolve().parent
    paths = [here/'run.py', here/'protocol.py']
    for folder, files in [('free_keeper4b', ['policy.py', 'scene.py', 'run_trial.py']),
                          ('keeper_residual4b2', ['protocol.py', 'run.py'])]:
        paths.extend(here.parent/folder/name for name in files)
    return hashlib.sha256(b''.join(p.read_bytes() for p in paths)).hexdigest()


def require_prefix(new_path, old_path, old_format=False):
    """Read-only audit after physics; no future/reference data given to policy."""
    with np.load(new_path) as new, np.load(old_path) as old:
        if old_format:
            expected_q = np.vstack((old['trace'][:, 1:37], old['final_qpos']))
            expected_v = np.vstack((old['trace'][:, 37:72], old['final_qvel']))
            items = [('qpos', expected_q), ('qvel', expected_v),
                     ('requested_torque', old['trace'][:, 72:101]),
                     ('control', old['trace'][:, 101:130]),
                     ('actual_torque', old['trace'][:, 130:159]),
                     ('final_target', old['trace'][:, 159:188]),
                     ('policy_target', np.repeat(old['decisions'][:, 97:126], 10, axis=0)),
                     ('decision_observation', old['decisions'][:, 1:97])]
        else:
            items = [(name, old[name]) for name in old.files]
        mismatches = [name for name, expected in items
                      if not np.array_equal(new[name][:len(expected)], expected)]
    if mismatches:
        raise ValueError('Original 10-second prefix diverged: '+', '.join(mismatches))
    return [name for name, _ in items]


def viewer_gate(path):
    report = json.loads((path/'report.json').read_text(encoding='utf-8'))
    if not report.get('viewer_enabled') or report.get('code_sha256') != fingerprint():
        raise ValueError('Viewer blocked: extended recovery not approved or code changed')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deploy', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--original-run', required=True, type=Path)
    p.add_argument('--viewer', action='store_true')
    p.add_argument('--validated-run', type=Path)
    a = p.parse_args()
    if a.viewer and not a.validated_run:
        p.error('--viewer requires --validated-run')
    if a.viewer:
        try:
            approved = viewer_gate(a.validated_run)
        except ValueError as e:
            p.error(str(e))
    _, old_hash = old_trace(a.original_run/'baseline/trace.npz')
    if old_hash != BASELINE_HASH:
        raise ValueError('Original reference integrity mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    policy = Locomotion(a.deploy)
    xml = Path(__file__).resolve().parents[4]/'app/unitree_mujoco/unitree_robots/g1/g1_29dof.xml'
    pairs = []
    for i in range(1 if a.viewer else 3):
        pair = a.output/f'pair_{i+1:02d}'
        pair.mkdir()
        if a.viewer:
            baseline_path = a.validated_run/'pair_01/baseline/trace.npz'
            with np.load(baseline_path) as saved:
                baseline = saved['qpos'].copy()
        else:
            base = trial(policy, xml, pair/'baseline', None, residual_enabled=False)
            if not base['safe']:
                pairs.append(dict(baseline=base, residual=None, prefixes_exact=False))
                break
            checked_base = require_prefix(pair/'baseline/trace.npz', a.original_run/'baseline/trace.npz', True)
            with np.load(pair/'baseline/trace.npz') as saved:
                baseline = saved['qpos'].copy()
        result = trial(policy, xml, pair/'residual', baseline, viewer=a.viewer)
        checked_res = require_prefix(pair/'residual/trace.npz', a.original_run/'trial_01/trace.npz') if result['safe'] else []
        entry = dict(baseline=base if not a.viewer else None, residual=result,
                     prefixes_exact=bool(checked_res),
                     prefix_arrays=dict(baseline=checked_base if not a.viewer else [], residual=checked_res))
        pairs.append(entry)
        print(json.dumps(dict(pair=i+1, success=result['success'], metrics=result['metrics'],
                              checks=result['motion'].get('checks')), indent=2), flush=True)
        if not result['safe']:
            break
    success = len(pairs) == (1 if a.viewer else 3) and all(
        x['residual'] is not None and x['residual']['success'] and x['prefixes_exact'] and
        (a.viewer or x['baseline']['safe']) for x in pairs)
    base_hashes = [x['baseline']['physical_trace_sha256'] for x in pairs if x['baseline']]
    res_hashes = [x['residual']['physical_trace_sha256'] for x in pairs if x['residual']]
    reproducible = not a.viewer and len(pairs) == 3 and len(set(base_hashes)) == len(set(res_hashes)) == 1
    if a.viewer:
        matches = res_hashes == [approved['residual_hashes'][0]]
    else:
        matches = None
    report = dict(success=success and (reproducible if not a.viewer else matches),
        viewer_enabled=not a.viewer and success and reproducible, pairs=len(pairs),
        exactly_reproducible=reproducible, viewer_matches_headless=matches,
        baseline_hashes=base_hashes, residual_hashes=res_hashes, code_sha256=fingerprint())
    write_json(a.output/'report.json', report)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
