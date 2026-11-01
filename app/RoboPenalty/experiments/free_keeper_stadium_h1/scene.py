"""Attach the untouched Unitree G1 with its free joint; no slider or support."""
from . import bootstrap
import mujoco
import numpy as np
from phase2.scene import RobotIndex


def build(deploy,unitree,home,keeper_y):
    spec=mujoco.MjSpec.from_file(str(deploy/'g1_description/scene_with_ball.xml'))
    original=spec.compile()
    source=mujoco.MjSpec.from_file(str(unitree/'unitree_robots/g1/g1_29dof.xml'))
    source_model=source.compile()
    if keeper_y is not None:
        if sum(j.type==mujoco.mjtJoint.mjJNT_FREE for j in source.joints)!=1:
            raise ValueError('Expected one original free root')
        for key in list(source.keys):source.delete(key)  # keyframes only, never physics
        for i,g in enumerate(source.geoms):
            if not g.name:g.name=f'geom_{i:03d}'
        frame=spec.worldbody.add_frame(name='free_keeper_origin',pos=[4.2,keeper_y,0],quat=[0,0,0,1])
        spec.attach(source,prefix='gk/',frame=frame)
    model=spec.compile();model.opt.timestep=.002
    data=mujoco.MjData(model);shooter=RobotIndex.resolve(model,'')
    keeper=RobotIndex.resolve(model,'gk/') if keeper_y is not None else None
    checks=dict(no_added_constraints=model.neq==original.neq,
        no_slider=all('keeper_slide' not in model.joint(i).name for i in range(model.njnt)),
        actuator_count=model.nu==original.nu+(29 if keeper else 0))
    # Attaching at the end must not change the original physical prefix.
    checks['original_bodies_preserved']=all(np.array_equal(getattr(model,key)[:original.nbody],getattr(original,key))
        for key in ('body_mass','body_inertia','body_ipos','body_iquat','body_pos','body_quat','body_parentid'))
    checks['original_contacts_preserved']=all(np.array_equal(getattr(model,key)[:original.ngeom],getattr(original,key))
        for key in ('geom_bodyid','geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_solref','geom_solimp','geom_contype','geom_conaffinity'))
    checks['original_motors_preserved']=all(np.array_equal(getattr(model,key)[:original.nu],getattr(original,key))
        for key in ('actuator_trnid','actuator_gear','actuator_gainprm','actuator_biasprm','actuator_ctrlrange','actuator_forcerange'))
    if keeper:
        root_joint=int(model.body_jntadr[keeper.pelvis])
        checks['root_free']=model.jnt_type[root_joint]==mujoco.mjtJoint.mjJNT_FREE
        for field in ('actuators','qpos','dofs'):
            checks['independent_'+field]=not(set(getattr(shooter,field))&set(getattr(keeper,field)))
        native=RobotIndex.resolve(source_model,'')
        checks['motor_order']=[model.joint(int(j)).name.removeprefix('gk/') for j in keeper.joints]==[
            source_model.joint(int(j)).name for j in native.joints]
        checks['hinge_parameters']=all(np.array_equal(getattr(model,key)[keeper.joints],getattr(source_model,key)[native.joints])
            for key in ('jnt_range','jnt_axis','jnt_pos','jnt_actfrcrange'))
        checks['dof_parameters']=all(np.array_equal(getattr(model,key)[keeper.dofs],getattr(source_model,key)[native.dofs])
            for key in ('dof_damping','dof_armature','dof_frictionloss'))
        checks['actuator_parameters']=all(np.array_equal(getattr(model,key)[keeper.actuators],getattr(source_model,key)[native.actuators])
            for key in ('actuator_gear','actuator_gainprm','actuator_biasprm','actuator_ctrlrange','actuator_forcerange'))
        checks['mass_inertia']=all(np.array_equal(getattr(model,key)[b],getattr(source_model,key)[source_model.body(model.body(b).name.removeprefix('gk/')).id])
            for b in keeper.bodies for key in ('body_mass','body_inertia','body_ipos','body_iquat'))
        sg=sorted(keeper.geoms);ng=sorted(native.geoms)
        checks['contact_geometry']=all(np.array_equal(getattr(model,key)[sg],getattr(source_model,key)[ng])
            for key in ('geom_type','geom_size','geom_friction','geom_solref','geom_solimp','geom_contype','geom_conaffinity'))
        data.qpos[keeper.qpos]=home
        mujoco.mj_forward(model,data)
        feet=[g for g in keeper.foot_geoms if model.geom_type[g]==mujoco.mjtGeom.mjGEOM_SPHERE and model.geom_contype[g]]
        if len(feet)!=8:raise ValueError('Original 4B foot contract changed')
        floor=model.geom('floor').id;z=float(data.geom_xpos[floor,2])
        qa=int(model.jnt_qposadr[root_joint])
        data.qpos[qa+2]+=z+.001-min(data.geom_xpos[g,2]-model.geom_size[g,0] for g in feet)
    if not all(checks.values()):raise ValueError('Composition rejected: '+str(checks))
    mujoco.mj_forward(model,data)
    return model,data,shooter,keeper,checks
