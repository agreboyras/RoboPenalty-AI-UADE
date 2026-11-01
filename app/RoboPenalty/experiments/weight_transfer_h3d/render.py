"""Real MuJoCo stills of recorded H3D states. No policy, integration or animation."""
from experiments.free_keeper_stadium_h1 import bootstrap
from experiments.free_keeper_stadium_h1.run import validate_resources
from experiments.free_keeper4b.render_trace import png
from experiments.central_block_h3a.run import dump
from .scene import build
import argparse,json
from pathlib import Path
import numpy as np
import mujoco

def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    bundle=bootstrap.PROJECT.parents[1];a.output=a.output.resolve()
    if a.output.exists() or not a.output.is_relative_to(bundle/'validation'):p.error('Use a new output inside validation/')
    deploy=bundle/'validation/keeper_live_20261030/package/app/RoboNaldo_Deploy';unitree=bundle/'app/unitree_mujoco';validate_resources(deploy,unitree)
    cfg=json.loads((a.trial/'configuration.json').read_text());z=np.load(a.trial/'trace.npz')
    m,d,*_=build(deploy,unitree,np.array(cfg['policy']['home']),cfg['policy']['limits'])
    a.output.mkdir(parents=True);m.vis.global_.offwidth=960;m.vis.global_.offheight=720
    # Contrast only in this offline renderer, never in a running trial.
    m.vis.headlight.ambient[:]=[.45,.45,.45];m.vis.headlight.diffuse[:]=[.8,.8,.8]
    m.geom_rgba[m.geom('floor').id]=[.50,.55,.50,1.]
    cam=mujoco.MjvCamera();mujoco.mjv_defaultCamera(cam);cam.lookat[:]=[4.2,-.05,.6];cam.distance=2.5;cam.azimuth=180;cam.elevation=-15
    meta=[]
    with mujoco.Renderer(m,height=720,width=960) as renderer:
        for when in (2.,2.48,2.8,2.874,2.966,5.998):
            i=int(np.argmin(abs(z['time']-when)));d.qpos[:]=z['qpos'][i];d.qvel[:]=z['qvel'][i];d.ctrl[:]=z['sent'][i]
            mujoco.mj_forward(m,d);renderer.update_scene(d,camera=cam);name=f't_{z["time"][i]:.3f}.png';png(a.output/name,renderer.render())
            meta.append(dict(image=name,recorded_time_s=float(z['time'][i]),original_measured_loads_n=z['load'][i],point_w=z['point'][i],pelvis_w=z['pelvis'][i]))
    dump(a.output/'frames.json',meta);print(a.output)

if __name__=='__main__':main()
