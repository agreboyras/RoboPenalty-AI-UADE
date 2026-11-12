"""Manual, free-root goalkeeper dive at the mouth of the goal."""
import argparse
from pathlib import Path
from types import SimpleNamespace
import time

import mujoco
import numpy as np

from experiments.free_keeper_stadium_h1 import bootstrap
from experiments.free_keeper_stadium_h1.presentation import FreeKeeperPresenter
from experiments.free_keeper_stadium_h1.run import actuator_caps, dump, root_addresses
from experiments.free_keeper4b.policy import JOINTS
from phase2.scene import RobotIndex
from presentation import PresentationConfig, ViewerClosed, png_write
from .dive import DURATION_S, GUARD_S, Dive


# Per-joint PD gains in Unitree actuator order, as used in H2.
KP = np.array([200, 150, 150, 200, 20, 20] * 2 + [200] * 3 + [100, 100, 50, 50, 40, 40, 40] * 2)
KD = np.array([5, 5, 5, 5, 2, 2] * 2 + [5] * 3 + [2] * 14)
DT = .002
KEEPER_X = 4.38


def build_demo(deploy, guard):
    project = bootstrap.PROJECT
    field = mujoco.MjSpec.from_file(str(deploy / 'g1_description/scene_with_ball.xml'))
    field.delete(field.body('pelvis'))
    source = mujoco.MjSpec.from_file(str(project.parent / 'unitree_mujoco/unitree_robots/g1/g1_29dof.xml'))
    for key in list(source.keys):
        source.delete(key)
    for number, geom in enumerate(source.geoms):
        if not geom.name:
            geom.name = f'geom_{number:03d}'
    frame = field.worldbody.add_frame(pos=[KEEPER_X, 0, 0], quat=[0, 0, 0, 1])
    field.attach(source, prefix='gk/', frame=frame)
    model = field.compile()
    model.opt.timestep = DT
    data = mujoco.MjData(model)
    keeper = RobotIndex.resolve(model, 'gk/')
    if tuple(model.joint(int(j)).name for j in keeper.joints) != tuple('gk/' + name for name in JOINTS):
        raise ValueError('Unexpected keeper joint order')
    root, _ = root_addresses(model, keeper)
    floor = model.geom('floor').id
    feet = {
        g for g in keeper.foot_geoms
        if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_SPHERE and model.geom_contype[g]
    }
    data.qpos[keeper.qpos] = guard
    mujoco.mj_forward(model, data)
    lowest_sole = min(data.geom_xpos[g, 2] - model.geom_size[g, 0] for g in feet)
    data.qpos[root + 2] += data.geom_xpos[floor, 2] + .001 - lowest_sole
    mujoco.mj_forward(model, data)
    return model, data, keeper, floor


class DivePresenter(FreeKeeperPresenter):
    def __init__(self, runtime, config, output):
        super().__init__(runtime, config, output, 'long', lod='none', camera='goal')
        if self.handle is not None:
            with self.handle.lock():
                self.trim_render_flags(self.handle.user_scn)

    def trim_render_flags(self, scene):
        scene.flags[self.mj.mjtRndFlag.mjRND_SHADOW] = 0
        scene.flags[self.mj.mjtRndFlag.mjRND_REFLECTION] = 0

    def select_camera(self, name):
        self.view = name
        self.camera = dict(lookat=[4.52, 0., .78], distance=3.85, azimuth=-5., elevation=-12.)
        self.camera_events.append(dict(view=name, time_sim_s=float(self.runtime.data.time)))
        self.apply_camera()

    def overlay(self):
        phase = self.status['phase']
        side = self.status['side']
        self.handle.set_texts((
            self.mj.mjtFontScale.mjFONTSCALE_100, self.mj.mjtGridPos.mjGRID_TOPLEFT,
            'Estirada manual\nFase\nLado',
            f'{self.runtime.data.time:.2f} s\n{phase}\n{side}',
        ))

    def capture_pose(self, label):
        before = self.runtime.integration_state(self.runtime.data)
        with self.mj.Renderer(self.runtime.model, height=480, width=640) as renderer:
            cam = self.mj.MjvCamera()
            self.mj.mjv_defaultCamera(cam)
            for key, value in self.camera.items():
                if key == 'lookat':
                    cam.lookat[:] = value
                else:
                    setattr(cam, key, value)
            renderer.update_scene(self.runtime.data, camera=cam)
            self.visual_scene.populate(renderer.scene, replace=False)
            self.trim_render_flags(renderer.scene)
            png_write(self.output / f'{label}.png', renderer.render())
        if not np.array_equal(before, self.runtime.integration_state(self.runtime.data)):
            raise RuntimeError('Capture modified the physical state')


