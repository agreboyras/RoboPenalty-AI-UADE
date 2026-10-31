"""Real MuJoCo render of recorded states; never changes a running experiment."""
import argparse
from pathlib import Path
import struct
import zlib
import mujoco
import numpy as np
from .policy import Locomotion
from .scene import build


def png(path, rgb):
    def chunk(kind, data):
        return struct.pack('!I', len(data))+kind+data+struct.pack('!I', zlib.crc32(kind+data))
    height, width, _ = rgb.shape
    rows = b''.join(b'\0'+row.tobytes() for row in rgb)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))+
                     chunk(b'IDAT', zlib.compress(rows))+chunk(b'IEND', b''))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deploy', required=True, type=Path)
    p.add_argument('--trial', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    policy = Locomotion(a.deploy)
    xml = Path(__file__).resolve().parents[3]/'unitree_mujoco/unitree_robots/g1/g1_29dof.xml'
    m, d, *_ = build(xml, policy.home, policy.source_torque_limits)
    m.vis.global_.offwidth, m.vis.global_.offheight = 960, 720
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.lookat[:] = [0, 0, 0.75]
    cam.distance, cam.azimuth, cam.elevation = 2.5, 135, -12
    # Setting qpos here only restores a recorded state for a still image.
    # There is no integration, policy correction or equilibrium assistance.
    with np.load(a.trial/'trace.npz') as trace, mujoco.Renderer(m, height=720, width=960) as renderer:
        for name, q, v in [('initial', trace['initial_qpos'], np.zeros(m.nv)),
                           ('final', trace['final_qpos'], trace['final_qvel'])]:
            d.qpos[:], d.qvel[:] = q, v
            mujoco.mj_forward(m, d)
            renderer.update_scene(d, camera=cam)
            png(a.output/f'{name}.png', renderer.render())
    print(str(a.output))


if __name__ == '__main__':
    main()
