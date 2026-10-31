"""Postmortem of complete or interrupted runs; never reclassifies acceptance."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from experiments.free_keeper4b.policy import JOINTS
from experiments.keeper_residual4b2.protocol import ACTIVE, DT
from .run import require_prefix


def describe(qpos, baseline):
    if len(qpos) > len(baseline) or not len(qpos):
        raise ValueError('Unaligned traces')
    t = np.arange(len(qpos))*DT
    delta = qpos[:, 7:36]-baseline[:len(qpos), 7:36]
    rows = []
    for start in range(8, 20):
        mask = (t >= start) & (t < start+1 if start < 19 else t <= 20)
        if not mask.any():
            continue
        values = delta[mask][:, ACTIVE]
        rows.append(dict(start_s=start, end_s=min(start+1, float(t[-1])),
            complete_interval=bool(t[-1] >= start+1),
            joint_mean_signed_rad=values.mean(axis=0).tolist(),
            joint_mean_abs_rad=np.abs(values).mean(axis=0).tolist(),
            joint_peak_abs_rad=np.abs(values).max(axis=0).tolist()))
    crossings = []
    for col in delta[t >= 8][::10][:, ACTIVE].T:
        signs = np.sign(col[np.abs(col) > 1e-5])
        crossings.append(int(np.count_nonzero(signs[1:] != signs[:-1])))
    return dict(observed_until_s=float(t[-1]), complete_20s=len(qpos) == 10001,
        evaluation_window_complete=bool(t[-1] >= 20),
        active_joint_names=[JOINTS[j] for j in ACTIVE], intervals=rows,
        descriptive_zero_crossings_50hz_deadband_1e_minus5_rad=crossings,
        final_signed_joint_errors_rad=delta[-1, ACTIVE].tolist(),
        note='Descriptive postmortem only. Acceptance remains in the original report.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--original-run', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    pair = a.run/'pair_01'
    with np.load(pair/'baseline/trace.npz') as f:
        baseline = f['qpos'].copy()
    with np.load(pair/'residual/trace.npz') as f:
        qpos = f['qpos'].copy()
    value = describe(qpos, baseline)
    value['baseline_prefix_exact'] = require_prefix(pair/'baseline/trace.npz', a.original_run/'baseline/trace.npz', True)
    value['residual_prefix_exact'] = require_prefix(pair/'residual/trace.npz', a.original_run/'trial_01/trace.npz')
    (a.output/'postmortem.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
    with (a.output/'error_evolution.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time_s', *[JOINTS[j]+'_error_rad' for j in ACTIVE], 'pelvis_error_m'])
        for i in range(0, len(qpos), 10):
            writer.writerow([i*DT, *(qpos[i, 7:36]-baseline[i, 7:36])[ACTIVE], qpos[i, 2]-baseline[i, 2]])
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()