def reach_time(samples, column, sign, distance):
    active = samples[samples[:, 0] >= GUARD_S]
    if len(active):
        reached = np.flatnonzero(sign * (active[:, column] - active[0, column]) >= distance)
        if len(reached):
            return float(active[reached[0], 0] - GUARD_S)
    return None


def run(deploy, output, side, viewer, captures):
    started = time.perf_counter()
    dive = Dive(side)
    model, data, keeper, floor = build_demo(deploy, dive.guard)
    caps = actuator_caps(model, keeper, model.actuator_ctrlrange[keeper.actuators, 1])
    ranges = model.jnt_range[keeper.joints]
    for _, _, first, last in dive.segments:
        if any(np.any((pose < ranges[:, 0]) | (pose > ranges[:, 1])) for pose in (first, last)):
            raise ValueError('Dive target outside a physical joint range')
    wrist = model.body(f'gk/{dive.leading}_wrist_yaw_link').id
    colliders = sorted(g for g in keeper.geoms if model.geom_contype[g] or model.geom_conaffinity[g])
    post = model.geom('goal_left_post').id
    half_span = float(abs(data.geom_xpos[post, 1]) - model.geom_size[post, 0])
    centers_local = model.geom_aabb[colliders, :3, None]
    extents_local = model.geom_aabb[colliders, 3:, None]
    signature = mujoco.mjtState.mjSTATE_INTEGRATION

    def integration_state(state):
        value = np.empty(mujoco.mj_stateSize(model, signature))
        mujoco.mj_getState(model, state, value, signature)
        return value

    runtime = SimpleNamespace(model=model, data=data, engine=SimpleNamespace(mujoco=mujoco, np=np),
                              integration_state=integration_state)
    presenter = None
    if viewer or captures:
        presenter = DivePresenter(runtime, PresentationConfig(enabled=viewer, fps=20.), output)
    samples = []
    contact = None
    max_span = max_penetration = max_joint_speed = max_joint_excess = 0.
    phase = None
    loop_start = time.perf_counter()
    try:
        for step in range(round(DURATION_S / DT)):
            t = step * DT
            state, reference = dive.reference(t)
            if state != phase:
                phase = state
                if presenter:
                    presenter.set_status(dict(phase=state, side='Izquierda' if side == 'LEFT' else 'Derecha'))
                    if step == 0:
                        presenter.begin_episode()
                    if captures:
                        presenter.capture_pose(f'{step:04d}_{state}')
            q, v = data.qpos[keeper.qpos], data.qvel[keeper.dofs]
            data.ctrl[keeper.actuators] = np.clip(KP * (reference - q) - KD * v, -caps, caps)
            mujoco.mj_step(model, data)
            # Positions and contacts are from the solve at t, before integration.
            pelvis, hand = data.xpos[keeper.pelvis], data.xpos[wrist]
            samples.append(np.r_[t, pelvis, hand])
            axes = data.geom_xmat[colliders].reshape(-1, 3, 3)
            centers_y = data.geom_xpos[colliders, 1] + (axes @ centers_local)[:, 1, 0]
            extents_y = (np.abs(axes) @ extents_local)[:, 1, 0]
            max_span = max(max_span, float(np.max(np.abs(centers_y) + extents_y)))
            max_joint_speed = max(max_joint_speed, float(np.abs(data.qvel[keeper.dofs]).max()))
            q = data.qpos[keeper.qpos]
            max_joint_excess = max(max_joint_excess, float(np.max(np.maximum(ranges[:, 0] - q, q - ranges[:, 1]))))
            for contact_id, c in enumerate(data.contact):
                g1, g2 = map(int, c.geom)
                if g1 not in keeper.geoms and g2 not in keeper.geoms:
                    continue
                max_penetration = max(max_penetration, -float(c.dist))
                if contact is None and floor in (g1, g2):
                    geom = g2 if g1 == floor else g1
                    if geom not in keeper.foot_geoms:
                        force = np.empty(6)
                        mujoco.mj_contactForce(model, data, contact_id, force)
                        if force[0] > .001:
                            contact = dict(time_s=t, body=model.body(int(model.geom_bodyid[geom])).name)
            if (not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all()
                    or max_joint_speed > 40 or max_penetration > .03 or max_joint_excess > .10):
                raise RuntimeError(f'Unstable physics at {t:.3f} s')
            if presenter:
                presenter.after_step()
        loop_wall = time.perf_counter() - loop_start
        if captures:
            presenter.capture_pose('final')
        if viewer:
            presenter.pause('finished', .50)
    finally:
        if presenter:
            presenter.close()

    positions = np.asarray(samples)
    body_time = reach_time(positions, 2, dive.sign, .20)
    hand_time = reach_time(positions, 5, dive.sign, .30)
    warnings = {i: warning.number for i, warning in enumerate(data.warning) if warning.number}
    checks = dict(
        within_posts=max_span < half_span,
        pelvis_20_cm_in_time=body_time is not None and body_time <= .65,
        wrist_30_cm_in_time=hand_time is not None and hand_time <= .65,
        side_landed=contact is not None and positions[-1, 3] < .30,
        joint_speed=max_joint_speed <= 20.,
        joint_ranges=max_joint_excess <= .03,
        penetration=max_penetration <= .02,
        no_warnings=not warnings,
    )
    report = dict(
        success=all(checks.values()), checks=checks, side=side, steps=len(samples),
        simulated_s=float(data.time), loop_wall_s=loop_wall, total_wall_s=time.perf_counter() - started,
        start_pelvis_w_m=positions[0, 1:4].tolist(), final_pelvis_w_m=positions[-1, 1:4].tolist(),
        max_lateral_collision_envelope_m=max_span, goal_clear_half_span_m=half_span,
        pelvis_20_cm_after_command_s=body_time, wrist_30_cm_after_command_s=hand_time,
        first_body_ground_contact=contact, max_joint_speed_rad_s=max_joint_speed,
        max_joint_excess_rad=max_joint_excess, max_penetration_m=max_penetration,
        warnings=warnings, viewer=viewer, viewer_frames=presenter.frames if presenter else 0,
    )
    np.save(output / 'positions.npy', positions, allow_pickle=False)
    dump(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deploy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--side', choices=('LEFT', 'RIGHT'), default='LEFT')
    parser.add_argument('--viewer', action='store_true')
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    try:
        report = run(args.deploy.resolve(), args.output, args.side, args.viewer, args.capture)
    except ViewerClosed:
        print('Visor cerrado. Ensayo interrumpido.')
        return 2
    for label, key in (('Pelvis 20 cm', 'pelvis_20_cm_after_command_s'),
                       ('Muñeca 30 cm', 'wrist_30_cm_after_command_s')):
        elapsed = report[key]
        print(f'{label}: {elapsed:.3f} s desde el impulso' if elapsed is not None else f'{label}: sin alcanzar')
    print(f'{report["simulated_s"]:.2f} s simulados / {report["total_wall_s"]:.2f} s reales')
    print(args.output / 'report.json')
    return 0 if report['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
