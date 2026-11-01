"""Post-episode comparison, never fed to the low-block controller."""
from .run import bootstrap,dump
from pathlib import Path
import argparse,json,hashlib
import numpy as np

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def compare(folder,baseline):
    e=read(folder/'interception.json')
    with np.load(folder/'trace.npz') as z:trace={k:z[k].copy() for k in z.files}
    with np.load(baseline/'trace.npz') as z:base={k:z[k].copy() for k in z.files}
    result=dict(run=folder.name,result=e)
    if folder.name.startswith('control'):
        result['exact_vs_passive']={k:bool(np.array_equal(trace[k],base[k])) for k in trace}
        return result
    event=e['first_keeper_ball'];time=event['solver_s'] if event else 14.
    with np.load(folder/'maneuver.npz') as z:cmd=z['commands'].copy();points=z['points'].copy()
    with np.load(baseline/'maneuver.npz') as z:bp=z['points'].copy()
    i=int(np.argmin(abs(trace['keeper'][:,0]-time)));j=int(np.argmin(abs(points[:,0]-time)))
    delta=trace['keeper'][i,14:43]-base['keeper'][i,14:43]
    joint_onset=None;max_knee_toward=None
    if e['shot_detection_s'] is not None:
        t=trace['keeper'][:,0];difference=trace['keeper'][:,21]-base['keeper'][:,21]
        moving=(t>=e['shot_detection_s'])&(abs(difference)>=.001)
        joint_onset=next((float(t[j]) for j in range(len(t)-4) if moving[j:j+5].all()),None)
        window=(points[:,0]>=e['shot_detection_s'])&(points[:,0]<=time)
        max_knee_toward=float((points[window,5]-bp[window,5]).max()) if window.any() else None
    n=min(len(trace['ball']),len(base['ball']));mask=trace['ball'][:n,0]<=time+1e-10
    root=bootstrap.PROJECT.parents[1];ref=root/'validation/passive_coverage_h3b/reference_left_near_b060/trace.npz'
    with np.load(ref) as z:
        ball_prefix=bool(np.array_equal(trace['ball'][:n][mask],z['ball'][:n][mask]))
        shooter_prefix=bool(np.array_equal(trace['shooter'][:n][mask],z['shooter'][:n][mask]))
    result.update(leg_actual_delta_at_contact_rad=dict(right_hip_roll=float(delta[7]),right_ankle_roll=float(delta[11])),
        point_delta_at_contact_world_m=dict(pelvis=points[j,1:4]-bp[j,1:4],right_knee=points[j,4:7]-bp[j,4:7],right_ankle=points[j,7:10]-bp[j,7:10]),
        requested_residual_at_contact_rad=cmd[i,30:59],raw_policy_at_contact_rad=cmd[i,1:30],final_reference_at_contact_rad=cmd[i,59:88],
        detection_latency_from_solver_foot_contact_s=e['shot_detection_s']-e['first_foot_ball']['solver_time_s'] if e['shot_detection_s'] is not None else None,
        reference_onset_delay_from_detection_s=e['maneuver_start_s']-e['shot_detection_s'] if e['shot_detection_s'] is not None else None,
        physical_hip_response_onset_s=joint_onset,physical_hip_response_delay_s=joint_onset-e['shot_detection_s'] if joint_onset is not None else None,
        response_definition='Descriptive onset: >=0.001 rad hip difference vs passive for 5 consecutive samples; not an acceptance threshold',
        maximum_knee_toward_ball_delta_y_before_contact_m=max_knee_toward,
        ball_exact_vs_unobstructed_until_contact=ball_prefix,shooter_exact_vs_unobstructed_until_contact=shooter_prefix,
        first_contact_velocity=event['ball_velocity_before_w'] if event else None)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);a=p.parse_args();base=a.root
    runs={}
    for n in ('active_p040_01','active_p040_02','viewer_active_p040_01'):
        if (base/n/'interception.json').exists():
            r=read(base/n/'interception.json')
            runs[n]=compare(base/n,base/'passive_left_01') if r.get('physical_valid') else dict(run=n,result=r)
    if (base/'control_center_01/interception.json').exists():
        runs['control_center_01']=compare(base/'control_center_01',bootstrap.PROJECT.parents[1]/'validation/passive_coverage_h3b/center_center')
    equal={}
    for n in ('active_p040_02','viewer_active_p040_01'):
        if (base/n/'trace.npz').exists() and runs.get(n,{}).get('result',{}).get('physical_valid'):
            with np.load(base/'active_p040_01/trace.npz') as first,np.load(base/n/'trace.npz') as other:
                equal[n]={k:bool(np.array_equal(first[k],other[k])) for k in first.files}
    protected=read(base/'previous_experiments_sha256.json');bundle=bootstrap.PROJECT.parents[1]
    changed=[n for n,h in protected.items() if hashlib.sha256((bundle/n).read_bytes()).hexdigest()!=h]
    stable=read(bundle/'validation/keeper_center_h25/protected_before.json')
    old_changed=[n for n,h in stable.items() if hashlib.sha256((bundle/n).read_bytes()).hexdigest()!=h]
    passive=read(base/'passive_left_01/interception.json');reference=read(base/'reference_left_01/interception.json') if (base/'reference_left_01/interception.json').exists() else None
    comparisons={}
    for label,folder,other in (
        ('passive_vs_h3b',base/'passive_left_01',bundle/'validation/passive_coverage_h3b/center_left_near_b060'),
        ('fresh_reference_vs_h3b',base/'reference_left_01',bundle/'validation/passive_coverage_h3b/reference_left_near_b060')):
        if (folder/'trace.npz').exists():
            with np.load(folder/'trace.npz') as a,np.load(other/'trace.npz') as b:
                comparisons[label]={k:bool(np.array_equal(a[k],b[k])) for k in a.files}
    active=[v['result'] for v in runs.values() if v.get('result',{}).get('action')=='left_near_b060' and v['result'].get('physical_valid')]
    conclusion='Requires review; no repeated active save established'
    if active and all(r['official_result']=='GOAL' and abs(r['impulse_on_ball_w_Ns'][0])<abs(passive['impulse_on_ball_w_Ns'][0]) for r in active):
        conclusion='No useful improvement with 0.04 rad; calibration stopped without increasing amplitude'
    out=dict(runs=runs,passive=passive,fresh_reference=reference,exact_baselines=comparisons,active_reproducibility=equal,previous_experiments_count=len(protected),previous_experiments_changed=changed,stable_count=len(stable),stable_changed=old_changed,
        conclusion=conclusion,
        note='Measured movement and outcome, not success inferred from target references. No generalization beyond the central control.')
    dump(base/'comparison.json',out);print(json.dumps(out,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item()))

if __name__=='__main__':main()
