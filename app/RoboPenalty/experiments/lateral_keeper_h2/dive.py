"""Joint references for a short manual dive from a crouched guard."""
import numpy as np

from experiments.free_keeper4b.policy import JOINTS
from .maneuver import interpolate


GUARD_S = 0.39
PUSH_S = 0.36
REACH_S = 0.31
LAND_S = 0.40
DURATION_S = 2.40


class Dive:
    def __init__(self, side):
        if side not in ('LEFT', 'RIGHT'):
            raise ValueError(f'Unknown side: {side}')
        # Sides are from the shooter's view. The keeper faces the shooter.
        self.sign = 1 if side == 'LEFT' else -1
        self.leading, self.trailing = ('right', 'left') if self.sign == 1 else ('left', 'right')
        joints = {name.removesuffix('_joint'): index for index, name in enumerate(JOINTS)}

        def set_angles(pose, **angles):
            for joint, angle in angles.items():
                pose[joints[joint]] = angle

        def bend(pose, leg, knee):
            # Compensate the flexion at hip and ankle to keep the foot flat.
            set_angles(pose, **{
                f'{leg}_knee': knee,
                f'{leg}_hip_pitch': -knee / 2 - .02,
                f'{leg}_ankle_pitch': -knee / 2 + .02,
            })

        guard = np.zeros(len(JOINTS))
        for leg, direction in (('left', 1), ('right', -1)):
            bend(guard, leg, .85)
            set_angles(guard, **{
                f'{leg}_hip_roll': direction * .10,
                f'{leg}_ankle_roll': -direction * .10,
                f'{leg}_shoulder_pitch': .35,
                f'{leg}_shoulder_roll': direction * .45,
                f'{leg}_elbow': .95,
            })

        push = guard.copy()
        bend(push, self.trailing, .48)
        bend(push, self.leading, 1.05)
        for leg in ('left', 'right'):
            roll = guard[joints[f'{leg}_hip_roll']] + self.sign * .26
            set_angles(push, **{
                f'{leg}_hip_roll': roll,
                f'{leg}_ankle_roll': np.clip(-roll, -.24, .24),
            })
        set_angles(push, waist_roll=self.sign * .13, **{
            f'{self.leading}_shoulder_roll': -self.sign * .98,
            f'{self.leading}_elbow': .85,
        })

        reach = push.copy()
        bend(reach, self.trailing, .74)
        bend(reach, self.leading, .88)
        set_angles(reach, **{
            f'{self.leading}_shoulder_roll': -self.sign * 1.12,
            f'{self.leading}_shoulder_pitch': -.05,
            f'{self.leading}_elbow': 1.12,
            f'{self.trailing}_elbow': 1.15,
        })

        land = reach.copy()
        set_angles(land, waist_roll=self.sign * .08, **{
            f'{self.leading}_shoulder_roll': -self.sign * .95,
            f'{self.leading}_elbow': 1.32,
        })

        self.guard = guard
        self.segments = (
            ('Impulso', PUSH_S, guard, push),
            ('Estirada', REACH_S, push, reach),
            ('Aterrizaje', LAND_S, reach, land),
        )

    def reference(self, time_s):
        elapsed = time_s - GUARD_S
        if elapsed < 0:
            return 'Guardia', self.guard
        for phase, duration, start, end in self.segments:
            if elapsed < duration:
                return phase, interpolate(start, end, elapsed / duration)
            elapsed -= duration
        return 'En el suelo', self.segments[-1][-1]
