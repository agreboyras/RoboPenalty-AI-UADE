"""Adapter for an external, hash-pinned locomotion TorchScript (no asset copies)."""
from pathlib import Path
import hashlib
import numpy as np
import yaml

POLICY_SHA = 'd1d91b0201beeb649a4624ba40052d10fe4aebe98bf6f4847decf75dd1fee2da'
CONFIG_SHA = '9be1972ff8f7b5cba57e428006d00a2b1c913b1d8253b5f1cb47294e286a8c0f'
DEPLOY_SHA = '90e51deaa22198e56fd638c117fe985f334c536a390bf0299ba1cadb0dbd3c7c'
JOINTS = tuple(f'{side}_{part}_joint' for side in ('left', 'right')
               for part in ('hip_pitch', 'hip_roll', 'hip_yaw', 'knee', 'ankle_pitch', 'ankle_roll')) + (
    'waist_yaw_joint', 'waist_roll_joint', 'waist_pitch_joint') + tuple(
    f'{side}_{part}_joint' for side in ('left', 'right') for part in (
        'shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow',
        'wrist_roll', 'wrist_pitch', 'wrist_yaw'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_config(path, expected):
    data = Path(path).read_bytes()
    if digest(data.replace(b'\r\n', b'\n')) != expected:
        raise ValueError(f'External configuration differs: {Path(path).name}')
    return yaml.safe_load(data)


def gravity_body(q):
    """World gravity direction rotated into the free-joint body frame (wxyz)."""
    w, x, y, z = q
    return np.array([2*(w*y-z*x), -2*(y*z+w*x), 1-2*(w*w+z*z)])


class Locomotion:
    def __init__(self, deploy):
        import torch
        self.torch = torch
        deploy = Path(deploy)
        path = deploy/'policy/loco_mode/model/policy_29dof.pt'
        if digest(path.read_bytes()) != POLICY_SHA:
            raise ValueError('External checkpoint SHA-256 mismatch')
        self.cfg = read_config(deploy/'policy/loco_mode/config/LocoMode.yaml', CONFIG_SHA)
        original = read_config(deploy/'deploy_mujoco/config/mujoco.yaml', DEPLOY_SHA)
        if (original['simulation_dt'], original['control_decimation']) != (0.002, 10):
            raise ValueError('Unverified control frequency')
        self.source_torque_limits = np.asarray(original['tau_limit'], dtype=float)
        c = self.cfg
        if c['num_obs'] != 96 or c['num_actions'] != 29 or c['action_scale'] != 0.25:
            raise ValueError('Unverified observation/action contract')
        self.mapping = np.asarray(c['joint2motor_idx'], dtype=int)
        if sorted(self.mapping.tolist()) != list(range(29)):
            raise ValueError('Joint mapping must be a permutation')
        self.default = np.asarray(c['default_angles'], dtype=np.float32)
        self.home = self.to_motor(self.default)
        self.kp = self.to_motor(np.asarray(c['kps'], dtype=float))
        self.kd = self.to_motor(np.asarray(c['kds'], dtype=float))
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        self.module = torch.jit.load(str(path), map_location='cpu').eval()
        if (tuple(self.module.hidden_state.shape), tuple(self.module.cell_state.shape)) != (
                (1, 1, 256), (1, 1, 256)):
            raise ValueError('Unverified recurrent state shape')
        if tuple(self.module.normalizer._mean.shape) != (1, 96):
            raise ValueError('Unverified normalizer shape')
        self.normalizer_before = {n: b.clone() for n, b in self.module.normalizer.named_buffers()}
        # Exactly the same observation clip and full exported normalizer/LSTM/actor.
        # Warm-up is not physics and is followed by explicit recurrent reset.
        with torch.inference_mode():
            for _ in range(50):
                out = self.module(torch.zeros((1, 96), dtype=torch.float32))
        if tuple(out.shape) != (1, 29) or not torch.isfinite(out).all():
            raise ValueError('Unverified output shape or nonfinite output')
        self.reset()

    def to_motor(self, policy_order):
        result = np.empty(29, dtype=float)
        result[self.mapping] = policy_order
        return result

    def reset(self):
        with self.torch.inference_mode():
            self.module.hidden_state.zero_()
            self.module.cell_state.zero_()
        self.last_action = np.zeros(29, dtype=np.float32)
        if self.recurrent_max() != 0.0:
            raise RuntimeError('Failed to reset LSTM')

    def recurrent_max(self):
        return max(float(self.module.hidden_state.abs().max()),
                   float(self.module.cell_state.abs().max()))

    def normalizer_unchanged(self):
        return all(self.torch.equal(b, self.normalizer_before[n])
                   for n, b in self.module.normalizer.named_buffers())

    def observe(self, q, dq, quaternion, omega):
        c = self.cfg
        # The original gathers into float32 qj_obs/dqj_obs BEFORE subtracting
        # the float32 default. Preserve that rounding, not only final dtype.
        q_policy = np.asarray(q[self.mapping], dtype=np.float32)
        dq_policy = np.asarray(dq[self.mapping], dtype=np.float32)
        obs = np.concatenate((np.asarray(omega)*c['ang_vel_scale'], gravity_body(quaternion),
            np.zeros(3), (q_policy-self.default)*c['dof_pos_scale'],
            dq_policy*c['dof_vel_scale'], self.last_action)).astype(np.float32)
        if obs.shape != (96,) or not np.isfinite(obs).all():
            raise ValueError('Invalid observation')
        return obs

    def decide(self, obs):
        with self.torch.inference_mode():
            action = self.module(self.torch.from_numpy(obs[None]).clamp(-100, 100))
            action = action.clamp(-100, 100).numpy().reshape(29).copy()
        if not np.isfinite(action).all():
            raise ValueError('Nonfinite action')
        self.last_action = action
        return self.to_motor(self.default + self.cfg['action_scale']*action)
