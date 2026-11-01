"""Causal rule-based shadow agent. No MuJoCo objects, preset or future input."""
from dataclasses import asdict, dataclass
from types import SimpleNamespace
import math
from phase3b.predictor import predict


@dataclass(frozen=True)
class Observation:
    time_s: float
    ball_position_w: tuple
    ball_velocity_w: tuple
    keeper_position_w: tuple
    keeper_quaternion_w: tuple
    phase: str


# Historical H3B nominal central, keeper centered: incoming unobstructed X=4.2.
# Similarity tolerance is an engineering abstention rule, NOT measured coverage.
CENTRAL_Y = -0.10970022205505191
CATALOG = {
    'MANTENER_CENTRO': dict(evidence='H3A/H3B nominal central: physical SAVE, 3 repeats',
                            status='demonstrated_nominal_only', risk='existing_balance'),
    'BLOQUEO_BAJO': dict(evidence='H3C contact worsened; no active SAVE',
                         status='experimental_not_validated', risk='contact_and_stability'),
    'CAIDA_LATERAL': dict(evidence='H2 approximately 2 s for 0.20 m; not timely',
                          status='experimental_not_validated', risk='fall_and_latency'),
    'SIN_ACCION_VIABLE': dict(evidence='abstention; does not switch off balance',
                             status='no_evidenced_intervention', risk='unblocked_shot'),
}


class Agent:
    def __init__(self):
        self.detected_s = None
        self.history = []

    def observe(self, o):
        values = (o.time_s, *o.ball_position_w, *o.ball_velocity_w,
                  *o.keeper_position_w, *o.keeper_quaternion_w)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Nonfinite observation')
        x, _, _ = o.ball_position_w
        vx, _, _ = o.ball_velocity_w
        # Physical motion only, not a preset label or absolute calibrated timer.
        if self.detected_s is None and vx > .5 and x < 4.2:
            self.detected_s = o.time_s
        # Adapter fields are mathematical coordinates only; no rail control used.
        p = predict(SimpleNamespace(ball_position_w=o.ball_position_w,
            ball_velocity_w=o.ball_velocity_w, keeper_q=0., keeper_v=0.,
            time_s=o.time_s, plane_x=4.2, rail_origin_y=0., rail_axis_y=1.))
        action = 'SIN_ACCION_VIABLE'
        why = 'No approaching detected shot with a supported prediction'
        centered = abs(o.keeper_position_w[0]-4.2) <= .05 and abs(o.keeper_position_w[1]) <= .05
        w, qx, qy, qz = o.keeper_quaternion_w
        upright = 1-2*(qx*qx+qy*qy) >= math.cos(math.radians(15))
        # Yaw must face the striker (-X), not merely be upright.
        facing = 1-2*(qy*qy+qz*qz) < -.95
        eligible = self.detected_s is not None and p.valid and o.phase == 'SHOOTING'
        near = (p.y_w is not None and abs(p.y_w-CENTRAL_Y) <= .02 and
                p.z_w is not None and abs(p.z_w-.115) <= .02)
        if eligible:
            if centered and upright and facing and near:
                action = 'MANTENER_CENTRO'
                why = 'Prediction similar to demonstrated nominal central; no additional movement, no SAVE guarantee'
            else:
                why = 'Outside nominal central similarity or pose; experimental movements lack evidence of timely SAVE'
        window = [r['prediction']['y_w'] for r in self.history[-9:]
                  if r['prediction']['valid'] and r['prediction']['y_w'] is not None]
        if p.valid: window.append(p.y_w)
        spread = max(window)-min(window) if window else None
        alternatives = {k: dict(v, eligible=(k==action),
            available_s=p.eta_s if p.valid else None,
            timing_assessment=('no extra motion latency' if k=='MANTENER_CENTRO' else
                ('insufficient: H2 measured approximately 2 s for 0.20 m' if p.valid and p.eta_s < 2. else
                 'time alone does not demonstrate interception') if k=='CAIDA_LATERAL' else
                'no useful dynamic reach demonstrated' if k=='BLOQUEO_BAJO' else 'abstain, keep physical controller unchanged'),
            rejection=None if k==action else 'Not supported for this observation; experimental evidence is not a SAVE capability')
            for k,v in CATALOG.items()}
        row = dict(observation=asdict(o), detected_s=self.detected_s,
            prediction={k:v for k,v in asdict(p).items() if k!='rail_target_m'},
            uncertainty=dict(recent_y_range_m=spread,
                kind='descriptive_only_not_confidence_interval',
                limitations='Constant horizontal velocity; friction, bounces and robot contacts not predicted; no probabilistic uncertainty'),
            action=action, reason=why, alternatives=alternatives)
        self.history.append(row)
        return row
