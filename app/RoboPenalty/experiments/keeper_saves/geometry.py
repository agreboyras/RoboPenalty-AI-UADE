"""Kinematic probes use scratch MjData only; intersection is not an executed save."""
from . import bootstrap
import numpy as np
import mujoco
import yaml
from lateral_scene import build_scene,Limits
from phase8b3.posture import PosturePD
from .posture_targets import extend
from .metrics import arm_geoms,envelope


def world():
    from portability.resources import runtime_record
    runtime_record()
    deploy=bootstrap.PROJECT.parent/'RoboNaldo_Deploy'
    scene=build_scene(deploy,bootstrap.PROJECT.parent/'unitree_mujoco',Limits())
    software=np.asarray(yaml.safe_load((deploy/'deploy_mujoco/config/mujoco_freekick.yaml').read_text())['tau_limit'])
    return (*scene,software)


def initial_posture(m,k):
    q=np.zeros(29)
    for n,j in enumerate(k.joints):
        name=m.joint(int(j)).name
        if 'shoulder_roll' in name:q[n]=.25 if 'left_' in name else -.25
        elif 'elbow' in name:q[n]=.30
    return q


def reach_probe(m,d,k):
    """Collision sphere intersection on a sampled Y grid at X=4; no mj_step."""
    g=arm_geoms(m,k);ball=m.body('ball').id;bq=int(m.jnt_qposadr[int(m.body_jntadr[ball])]);bg=m.geom('ball_geom').id
    scratch=mujoco.MjData(m);scratch.qpos[:]=d.qpos;scratch.qvel[:]=0
    result={'envelope':envelope(m,d,g),'heights':{},'arm_collision_geoms':[m.geom(i).name for i in g]}
    for z in (.115,.4,.6,.8,1.):
        hit=[];nearest=10.
        for y in np.linspace(-1.2,1.2,81):
            scratch.qpos[bq:bq+3]=[4.,y,z];mujoco.mj_forward(m,scratch)
            distance=min(float(mujoco.mj_geomDistance(m,scratch,bg,int(i),2.,None)) for i in g)
            nearest=min(nearest,distance)
            if distance<=0:hit.append(float(y))
        result['heights'][str(z)]=dict(sampled_center_y_interval=[min(hit),max(hit)] if hit else None,
             sampled_hit_count=len(hit),min_surface_distance_m=nearest)
    result['note']='Y grid 0.03m, sphere radius from unchanged model; convex collision geometry. No force/contact guarantee.'
    return result


def geometric_map():
    m,d,s,k,rail,software=world();base=initial_posture(m,k);pd=PosturePD(m,k,rail)
    names=pd.names;guard=pd.target(base);results=[]
    from types import SimpleNamespace
    for side in ('WAIT','LEFT','RIGHT'):
        pd.decision=None if side=='WAIT' else SimpleNamespace(state='TRACKING',prediction={'valid':True,'y_w':1. if side=='LEFT' else -1.})
        pd.observation=SimpleNamespace(rail_origin_y=0.,keeper_q=0.)
        stable=pd.target(base)
        for amount in ((0.,) if side=='WAIT' else (0.,.5,1.)):
            q=extend(stable,names,side,amount);ranges=m.jnt_range[k.joints]
            assert np.all(q>=ranges[:,0]+.02) and np.all(q<=ranges[:,1]-.02)
            d.qpos[k.qpos]=q;mujoco.mj_forward(m,d)
            contacts=[dict(a=m.geom(int(c.geom1)).name,b=m.geom(int(c.geom2)).name,distance_m=float(c.dist))
                      for c in d.contact[:d.ncon] if int(c.geom1) in k.geoms and int(c.geom2) in k.geoms]
            results.append(dict(side=side,extension=amount,target_rad=q.tolist(),self_contacts=contacts,reach=reach_probe(m,d,k)))
    return dict(physical_steps=0,names=names,reference_only=True,rows=results)
