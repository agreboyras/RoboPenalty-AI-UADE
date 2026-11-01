"""External 4B.1 inference only. This process never creates a MuJoCo world."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deploy', type=Path, required=True)
    a = p.parse_args()
    import numpy as np
    from experiments.free_keeper4b.policy import Locomotion, JOINTS, POLICY_SHA
    with contextlib.redirect_stdout(io.StringIO()):
        policy = Locomotion(a.deploy)
    policy.reset()
    print(json.dumps(dict(home=policy.home.tolist(), kp=policy.kp.tolist(),
        kd=policy.kd.tolist(), limits=policy.source_torque_limits.tolist(),
        joints=JOINTS, checkpoint_sha256=POLICY_SHA,
        recurrent_reset_max=policy.recurrent_max(), physical_velocity_command=[0,0,0])),flush=True)
    for line in sys.stdin:
        msg = json.loads(line)
        if msg['op'] == 'stop':
            print(json.dumps(dict(seq=msg['seq'], normalizer_unchanged=policy.normalizer_unchanged())),flush=True)
            return
        if msg['op'] != 'observe': raise ValueError('Unknown inference operation')
        obs = policy.observe(*(np.asarray(msg[k],dtype=float) for k in ('q','dq','quaternion','omega')))
        target = policy.decide(obs)
        print(json.dumps(dict(seq=msg['seq'],observation=obs.tolist(),target=target.tolist()),allow_nan=False),flush=True)


if __name__ == '__main__': main()
