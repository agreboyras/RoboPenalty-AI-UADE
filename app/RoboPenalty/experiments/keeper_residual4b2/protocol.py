"""Protocol frozen before the first physical run. Amplitude has no CLI override."""
import numpy as np
from experiments.free_keeper4b.policy import JOINTS

STEPS = 5000
DT = 0.002
LIMITS = dict(max_roll_pitch_deg=15.0, max_drift_m=0.10, min_height_m=0.50,
              saturation_s=0.10, penetration_m=0.005, joint_tolerance_rad=1e-6,
              max_joint_speed_rad_s=8.0, torque_tolerance_nm=1e-9)
ACCEPTANCE = dict(knee_increase_each_rad=0.005, pelvis_drop_m=0.0005,
                  recovery_joint_mean_abs_rad=0.005, recovery_height_mean_abs_m=0.002)
AMPLITUDE = np.zeros(29)
for side in ('left', 'right'):
    for part, delta in (('hip_pitch', -0.01), ('knee', 0.02), ('ankle_pitch', -0.01)):
        AMPLITUDE[JOINTS.index(f'{side}_{part}_joint')] = delta
AMPLITUDE.setflags(write=False)
ACTIVE = np.flatnonzero(AMPLITUDE)
KNEES = [JOINTS.index(f'{side}_knee_joint') for side in ('left', 'right')]


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x*x*x*(10+x*(-15+6*x))


def residual(t):
    if t < 3:
        weight = 0.0
    elif t < 5:
        weight = smooth((t-3)/2)
    elif t < 6:
        weight = 1.0
    elif t < 8:
        weight = 1-smooth((t-6)/2)
    else:
        weight = 0.0
    return weight*AMPLITUDE


def safety_reason(height, tilt, drift, q, joint_ranges, dq, applied, torque_limits,
                  saturation_steps, improper, penetration, external, warnings):
    if not np.isfinite(np.r_[height, tilt, drift, q, dq, applied]).all():
        return 'nonfinite_state'
    if external:
        return 'external_force'
    if warnings:
        return 'mujoco_warning'
    if height < LIMITS['min_height_m']:
        return 'pelvis_height'
    if np.max(np.abs(tilt)) >= LIMITS['max_roll_pitch_deg']:
        return 'tilt'
    if drift >= LIMITS['max_drift_m']:
        return 'drift'
    if np.any(q < joint_ranges[:, 0]-LIMITS['joint_tolerance_rad']) or np.any(
            q > joint_ranges[:, 1]+LIMITS['joint_tolerance_rad']):
        return 'joint_limit'
    if np.max(np.abs(dq)) > LIMITS['max_joint_speed_rad_s']:
        return 'joint_speed'
    if np.any(np.abs(applied) > torque_limits+LIMITS['torque_tolerance_nm']):
        return 'torque_limit'
    if saturation_steps*DT >= LIMITS['saturation_s']:
        return 'persistent_saturation'
    if improper:
        return 'improper_contact'
    if penetration > LIMITS['penetration_m']:
        return 'penetration'
    return None


def compare(qpos, baseline):
    """POST-EPISODE only: aligned actual joint/pelvis states, never agent inputs."""
    if len(qpos) != STEPS+1 or qpos.shape != baseline.shape:
        return dict(success=False, reason='incomplete_or_unaligned')
    t = np.arange(STEPS+1)*DT
    plateau = (t >= 5.5) & (t < 6.0)
    recovered = (t >= 9.0) & (t <= 10.0)
    # Scene builder verifies this hinge order before using this evaluator.
    delta = qpos[:, 7:36]-baseline[:, 7:36]
    knees = delta[plateau][:, KNEES].mean(axis=0)
    drop = float((baseline[plateau, 2]-qpos[plateau, 2]).mean())
    returned = np.abs(delta[recovered][:, ACTIVE]).mean(axis=0)
    height_error = float(np.abs(qpos[recovered, 2]-baseline[recovered, 2]).mean())
    checks = dict(knees_each=bool(np.all(knees >= ACCEPTANCE['knee_increase_each_rad'])),
        pelvis_lowered=drop >= ACCEPTANCE['pelvis_drop_m'],
        joints_recovered=bool(np.all(returned <= ACCEPTANCE['recovery_joint_mean_abs_rad'])),
        height_recovered=height_error <= ACCEPTANCE['recovery_height_mean_abs_m'],
        pre_residual_exact=bool(np.array_equal(qpos[t <= 3], baseline[t <= 3])))
    return dict(success=all(checks.values()), checks=checks,
        knee_increase_rad=knees.tolist(), pelvis_drop_m=drop,
        recovery_joint_mean_abs_rad=returned.tolist(), recovery_height_mean_abs_m=height_error,
        plateau_joint_delta_rad=delta[plateau].mean(axis=0).tolist())
