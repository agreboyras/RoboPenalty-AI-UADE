"""Real MuJoCo renders of recorded physical states, never a fabricated animation."""
from . import bootstrap
from .geometry import world
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import mujoco
from phase7d.visual_scene import StadiumScene,prepare_model
from phase7d.integrity import model_signature
from presentation import png_write


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve()
    if out.exists() or not out.is_relative_to(bootstrap.PROJECT):p.error('New output directory inside this RoboPenalty copy required')
    out.mkdir(parents=True);payload=a.trial.read_bytes();trial=json.loads(payload)
    m,d,*_=world();signature=model_signature(m);prepare_model(m);scene=StadiumScene(m)
    camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(camera)
    camera.lookat[:]=[4.2,0,.85];camera.distance=2.35;camera.azimuth=10.;camera.elevation=-8.
    with mujoco.Renderer(m,height=640,width=960) as renderer:
        for name,key in (('wait','1.98'),('available_700ms','2.70'),('extension','4.98'),('recovery','9.98')):
            snapshot=trial['snapshots'][key];d.qpos[:]=snapshot['qpos'];d.qvel[:]=snapshot['qvel'];d.ctrl[:]=snapshot['ctrl']
            mujoco.mj_forward(m,d);q=d.qpos.copy();v=d.qvel.copy()
            renderer.update_scene(d,camera=camera);scene.populate(renderer.scene,replace=False)
            png_write(out/(name+'.png'),renderer.render())
            assert np.array_equal(q,d.qpos) and np.array_equal(v,d.qvel)
    assert signature==model_signature(m)
    (out/'render.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(payload).hexdigest(),
        replay_of_measured_states=True,new_physical_steps=0,model_signature_unchanged=True),indent=2)+'\n')


if __name__=='__main__':main()
