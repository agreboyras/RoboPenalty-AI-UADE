"""Same G1 and floor as H1, in a world containing only that robot and floor."""
from experiments.free_keeper_stadium_h1 import bootstrap
import mujoco
import numpy as np
from phase2.scene import RobotIndex
from experiments.free_keeper_stadium_h1.scene import build as full_build
from experiments.free_keeper_stadium_h1.run import actuator_caps

def build(deploy,unitree,home,software_limits):
    reference,_,_,rk,oldchecks=full_build(deploy,unitree,home,0.)
    world=mujoco.MjSpec()
    option_fields=[n for n in dir(reference.opt) if not n.startswith('_')]
    for n in option_fields:setattr(world.option,n,getattr(reference.opt,n))
    f=reference.geom('floor').id
    world.worldbody.add_geom(name='floor',type=mujoco.mjtGeom(int(reference.geom_type[f])),
        pos=reference.geom_pos[f],quat=reference.geom_quat[f],size=reference.geom_size[f],
        friction=reference.geom_friction[f],solref=reference.geom_solref[f],solimp=reference.geom_solimp[f],
        solmix=float(reference.geom_solmix[f]),margin=float(reference.geom_margin[f]),gap=float(reference.geom_gap[f]),
        priority=int(reference.geom_priority[f]),condim=int(reference.geom_condim[f]),
        contype=int(reference.geom_contype[f]),conaffinity=int(reference.geom_conaffinity[f]),rgba=[.22,.29,.25,1])
    world.worldbody.add_light(name='diagnostic_light',pos=[3,-3,5],dir=[0,0,-1])
    source=mujoco.MjSpec.from_file(str(unitree/'unitree_robots/g1/g1_29dof.xml'))
    for key in list(source.keys):source.delete(key)
    for i,g in enumerate(source.geoms):
        if not g.name:g.name=f'geom_{i:03d}'
    frame=world.worldbody.add_frame(name='keeper_origin',pos=[4.2,0,0],quat=[0,0,0,1])
    world.attach(source,prefix='gk/',frame=frame)
    m=world.compile();d=mujoco.MjData(m);k=RobotIndex.resolve(m,'gk/')
    checks=dict(oldchecks)
    checks.update(one_free_root=int(np.sum(m.jnt_type==mujoco.mjtJoint.mjJNT_FREE))==1,
        only_g1_and_floor=m.nq==36 and m.nv==35 and m.nu==29 and m.neq==0 and m.nbody==len(k.bodies)+1 and m.ngeom==len(k.geoms)+1,
        exact_options=all(np.array_equal(getattr(m.opt,n),getattr(reference.opt,n)) for n in option_fields))
    for key in ('friction','solref','solimp','solmix','margin','gap','priority','condim','contype','conaffinity','type','size','pos','quat'):
        checks['floor_'+key]=np.array_equal(getattr(m,'geom_'+key)[m.geom('floor').id],getattr(reference,'geom_'+key)[f])
    for key in ('body_mass','body_inertia','body_ipos','body_iquat'):
        checks[key]=all(np.array_equal(getattr(m,key)[b],getattr(reference,key)[reference.body(m.body(b).name).id]) for b in k.bodies)
    for key in ('geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_solref','geom_solimp','geom_contype','geom_conaffinity'):
        checks[key]=all(np.array_equal(getattr(m,key)[g],getattr(reference,key)[reference.geom(m.geom(g).name).id]) for g in k.geoms)
    for key in ('jnt_range','jnt_axis','jnt_pos','jnt_actfrcrange'):
        checks[key]=np.array_equal(getattr(m,key)[k.joints],getattr(reference,key)[rk.joints])
    for key in ('dof_damping','dof_armature','dof_frictionloss'):
        checks[key]=np.array_equal(getattr(m,key)[k.dofs],getattr(reference,key)[rk.dofs])
    for key in ('actuator_gear','actuator_gainprm','actuator_biasprm','actuator_ctrlrange','actuator_forcerange'):
        checks[key]=np.array_equal(getattr(m,key)[k.actuators],getattr(reference,key)[rk.actuators])
    caps=actuator_caps(m,k,software_limits)
    checks['effective_caps']=np.array_equal(caps,actuator_caps(reference,rk,software_limits))
    if not all(checks.values()):raise ValueError('Composition mismatch: '+str([n for n,v in checks.items() if not v]))
    j=int(m.body_jntadr[k.pelvis]);qa=int(m.jnt_qposadr[j]);va=int(m.jnt_dofadr[j])
    d.qpos[k.qpos]=home;mujoco.mj_forward(m,d)
    feet=[g for g in k.foot_geoms if m.geom_type[g]==mujoco.mjtGeom.mjGEOM_SPHERE and m.geom_contype[g]]
    if len(feet)!=8:raise ValueError('Unverified soles')
    d.qpos[qa+2]+=.001-min(d.geom_xpos[g,2]-m.geom_size[g,0] for g in feet)
    mujoco.mj_forward(m,d)
    return m,d,k,qa,va,caps,checks
