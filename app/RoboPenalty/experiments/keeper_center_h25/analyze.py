"""Offline diagnostics; recorded samples never feed a maneuver decision."""
import argparse
import json
from pathlib import Path
import numpy as np
from experiments.free_keeper_stadium_h1.run import dump


def first_crossing(time,signal,level,start=2.):
    ids=np.flatnonzero(time>=start)
    for i in ids:
        if signal[i]>=level:
            if i==0 or time[i-1]<start or signal[i]==signal[i-1]:return float(time[i])
            u=(level-signal[i-1])/(signal[i]-signal[i-1])
            return float(time[i-1]+u*(time[i]-time[i-1]))
    return None


def arrivals(project):
    catalog=json.loads((project/'phase8c/catalog_v1.json').read_text());out={}
    for name,entry in catalog['actions'].items():
        raw=json.loads((project/'phase8c'/entry['probe']).read_text());e=raw['evaluation']
        shot=e['first_foot_ball']['time_sim_s'];trace=raw['trace']
        times=np.array([r['observation']['time_s'] for r in trace]);xyz=np.array([r['observation']['ball_position_w'] for r in trace])
        center=first_crossing(times,xyz[:,0],4.2,shot)
        out[name]=dict(first_foot_ball_s=shot,
            time_to_X4_measured_s=e['approach_crossing_measured']['time_sim_s']-shot,
            time_to_X4_2_interpolated_50Hz_s=center-shot if center is not None else None,
            time_to_goal_measured_s=e['goal_crossing_measured']['time_sim_s']-shot,
            goal_Y_m=e['goal_crossing_measured']['position_w'][1],
            source='Historical nominal calibration; not available to the runtime as future observations')
    return out


def analyze(folder):
    folder=Path(folder);r=json.loads((folder/'report.json').read_text());v=json.loads((folder/'variant.json').read_text())
    with np.load(folder/'trace.npz') as trace:
        f=trace['frames'];ball=trace['ball'].copy()
    if not len(f):return dict(valid=False,reason='No physical frames')
    t=f[:,0];pos=f[:,1:16].reshape(-1,5,3);sign=1 if v['side']=='LEFT' else -1
    arm=2 if sign==1 else 1;shoulder=4 if sign==1 else 3
    origin=pos[np.argmin(abs(t-2.))];dy=sign*(pos[:,0,1]-origin[0,1]);wy=sign*(pos[:,arm,1]-origin[arm,1])
    vy=np.gradient(pos[:,0,1],.002);wv=np.gradient(pos[:,arm,1],.002)
    valid=(t>=2.)&(dy>=.005)&(sign*vy>=.02)
    onset=None
    for i in range(len(valid)-4):
        if valid[i:i+5].all():onset=float(t[i]);break
    crossings={}
    for label,signal in [('pelvis',dy),('wrist',wy)]:
        crossings[label]={}
        for level in [.20,.40,.60]:
            at=first_crossing(t,signal,level)
            crossings[label][str(level)]=dict(absolute_s=at,from_handoff_s=at-2. if at is not None else None)
    active=t>=2.;dq=f[:,46:75];tau=f[:,162:191];ref=f[:,75:104];q=f[:,17:46]
    work={}
    for label,a,b in [('legs',0,12),('torso',12,15),('arms',15,29)]:
        power=tau[active,a:b]*dq[active,a:b]
        work[label]=dict(net_work_J=float(power.sum()*.002),absolute_work_J=float(abs(power).sum()*.002),
            max_tracking_error_rad=float(abs(ref[active,a:b]-q[active,a:b]).max()),
            max_executed_joint_excursion_rad=float(abs(q[active,a:b]-q[np.argmin(abs(t-2.)),a:b]).max()))
    peak=np.argmax(wy*(t>=2.))
    pelvis=sign*(pos[peak,0,1]-origin[0,1])
    torso=sign*((pos[peak,shoulder,1]-pos[peak,0,1])-(origin[shoulder,1]-origin[0,1]))
    chain=sign*((pos[peak,arm,1]-pos[peak,shoulder,1])-(origin[arm,1]-origin[shoulder,1]))
    prep_end=v['real_knots'][1] if v['variant']!='original' else 3.
    prep=(t>=2.)&(t<=prep_end)
    source=r['metrics']
    return dict(valid=r['success'],variant=v['variant'],side=v['side'],component=v['component'],
        handoff_time_s=2.,reference_handoff_jump_rad=0. if np.array_equal(r['handoff']['last_policy_reference'],r['handoff']['first_owned_reference']) else None,
        last_policy_time_s=r['last_policy_time_s'],policy_decisions=r['policy_decisions'],
        scheduled_hold_after_handoff_s=0. if v['variant']!='original' else .2,
        scheduled_preparation_s=prep_end-2. if v['variant']!='original' else .8,
        first_pelvis_motion_s=onset,onset_delay_from_handoff_s=onset-2. if onset is not None else None,
        physical_onset_after_push_reference_s=onset-prep_end if onset is not None else None,
        thresholds=crossings,max_pelvis_toward_m=float(dy[active].max()),max_wrist_toward_m=float(wy[active].max()),
        peak_pelvis_lateral_speed_m_s=float(abs(vy[active]).max()),peak_wrist_lateral_speed_m_s=float(abs(wv[active]).max()),
        preparation_pelvis_drop_m=float(origin[0,2]-pos[prep,0,2].min()),
        max_tilt_deg=source['max_tilt_deg'],max_penetration_m=source['max_penetration_m'],
        max_joint_excess_rad=source['max_joint_excess_rad'],max_saturation_s=max(source['saturation_longest_s']),
        final_pelvis=pos[-1,0].tolist(),max_body_longitudinal_displacement_m=float(abs(pos[active,0,0]-origin[0,0]).max()),
        wrist_peak_decomposition=dict(time_s=float(t[peak]),wrist_delta_m=float(wy[peak]),pelvis_delta_m=float(pelvis),
            shoulder_relative_to_pelvis_delta_m=float(torso),wrist_relative_to_shoulder_delta_m=float(chain),
            note='Exact geometric decomposition at one instant, NOT isolated causal contributions'),
        joint_groups=work,ball_max_horizontal_displacement_m=float(abs(ball[:,1:3]-ball[0,1:3]).max()),
        ball_max_speed_m_s=float(np.linalg.norm(ball[:,4:7],axis=1).max()),
        warning='Work and tracking are measured; group work percentages are not causal attribution. No save evaluated.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);a=p.parse_args()
    target=a.run/'diagnosis.json'
    if target.exists():p.error('diagnosis.json already exists; not overwritten')
    value=analyze(a.run);dump(target,value);print(json.dumps(value,indent=2))


if __name__=='__main__':main()
