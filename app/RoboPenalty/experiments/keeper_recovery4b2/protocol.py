"""Extended observation period, frozen before execution; same residual/safety."""
import numpy as np
from experiments.keeper_residual4b2.protocol import (
    DT, LIMITS, ACCEPTANCE as ORIGINAL_ACCEPTANCE, ACTIVE, KNEES, residual, safety_reason)

STEPS = 10000
ACCEPTANCE = dict(ORIGINAL_ACCEPTANCE, duration_s=20.0,
                  evaluation_start_s=18.0, evaluation_end_s=20.0,
                  recovery_joint_peak_abs_rad=0.005)


def compare(qpos, baseline):
    """All reference comparisons are post-episode, with a 20 s moving baseline."""
    if qpos.shape != (STEPS+1, 36) or qpos.shape != baseline.shape:
        return dict(success=False, reason='incomplete_or_unaligned')
    t = np.arange(STEPS+1)*DT
    dq = qpos[:, 7:36]-baseline[:, 7:36]
    dz = qpos[:, 2]-baseline[:, 2]
    flex = (t >= 5.5) & (t < 6)
    old = (t >= 9) & (t <= 10)
    late = (t >= 18) & (t <= 20)
    knee = dq[flex][:, KNEES].mean(axis=0)
    drop = -float(dz[flex].mean())
    old_mean = np.abs(dq[old][:, ACTIVE]).mean(axis=0)
    mean = np.abs(dq[late][:, ACTIVE]).mean(axis=0)
    peak = np.abs(dq[late][:, ACTIVE]).max(axis=0)
    height = float(np.abs(dz[late]).mean())
    checks = dict(knees_each=bool(np.all(knee >= 0.005)), pelvis_lowered=drop >= 0.0005,
        joints_recovered_mean=bool(np.all(mean <= 0.005)),
        joints_recovered_peak=bool(np.all(peak <= 0.005)), height_recovered=height <= 0.002,
        pre_residual_exact=bool(np.array_equal(qpos[t <= 3], baseline[t <= 3])))
    history = []
    for start in range(8, 20):
        mask = (t >= start) & (t < start+1 if start < 19 else t <= 20)
        values = dq[mask][:, ACTIVE]
        history.append(dict(start_s=start, end_s=start+1,
            joint_mean_signed_rad=values.mean(axis=0).tolist(),
            joint_mean_abs_rad=np.abs(values).mean(axis=0).tolist(),
            joint_peak_abs_rad=np.abs(values).max(axis=0).tolist(),
            pelvis_mean_abs_m=float(np.abs(dz[mask]).mean())))
    # Describe reversals at 50 Hz with a 1e-5 rad deadband; this is descriptive,
    # never an altered acceptance threshold or proof of asymptotic convergence.
    sampled = dq[t >= 8][::10][:, ACTIVE]
    crossings = []
    for col in sampled.T:
        sign = np.sign(col[np.abs(col) > 1e-5])
        crossings.append(int(np.count_nonzero(sign[1:] != sign[:-1])))
    return dict(success=all(checks.values()), checks=checks,
        knee_increase_rad=knee.tolist(), pelvis_drop_m=drop,
        original_window_mean_abs_rad=old_mean.tolist(),
        original_joint_recovery_pass=bool(np.all(old_mean <= 0.005)),
        recovery_joint_mean_abs_rad=mean.tolist(), recovery_joint_peak_abs_rad=peak.tolist(),
        recovery_height_mean_abs_m=height, all_29_joint_mean_abs_rad=np.abs(dq[late]).mean(axis=0).tolist(),
        final_joint_error_rad=dq[-1, ACTIVE].tolist(),
        zero_crossings_8_to_20= crossings, history=history)
