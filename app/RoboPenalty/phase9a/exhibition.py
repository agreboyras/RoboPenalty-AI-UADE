"""One rehearsed, physically scored penalty with the free goalkeeper in 7D."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import mujoco
import numpy as np
import yaml

from experiments.free_keeper4b.policy import JOINTS
from experiments.free_keeper_stadium_h1.policy_client import PolicyClient
from experiments.free_keeper_stadium_h1.run import actuator_caps, crossing, dump, root_addresses
from experiments.free_keeper_stadium_h1.scene import build
from experiments.lateral_keeper_h2.dive import Dive, GUARD_S
from experiments.lateral_keeper_h2.maneuver import interpolate
from phase2.freekick_adapter import FreeKickAdapter
from phase4a.evaluation import classify
from phase4a.scenarios import initialize
from phase8b2.experiment import identifier
from phase9a.commands import EXHIBITION_LABELS, LEFT_NEAR, LEFT_OPEN
from phase7d.presentation import MonumentalPresenter
from phase9a.control import Control

SHOTS = {LEFT_NEAR: (3.66, 1.), LEFT_OPEN: (3.50, 1.24)}
WIDE_REFERENCE = Path(__file__).with_name('exhibition_left_open.json')
PREPARE_DURATION_S = .48
DURATION_S = 7.
DT = .002
PROJECT = Path(__file__).resolve().parents[1]


def exhibition_catalog(catalog):
    """Add the measured exhibition shot to an isolated copy of the 8C catalog."""
    extended = copy.copy(catalog)
    reference_bytes = WIDE_REFERENCE.read_bytes()
    reference = json.loads(reference_bytes)
    evaluation = reference['evaluation']
    if not (evaluation['goal_detected'] and evaluation['first_foot_ball']
            and .75 <= evaluation['goal_crossing_measured']['position_w'][1] <= 1.35
            and reference['sample_dt_s'] == 10 * DT
            and len(reference['ball_trace']) == round(DURATION_S / (10 * DT))):
        raise ValueError('Invalid open-left reference')
    digest = hashlib.sha256(reference_bytes).hexdigest()
    extended.id = hashlib.sha256((catalog.id + digest).encode('ascii')).hexdigest()
    extended.actions = tuple(SHOTS)
    bias = reference['configuration']['target_bias']
    extended.mapping = {LEFT_NEAR: catalog.mapping[LEFT_NEAR], LEFT_OPEN: (identifier(bias), bias)}
    extended.calibration = {
        LEFT_NEAR: catalog.calibration[LEFT_NEAR],
        LEFT_OPEN: dict(kind='historical_calibration', distance='long',
                        plane_y_w_m=evaluation['approach_crossing_measured']['position_w'][1],
                        source=str(WIDE_REFERENCE), sha256=digest),
    }
    return extended


class ExhibitionControl(Control):
    shot_labels = EXHIBITION_LABELS
    shot_prompt = 'Tiros: Patea a la izquierda / Patea a la izquierda abierta'
    help_text = (
        'Exhibición de un penal. Iniciar partido; Patea a la izquierda o Patea a la izquierda abierta; '
        '/voz (o Enter) con --voice; pausar partida; reanudar partida; salir.'
    )

    def process(self, message):
        self.assert_owner()
        intent = message.intent
        if intent == 'five':
            return False, 'La exhibición es de un solo penal. Escribí «Iniciar partido».'
        if self.awaiting_shot and intent and intent.startswith('shot:') and intent[5:] not in SHOTS:
            return False, self.shot_prompt
        accepted, reason = super().process(message)
        if accepted and intent and intent.startswith('shot:'):
            reason = f'{self.shot_labels[intent[5:]].capitalize()}. Estirada de exhibición al detectar el golpe.'
        elif accepted and intent and intent.startswith('mode:'):
            reason = f'Modo {self.mode.upper()}. Exhibición de arquero libre.'
        return accepted, reason


def fixed_selector(base, action=LEFT_NEAR):
    class ExhibitionSelector(base):
        def choose(self, observation, calibration, episode_id, strategy='fixed', seed=2026,
                   fixed_action='left'):
            return super().choose(observation, calibration, episode_id, 'fixed', seed, action)

    return ExhibitionSelector


class ExhibitionPresenter(MonumentalPresenter):
    def select_camera(self, name):
        if name not in ('exhibition_start', 'exhibition_goal'):
            return super().select_camera(name)
        self.view = name
        if name == 'exhibition_start':
            self.camera = dict(lookat=[1.9, 0., .75], distance=7.5, azimuth=35., elevation=-17.)
        else:
            self.camera = dict(lookat=[4.52, 0., .78], distance=3.85, azimuth=-5., elevation=-12.)
        self.camera_events.append(dict(view=name, time_sim_s=float(self.runtime.data.time)))
        self.apply_camera()

    def overlay(self):
        status = self.status
        phase = status.get('phase', 'READY')
        if self.service and self.service.control.paused:
            phase += ' [PAUSA]'
        shot = EXHIBITION_LABELS.get(status.get('action'), 'Elegí el tiro').capitalize()
        result = {'save': 'ATAJADA', 'goal': 'GOL', 'miss': 'ERRADO'}.get(status.get('last_result'), '—')
        self.handle.set_texts((
            self.mj.mjtFontScale.mjFONTSCALE_100,
            self.mj.mjtGridPos.mjGRID_TOPLEFT,
            'Exhibición\nPartido\nArquero libre\nResultado\nGoles / Atajadas / Errados\nTiempo',
            f'{shot}\n{phase}\n{self.runtime.keeper_phase}\n{result}\n'
            f'{status.get("goals", 0)} / {status.get("saves", 0)} / {status.get("misses", 0)}\n'
            f'{self.runtime.data.time:.2f} s',
        ))


class ExhibitionRuntime:
    def __init__(self, catalog, observation_type, policy_python, loco_deploy, output):
        started = time.perf_counter()
        self.catalog = catalog
        self.observation_type = observation_type
        self.engine = SimpleNamespace(mujoco=mujoco, np=np)
        self.console = sys.stdout
        self.keeper_phase = 'Guardia'
        self.last_action = None
        self.policy_python = policy_python.resolve()
        self.loco_deploy = loco_deploy.resolve()
        self.client = self._start_policy(output)
        self.runs = 0
        self.presenter = None
        try:
            self.plan = Dive('LEFT')
            self.guard = self.plan.guard.copy()
            for side in ('left', 'right'):
                self.guard[JOINTS.index(f'{side}_hip_pitch_joint')] += .02
                self.guard[JOINTS.index(f'{side}_ankle_pitch_joint')] -= .02
            meta = self.client.metadata
            self.home = np.asarray(meta['home'])
            self.kp, self.kd = np.asarray(meta['kp']), np.asarray(meta['kd'])
            deploy = PROJECT.parent / 'RoboNaldo_Deploy'
            self.model, self.data, self.shooter, self.keeper, self.composition = build(
                deploy, PROJECT.parent / 'unitree_mujoco', self.home, 0.)
            joint_names = tuple(self.model.joint(int(j)).name.removeprefix('gk/') for j in self.keeper.joints)
            if joint_names != JOINTS:
                raise ValueError('Keeper joint order differs from the balance policy')
            self.root_q, self.root_v = root_addresses(self.model, self.keeper)
            self.data.qpos[self.root_q] = 4.38
            self.initial_qpos = self.data.qpos.copy()
            mujoco.mj_forward(self.model, self.data)
            self.kick = FreeKickAdapter(deploy, self.model, self.shooter)
            self.session = self.kick.fsm.freekick_policy.ort_session
            self.template = self._clone_kick(self.kick)
            self.shooter_caps = np.asarray(yaml.safe_load(
                (deploy / 'deploy_mujoco/config/mujoco_freekick.yaml').read_text())['tau_limit'])
            self.keeper_caps = actuator_caps(self.model, self.keeper, meta['limits'])
            self.ranges = self.model.jnt_range[self.keeper.joints]
            self.ball = self.model.body('ball').id
            self.ball_geom = self.model.geom('ball_geom').id
            joint = int(self.model.body_jntadr[self.ball])
            self.ball_q, self.ball_v = int(self.model.jnt_qposadr[joint]), int(self.model.jnt_dofadr[joint])
            self.signature = mujoco.mjtState.mjSTATE_INTEGRATION
            self.probes = {
                action: json.loads(Path(entry['source']).read_bytes())
                for action, entry in catalog.calibration.items()
            }
            self.setup_wall_s = time.perf_counter() - started
        except BaseException:
            self.client.close(force=True)
            raise

    def _start_policy(self, output):
        client = PolicyClient(self.policy_python, self.loco_deploy, output, PROJECT)
        meta = client.metadata
        if (tuple(meta['joints']) != JOINTS or meta['recurrent_reset_max'] != 0
                or meta['physical_velocity_command'] != [0, 0, 0]):
            client.close(force=True)
            raise ValueError('Invalid balance-policy contract')
        return client

    def _clone_kick(self, adapter):
        return copy.deepcopy(adapter, {id(self.session): self.session})

    def close(self):
        self.client.close()
        if getattr(self.client, 'final', {}).get('normalizer_unchanged') is False:
            raise RuntimeError('Balance normalizer changed during the exhibition')

    def attach(self, presenter):
        self.presenter = presenter

    def integration_state(self, data):
        value = np.empty(mujoco.mj_stateSize(self.model, self.signature))
        mujoco.mj_getState(self.model, data, value, self.signature)
        return value

    def _reset(self, output):
        if self.runs:
            self.close()
            self.client = self._start_policy(output)
        self.runs += 1
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.initial_qpos
        self.kick = self._clone_kick(self.template)
        self.keeper_phase = 'Guardia'
        if self.presenter and self.presenter.view == 'exhibition_goal':
            self.presenter.select_camera('exhibition_start')
        self.last_action = None
        initialize(dict(translate_x=-2.), self.model, self.data, self.kick, None, False)
        mujoco.mj_forward(self.model, self.data)

    def _observe_initial(self, distance, opponent):
        data = self.data
        y = float(data.xpos[self.keeper.pelvis, 1])
        return self.observation_type(
            distance, opponent, y, y, 0., .22, float(self.model.geom_size[self.ball_geom, 0]),
            tuple(data.xpos[self.ball]), tuple(data.xpos[self.shooter.pelvis]),
            available_actions=self.catalog.actions,
        )

    def execute(self, distance, opponent, output, on_prepared, on_shooting, *, enable_dive=True):
        start = time.perf_counter()
        self._reset(Path(output).parent)
        initial = self.integration_state(self.data)
        action = on_prepared(self._observe_initial(distance, opponent))
        if action not in SHOTS:
            raise ValueError('Exhibition requires a rehearsed shot')
        self.last_action = action
        prepare_s, dive_speed = SHOTS[action]
        scenario, bias = self.catalog.mapping[action]
        configuration = dict(translate_x=-2., target_bias=bias)
        self.kick.state.target_y_bias = bias
        probe = self.probes[action]
        if 'ball_trace' in probe:
            ball_trace = np.asarray(probe['ball_trace'])
        else:
            ball_trace = np.asarray([
                row['observation']['ball_position_w'] + row['observation']['ball_velocity_w']
                for row in probe['trace']
            ])
        if self.presenter:
            self.presenter.status['action'] = action
            self.presenter.capture()
            self.presenter.pause('before_shot', self.presenter.config.before_shot_s)
        on_shooting()
        if self.presenter:
            self.presenter.begin_episode()

        data = self.data
        target = self.home.copy()
        dive_start = dive_origin = dive_reference = None
        first_foot = first_keeper = goal_cross = None
        foot_peak = keeper_peak = 0.
        maximum_speed = maximum_penetration = maximum_excess = maximum_reach = 0.
        ready_height = None
        prefix_error = 0.
        previous_ball = data.qpos[self.ball_q:self.ball_q + 3].copy()
        force = np.zeros(6)
        for step in range(round(DURATION_S / DT)):
            t = step * DT
            ball_velocity = data.qvel[self.ball_v:self.ball_v + 3]
            # The incoming shot ends at the first keeper contact or goal-plane crossing.
            # Later bounces may differ and cannot change the measured incoming path.
            if step % 10 == 0 and first_keeper is None and goal_cross is None:
                baseline = ball_trace[step // 10]
                prefix_error = max(prefix_error, float(np.max(np.abs(previous_ball - baseline[:3]))),
                                   float(np.max(np.abs(ball_velocity - baseline[3:]))))
            if np.any(data.xfrc_applied) or np.any(data.qfrc_applied):
                raise RuntimeError('External force during exhibition')
            if t < prepare_s:
                if step % 10 == 0:
                    q, v = self.root_q, self.root_v
                    answer = self.client.request(
                        'observe', q=data.qpos[self.keeper.qpos].tolist(),
                        dq=data.qvel[self.keeper.dofs].tolist(),
                        quaternion=data.qpos[q + 3:q + 7].tolist(),
                        omega=data.qvel[v + 3:v + 6].tolist(),
                    )
                    target = np.clip(answer['target'], self.ranges[:, 0], self.ranges[:, 1])
                reference = target
            elif dive_start is None:
                self.keeper_phase = 'Preparación'
                reference = interpolate(target, self.guard, (t - prepare_s) / PREPARE_DURATION_S)
                if enable_dive and first_foot and ball_velocity[0] > .5:
                    dive_start = t
                    dive_origin = data.qpos[self.root_q:self.root_q + 3].copy()
                    dive_reference = reference.copy()
                    self.keeper_phase = 'Impulso'
                    if self.presenter and self.presenter.view == 'exhibition_start':
                        self.presenter.select_camera('exhibition_goal')
            else:
                elapsed = t - dive_start
                self.keeper_phase, reference = self.plan.reference(GUARD_S + elapsed * dive_speed)
                reference = interpolate(dive_reference, reference, elapsed / .18)
            q = data.qpos[self.keeper.qpos]
            v = data.qvel[self.keeper.dofs]
            data.ctrl[self.keeper.actuators] = np.clip(self.kp * (reference - q) - self.kd * v,
                                                       -self.keeper_caps, self.keeper_caps)
            self.kick.command_before_step(t)
            data.ctrl[self.shooter.actuators] = self.kick.torque(data, self.shooter_caps)
            self.engine.mujoco.mj_step(self.model, data)
            position = data.qpos[self.ball_q:self.ball_q + 3].copy()
            cross = crossing(previous_ball, position)
            if cross is not None and goal_cross is None:
                fraction = (5. - previous_ball[0]) / (position[0] - previous_ball[0])
                goal_cross = dict(time_sim_s=t + fraction * DT, position_w=cross.tolist(),
                                  inside=bool(abs(cross[1]) <= 1.5 and 0 <= cross[2] <= 1.8))
            previous_ball = position
            for contact_id, contact in enumerate(data.contact):
                a, b = map(int, contact.geom)
                if a in self.keeper.geoms or b in self.keeper.geoms:
                    maximum_penetration = max(maximum_penetration, -float(contact.dist))
                if self.ball_geom not in (a, b):
                    continue
                other = b if a == self.ball_geom else a
                foot = other in self.shooter.foot_geoms
                keeper = other in self.keeper.geoms
                if not (foot or keeper):
                    continue
                mujoco.mj_contactForce(self.model, data, contact_id, force)
                normal = float(force[0])
                if foot:
                    foot_peak = max(foot_peak, normal)
                    seen = first_foot
                else:
                    keeper_peak = max(keeper_peak, normal)
                    seen = first_keeper
                if seen is not None or normal <= .001:
                    continue
                event = dict(time_sim_s=float(data.time), solver_time_s=t,
                             geom=self.model.geom(other).name, normal_force_n=normal,
                             position_w=contact.pos.tolist(),
                             body=self.model.body(int(self.model.geom_bodyid[other])).name)
                if foot:
                    first_foot = event
                    ready_height = float(data.qpos[self.root_q + 2])
                else:
                    first_keeper = event
            if step % 10 == 0:
                self.kick.update(data, data.xpos[self.ball].copy(),
                                 data.qvel[self.ball_v:self.ball_v + 3].copy(), t)
            if dive_origin is not None:
                maximum_reach = max(maximum_reach, float(data.qpos[self.root_q + 1] - dive_origin[1]))
            q = data.qpos[self.keeper.qpos]
            maximum_speed = max(maximum_speed, float(np.abs(data.qvel[self.keeper.dofs]).max()))
            maximum_excess = max(maximum_excess, float(np.max(np.maximum(
                self.ranges[:, 0] - q, q - self.ranges[:, 1]))))
            if (not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all()
                    or maximum_penetration > .03 or maximum_speed > 40 or maximum_excess > .10):
                raise RuntimeError(f'Unstable exhibition physics at {t:.3f} s')
            if self.presenter:
                self.presenter.after_step()
        if any(warning.number for warning in data.warning):
            raise RuntimeError('MuJoCo warning during exhibition')
        final_ball = data.qpos[self.ball_q:self.ball_q + 3]
        final_velocity = data.qvel[self.ball_v:self.ball_v + 3]
        physical = dict(
            configuration=configuration, simulated_s=float(data.time),
            initial_state_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
            evaluation=dict(
                first_foot_ball=first_foot, foot_peak_force_n=foot_peak,
                first_keeper_ball=first_keeper, keeper_peak_contact_force_n=keeper_peak,
                goal_detected=bool(goal_cross and goal_cross['inside']), goal_crossing_measured=goal_cross,
            ),
            free_keeper=dict(
                side='LEFT', preparation_start_s=prepare_s, dive_start_s=dive_start, dive_speed_scale=dive_speed,
                pelvis_height_at_kick_m=ready_height, maximum_lateral_reach_m=maximum_reach,
                final_pelvis_position_w=data.qpos[self.root_q:self.root_q + 3].tolist(),
                joint_speed_peak_rad_s=maximum_speed, joint_range_excess_peak_rad=maximum_excess,
                penetration_peak_m=maximum_penetration,
            ),
            ball_final_position_w=final_ball.tolist(), ball_final_velocity_w=final_velocity.tolist(),
            ball_prefix_error_vs_historical_probe=prefix_error,
        )
        dump(Path(output), physical)
        if enable_dive and dive_start is None:
            raise RuntimeError('The exhibition ended without a verified launch of the dive')
        return physical, dict(action=action, scenario=scenario), time.perf_counter() - start

    def evaluate(self, result, distance, action):
        probe = self.probes.get(action)
        if distance != 'long' or probe is None or result['configuration'] != probe['configuration']:
            raise ValueError('Unexpected exhibition calibration')
        prefix_error = result['ball_prefix_error_vs_historical_probe']
        if prefix_error > 1e-8:
            raise RuntimeError(f'Ball deviated before keeper contact or goal crossing: {prefix_error:.3g}')
        label = classify(result, probe)
        if label == 'save_with_contact_and_goal_counterfactual':
            x, y, _ = result['ball_final_position_w']
            vx = result['ball_final_velocity_w'][0]
            if x < 5. and (vx <= .05 or abs(y) >= 1.5):
                return 'save', prefix_error
        elif label in ('goal', 'miss'):
            return label, prefix_error
        raise RuntimeError(f'Unresolved exhibition result: {label}')

    def summary(self):
        return dict(mode='free_keeper_exhibition', shot=self.last_action, runs=self.runs,
                    composition=self.composition, setup_wall_s=self.setup_wall_s,
                    final_keeper_phase=self.keeper_phase)
