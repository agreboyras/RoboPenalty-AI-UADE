"""Offline timing and reach. A falling or opposite-direction motion is not useful reach."""
from experiments.free_keeper_stadium_h1 import bootstrap
from experiments.central_block_h3a.run import dump
from .maneuver import PROTOCOL,partial
import argparse,json,hashlib
from pathlib import Path
import numpy as np

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def sustained(t,mask,start=2.,seconds=.04):
    # Sample timestamps must span the full interval (21 samples span 40 ms).
    count=max(1,int(round(seconds/.002))+1)
    eligible=(t>=start-1e-9)&mask
    for i in np.flatnonzero(eligible):
        if i+count<=len(t) and eligible[i:i+count].all():return dict(onset_s=float(t[i]),confirmed_s=float(t[i+count-1]),elapsed_confirmed_s=float(t[i+count-1]-start))
    return None

def crossing(t,y,value):
    for i in np.flatnonzero((t>=2.-1e-9)&(y>=value)):
        if i>0 and t[i-1]>=2.-1e-9 and y[i]!=y[i-1]:return float(t[i-1]+(value-y[i-1])/(y[i]-y[i-1])*(t[i]-t[i-1])-2.)
        return float(t[i]-2.)
    return None

def summarize(folder,baseline):
    r=read(folder/'report.json');cfg=read(folder/'configuration.json');z=np.load(folder/'trace.npz');b=np.load(baseline/'trace.npz')
    t=z['time'];origin=z['point'][np.argmin(abs(t-2.))];dy=z['point'][:,1]-origin[1]
    active=t>=2.;deadline=active&(t<=2.+.874+1e-9);load=z['load'];R=r['baseline_right_n_mean'];weight=cfg['weight_n']
    avg=np.array([load[max(0,i-19):i+1].mean(axis=0) for i in range(len(t))])
    good=np.array([partial(v,R,weight) for v in avg]);release=(avg[:,1]<=.10*R)&(avg[:,0]>=.55*weight)&(z['clearance'][:,1]>=.002)
    thresholds={str(v):crossing(t,dy,v) for v in (.02,.05,.10)}
    wrong={str(v):crossing(t,-dy,v) for v in (.02,.05,.10)}
    onset=sustained(t,(avg[:,1]<=.90*R)&(avg[:,0]>=.55*weight))
    transfer=sustained(t,good);free=sustained(t,release,seconds=.02)
    equal_to_baseline_prefix={key:bool(np.array_equal(z[key][t<2.-1e-9],b[key][b['time']<2.-1e-9])) for key in ('qpos','qvel','load','com','point')}
    relative=z['point'][:,1]-b['point'][:len(t),1]
    candidate=deadline&(dy>=.02)&(relative>=.015)&(z['point'][:,2]>=.03)&(z['point'][:,2]<=.23)
    if r['fall_time_s'] is not None:candidate &= t<r['fall_time_s']
    if transfer and free:candidate &= t>=max(transfer['confirmed_s'],free['confirmed_s'])
    else:candidate[:]=False
    success=bool(r['physical_valid'] and transfer and free and candidate.any())
    brief=active&(load[:,1]<1.)&(z['clearance'][:,1]>0)&(load[:,0]>=.55*weight)
    return dict(run=folder.name,report=r,first_effective_unloading=onset,partial_unload_offline=transfer,foot_release_offline=free,
        toward_ball_thresholds_elapsed_s=thresholds,opposite_direction_thresholds_elapsed_s=wrong,
        maximum_toward_ball_before_deadline_m=float(dy[deadline].max()),maximum_toward_ball_anytime_m=float(dy[active].max()),
        final_point_signed_y_displacement_m=float(dy[-1]),max_baseline_relative_gain_before_deadline_m=float(relative[deadline].max()),
        min_right_normal_n_before_deadline=float(load[deadline,1].min()),min_right_load_share_before_deadline=float((load[deadline,1]/np.maximum(load[deadline].sum(axis=1),1)).min()),
        max_right_load_share_before_deadline=float((load[deadline,1]/np.maximum(load[deadline].sum(axis=1),1)).max()),
        first_brief_force_free_positive_clearance_elapsed_s=float(t[np.flatnonzero(brief)[0]]-2.) if brief.any() else None,
        max_right_clearance_before_deadline_m=float(z['clearance'][deadline,1].max()),
        point_height_range_m=[float(z['point'][active,2].min()),float(z['point'][active,2].max())],
        min_support_margin_m=float(np.nanmin(z['margin'][active])),max_pelvis_speed_mps=float(np.linalg.norm(z['root_velocity'][active],axis=1).max()),
        reference_onset_elapsed_s=next((float(t[i]-2.) for i in range(len(t)) if abs(z['residual'][i]).max()>1e-8),None),
        useful_and_fast=success,exact_pre_transfer_vs_baseline=equal_to_baseline_prefix,
        timing_note='Force feedback online uses 40 ms moving mean at 50Hz with 40ms sustain; offline confirmation uses 500Hz samples. No thresholds changed.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);a=p.parse_args();base=a.root;baseline=base/'baseline_01'
    runs={};equal={}
    for folder in sorted(base.iterdir()):
        if folder.is_dir() and not folder.name.startswith('baseline_') and (folder/'report.json').exists() and (folder/'configuration.json').exists():
            runs[folder.name]=summarize(folder,baseline)
            if folder.name!='transfer_01' and read(folder/'report.json')['steps']==3000:
                with np.load(base/'transfer_01/trace.npz') as first,np.load(folder/'trace.npz') as other:
                    equal[folder.name]={key:bool(np.array_equal(first[key],other[key],equal_nan=key in ('cop','margin'))) for key in first.files}
    baseline_reps={}
    for folder in sorted(base.glob('baseline_*')):
        if folder.is_dir() and folder.name!='baseline_01' and (folder/'trace.npz').exists():
            with np.load(baseline/'trace.npz') as first,np.load(folder/'trace.npz') as other:
                baseline_reps[folder.name]={key:bool(np.array_equal(first[key],other[key],equal_nan=key in ('cop','margin'))) for key in first.files}
    bundle=bootstrap.PROJECT.parents[1];protected=read(base/'previous_experiments_sha256.json');old=read(bundle/'validation/keeper_center_h25/protected_before.json')
    changed=[n for n,h in protected.items() if hashlib.sha256((bundle/n).read_bytes()).hexdigest()!=h]
    stable_changed=[n for n,h in old.items() if hashlib.sha256((bundle/n).read_bytes()).hexdigest()!=h]
    out=dict(baseline=read(baseline/'report.json'),baseline_repetitions=baseline_reps,runs=runs,exact_repetitions=equal,protocol=PROTOCOL,
        previous_experiment_count=len(protected),previous_experiment_changes=changed,stable_count=len(old),stable_changes=stable_changed,
        status='VIABLE' if any(v['useful_and_fast'] for v in runs.values()) else 'NO VIABLE PARA EL PROTOCOLO ENSAYADO' if any(v['report']['physical_valid'] for v in runs.values()) else 'PARCIAL',
        note='No penalty or ball trial. This does not establish impossibility of other balance controllers or transfer strategies.')
    dump(base/'comparison.json',out);print(json.dumps(out,indent=2))

if __name__=='__main__':main()
