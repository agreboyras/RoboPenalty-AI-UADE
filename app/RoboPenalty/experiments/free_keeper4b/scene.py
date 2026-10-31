"""In-memory scene; original XML, inertias, joints and contacts stay untouched."""
from pathlib import Path
import mujoco
import numpy as np
from .policy import JOINTS


def build(xml, home, source_limits):
    spec = mujoco.MjSpec.from_file(str(Path(xml).resolve()))
    spec.option.timestep = 0.002
    spec.worldbody.add_geom(name='balance_floor', type=mujoco.mjtGeom.mjGEOM_PLANE,
                            size=[5, 5, 0.1], rgba=[0.24, 0.29, 0.32, 1],
                            friction=[1, 0.005, 0.0001])
    spec.worldbody.add_light(name='balance_light', pos=[0, -2, 4], dir=[0, 0, -1])
    model = spec.compile()
    free = np.flatnonzero(model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)
    if model.nu != 29 or model.nq != 36 or model.nv != 35 or len(free) != 1 or model.neq:
        raise ValueError('Expected exactly one unconstrained free-base G1 with 29 motors')
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, int(j))
             for j in model.actuator_trnid[:, 0]]
    if tuple(names) != JOINTS or not np.allclose(model.actuator_gear[:, 0], 1):
        raise ValueError('Unverified actuator order or transmission')
    jid = model.actuator_trnid[:, 0].copy()
    qadr, vadr = model.jnt_qposadr[jid], model.jnt_dofadr[jid]
    limits = np.asarray(source_limits, dtype=float).copy()
    for a, j in enumerate(jid):
        for enabled, bounds in ((model.actuator_ctrllimited[a], model.actuator_ctrlrange[a]),
                                (model.actuator_forcelimited[a], model.actuator_forcerange[a]),
                                (model.jnt_actfrclimited[j], model.jnt_actfrcrange[j])):
            if enabled:
                limits[a] = min(limits[a], abs(bounds[0]), abs(bounds[1]))
    data = mujoco.MjData(model)
    data.qpos[qadr] = home
    mujoco.mj_forward(model, data)
    foot_bodies = {model.body(name).id for name in ('left_ankle_roll_link', 'right_ankle_roll_link')}
    # Only initialization: place the actual spherical foot collision soles 1 mm
    # above the floor. Never write root qpos again during physics.
    soles = [data.geom_xpos[g, 2] - model.geom_size[g, 0] for g in range(model.ngeom)
             if model.geom_bodyid[g] in foot_bodies and model.geom_contype[g]
             and model.geom_type[g] == mujoco.mjtGeom.mjGEOM_SPHERE]
    if len(soles) != 8:
        raise ValueError('Unverified Unitree foot contact geometry')
    root_q = int(model.jnt_qposadr[free[0]])
    data.qpos[root_q+2] += 0.001 - min(soles)
    mujoco.mj_forward(model, data)
    return model, data, qadr, vadr, jid, limits, foot_bodies
