"""MuJoCo renders of saved Warp states: playback only, never a second simulation."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from .environment import configure_cache


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',required=True,type=Path)
    p.add_argument('--recording',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--cache',required=True,type=Path)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    configure_cache(a.cache)
    sys.path.insert(0,str(a.reference.resolve()))
    import mjlab.tasks
    import src.tasks
    from mjlab.tasks.registry import load_env_cfg
    from mjlab.envs import ManagerBasedRlEnv
    import mujoco
    import imageio.v2 as imageio
    from PIL import Image,ImageDraw
    cfg=load_env_cfg('Eval-Goalkeeper',play=False);cfg.scene.num_envs=1;cfg.seed=2810
    env=ManagerBasedRlEnv(cfg=cfg,device='cpu')
    m=env.sim.mj_model; d=mujoco.MjData(m)
    m.vis.global_.offwidth=640;m.vis.global_.offheight=480
    cam=mujoco.MjvCamera();mujoco.mjv_defaultCamera(cam)
    cam.lookat[:]=[1.0,0,0.7];cam.distance=7.5;cam.azimuth=90;cam.elevation=-12
    files=sorted(a.recording.glob('episode_*/trace.npz'))[:2]
    counts=[]
    try:
        with mujoco.Renderer(m,height=480,width=640) as renderer, imageio.get_writer(
                a.output/'reference_replay.mp4',fps=50,codec='libx264',quality=8) as movie:
            for episode,path in enumerate(files,1):
                with np.load(path) as trace:
                    frames=trace['frames']
                    count=0
                    for rowid in range(3,len(frames),4):
                        row=frames[rowid]
                        # Restore saved states on a render-only MjData. NO mj_step.
                        d.qpos[:]=row[1:1+m.nq]
                        d.qvel[:]=row[1+m.nq:1+m.nq+m.nv]
                        d.ctrl[:]=row[1+m.nq+m.nv:1+m.nq+m.nv+m.nu]
                        mujoco.mj_forward(m,d)
                        renderer.update_scene(d,camera=cam)
                        rgb=renderer.render()
                        im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
                        draw.rectangle((0,0,640,22),fill='black')
                        draw.text((8,5),f'RECORDED WARP STATES | episode {episode} | t={row[0]:.2f}s',fill='white')
                        movie.append_data(np.asarray(im));count+=1
                        if count in [1,30,35,50] or rowid+4>=len(frames):
                            im.save(a.output/f'episode_{episode:02d}_frame_{count:03d}.png')
                    counts.append(count)
    finally:
        env.close()
    (a.output/'provenance.json').write_text(json.dumps(dict(
        source='actual Warp qpos/qvel/ctrl records; no new integration',fps=50,
        substep_sampling=4,physics_dt=0.005,frames_per_episode=counts,
        resets='cuts between original episodes, NOT physical recovery'),indent=2),encoding='utf-8')


if __name__=='__main__':main()
