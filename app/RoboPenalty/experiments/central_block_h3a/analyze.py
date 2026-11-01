"""Offline paired comparison; no physics or decision feedback."""
from experiments.free_keeper_stadium_h1 import bootstrap
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from .run import dump

def compare(folder,reference):
    e=json.loads((folder/'interception.json').read_text());r=json.loads((folder/'report.json').read_text())
    with np.load(folder/'trace.npz') as z:ball=z['ball'].copy();arrays={n:z[n].copy() for n in z.files}
    with np.load(reference/'trace.npz') as z:ref=z['ball'].copy();ref_shooter=z['shooter'].copy()
    event=e['first_keeper_ball'];when=event['solver_s'] if event else 14.
    pre=ball[:,0]<=when+1e-10
    eq=bool(ball.shape==ref.shape and np.array_equal(ball[pre],ref[pre]))
    i=int(np.searchsorted(ball[:,0],when+1e-5));i=min(i,len(ball)-1)
    vdiff=float(np.linalg.norm(ball[i,4:7]-ref[i,4:7]))
    points={}
    for dt in (0.,.01,.02,.1,.5):
        j=min(len(ball)-1,int(np.searchsorted(ball[:,0],when+dt+1e-5)))
        points[str(dt)]=dict(time_s=ball[j,0],ball_position_w=ball[j,1:4],velocity_w=ball[j,4:7],reference_velocity_w=ref[j,4:7])
    return dict(run=folder.name,status=e['status'],official_result=e['official_result'],physical_valid=e['physical_valid'],
        checks=e['checks'],steps=e['steps'],impact_solver_s=e['first_foot_ball']['solver_time_s'] if e['first_foot_ball'] else None,
        first_keeper_contact_solver_s=when if event else None,keeper_contact_body=event['keeper_body'] if event else None,
        plane4_2_crossings=[c for c in e['plane_crossings'] if c['plane_x']==4.2],goal_crossings=e['goal_crossings'],
        peak_force_n=e['peak_normal_contact_force_n'],contact_samples=e['contact_samples'],
        impulse_on_ball_w_Ns=e['total_impulse_on_ball_w_Ns'],ball_trace_exact_before_contact=eq,
        shooter_exact_before_contact=bool(np.array_equal(arrays['shooter'][pre],ref_shooter[pre])),
        velocity_difference_vs_reference_first_contact_step_mps=vdiff,points_after_contact=points,
        max_ball_x_m=float(ball[:,1].max()),final_ball_position_w=ball[-1,1:4],
        max_keeper_tilt_deg=r['max_keeper_tilt_deg'],max_keeper_drift_m=r['max_keeper_horizontal_drift_m'],
        min_keeper_height_m=r['min_keeper_height_m'],max_keeper_penetration_m=r['max_keeper_penetration_m'],
        max_joint_speed_rad_s=e['max_joint_speed_rad_s'],max_joint_excess_rad=e['max_joint_excess_rad'],
        saturation_run_s=r['max_saturation_run_s'],h1_legacy_success=r['success'],h1_legacy_failed_checks=[n for n,v in r['checks'].items() if not v],
        loop_wall_s=e['loop_wall_s'],total_wall_s=e['total_wall_s'],warnings=r['warnings'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);a=p.parse_args()
    ref=a.root/'reference_aside_01';names=['center_00']+[f'center_repeat_{i:02}' for i in (1,2,3)]
    rows=[compare(a.root/n,ref) for n in names]
    equal={}
    with np.load(a.root/names[0]/'trace.npz') as first:
        for n in names[1:]:
            with np.load(a.root/n/'trace.npz') as other:equal[n]={k:bool(np.array_equal(first[k],other[k])) for k in first.files}
    protected=json.loads((a.root/'previous_experiments_sha256.json').read_text(encoding='utf-8-sig'))
    root=bootstrap.PROJECT.parents[1]
    changed=[n for n,h in protected.items() if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    old=json.loads((root/'validation/keeper_center_h25/protected_before.json').read_text())
    stable_changed=[n for n,h in old.items() if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    baseline=json.loads((ref/'interception.json').read_text())
    success=bool(baseline['physical_valid'] and baseline['goal_detected'] and all(
        r['status']=='ATAJADA DEMOSTRADA' and r['physical_valid'] and r['ball_trace_exact_before_contact']
        and r['velocity_difference_vs_reference_first_contact_step_mps']>1e-6 for r in rows)
        and all(all(v.values()) for v in equal.values()) and not changed and not stable_changed)
    viewer=None
    if (a.root/'center_viewer_01/interception.json').exists():
        viewer=compare(a.root/'center_viewer_01',ref)
        with np.load(a.root/names[0]/'trace.npz') as first,np.load(a.root/'center_viewer_01/trace.npz') as visual:
            viewer['headless_bitwise']={k:bool(np.array_equal(first[k],visual[k])) for k in first.files}
        success &= viewer['physical_valid'] and all(viewer['headless_bitwise'].values())
    out=dict(status='ATAJADA DEMOSTRADA' if success else 'NO DEMOSTRADA',reference=compare(ref,ref),viewer=viewer,
        centered=rows,repetitions_bitwise=equal,previous_experiments_count=len(protected),previous_experiments_changed=changed,
        stable_protected_count=len(old),stable_changed=stable_changed)
    dump(a.root/'comparison.json',out);print(json.dumps(out,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item()))

if __name__=='__main__':main()
