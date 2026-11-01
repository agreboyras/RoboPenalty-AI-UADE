"""Paired offline coverage matrix; never accessed by the physical controller."""
from .run import bootstrap,ACTIONS
from experiments.central_block_h3a.run import dump
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def trial(folder):
    e=read(folder/'interception.json');r=read(folder/'report.json');c=read(folder/'ball_keeper_contacts.json')
    return dict(run=folder.name,category=e.get('category','RESULTADO NO CONCLUYENTE'),official_result=e.get('official_result','UNRESOLVED'),
        valid=e['physical_valid'],complete=r['steps']==7000,steps=r['steps'],goal=e.get('goal_detected'),
        impact_solver_s=r['first_foot_ball']['solver_time_s'] if r['first_foot_ball'] else None,
        contact_solver_s=c[0]['solver_s'] if c else None,contact_bodies=sorted(set(x['keeper_body'] for x in c)),
        contact_samples=len(c),peak_force_n=e.get('peak_normal_contact_force_n'),impulse_on_ball_w_Ns=e.get('total_impulse_on_ball_w_Ns'),
        incoming_min_gap_m=e.get('incoming_min_surface_gap_m'),incoming_min_solver_s=e.get('incoming_min_solver_s'),
        global_min_gap=e.get('minimum_ball_keeper_distance'),crossings=e.get('plane_crossings'),
        max_tilt_deg=r['max_keeper_tilt_deg'],max_drift_m=r['max_keeper_horizontal_drift_m'],min_height_m=r['min_keeper_height_m'],
        max_keeper_penetration_m=r['max_keeper_penetration_m'],max_joint_speed_rad_s=e.get('max_joint_speed_rad_s'),
        max_joint_excess_rad=e.get('max_joint_excess_rad'),max_saturation_s=r['max_saturation_run_s'],warnings=r['warnings'],failure=r['failure'],
        total_wall_s=r['total_wall_s'],loop_wall_s=r['loop_wall_s'],checks=e.get('checks'),
        first_contact=c[0] if c else None,last_contact=c[-1] if c else None)

def paired(center,reference):
    a=trial(center);b=trial(reference)
    with np.load(center/'trace.npz') as z:ball=z['ball'].copy();shoot=z['shooter'].copy()
    with np.load(reference/'trace.npz') as z:ref=z['ball'].copy();ref_shoot=z['shooter'].copy()
    cut=a['contact_solver_s'] if a['contact_solver_s'] is not None else min([c['time_s'] for c in b['crossings'] if c['plane_x']==5.]+[14.])
    n=min(len(ball),len(ref));mask=ball[:n,0]<=cut+1e-10
    pair=dict(verified_until_solver_s=cut,ball_exact_before_contact_or_goal=bool(np.array_equal(ball[:n][mask],ref[:n][mask])),
        shooter_exact_before_contact_or_goal=bool(np.array_equal(shoot[:n][mask],ref_shoot[:n][mask])))
    if a['contact_solver_s'] is not None:
        i=min(n-1,int(np.searchsorted(ball[:n,0],cut+1e-5)))
        pair['post_contact_velocity_difference_vs_reference_mps']=float(np.linalg.norm(ball[i,4:7]-ref[i,4:7]))
    return dict(reference=b,center=a,pair=pair)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path)
    p.add_argument('--corner-run',default='center_right_corner_m140',help='Explicit selection; failed initialization is retained')
    args=p.parse_args();base=args.root
    if Path(args.corner_run).name!=args.corner_run:p.error('corner-run must be a directory name inside root')
    selected={a:('center_'+a) for a in ACTIONS};selected['right_corner_m140']=args.corner_run
    matrix={a:paired(base/selected[a],base/('reference_'+a)) for a in ACTIONS}
    repeat_results={}
    for action in ACTIONS:
        found=[]
        for folder in sorted(base.glob('repeat_'+action+'_*')):
            if not folder.is_dir() or not (folder/'interception.json').exists():continue
            row=paired(folder,base/('reference_'+action))
            with np.load(base/('center_'+action)/'trace.npz') as a,np.load(folder/'trace.npz') as b:
                row['bitwise_vs_first_center']={k:bool(np.array_equal(a[k],b[k])) for k in a.files}
            found.append(row)
        repeat_results[action]=found
    protected=read(base/'previous_experiments_sha256.json');root=bootstrap.PROJECT.parents[1]
    changed=[n for n,h in protected.items() if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    stable=read(root/'validation/keeper_center_h25/protected_before.json')
    stable_changed=[n for n,h in stable.items() if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    with np.load(root/'validation/central_block_h3a/center_00/trace.npz') as a,np.load(base/'center_center/trace.npz') as b:
        center_h3a={k:bool(np.array_equal(a[k],b[k])) for k in a.files}
    failures=[]
    for folder in sorted(base.glob('center_*')):
        if folder.is_dir() and (folder/'report.json').exists():
            r=read(folder/'report.json')
            if r['failure']:failures.append(dict(run=folder.name,steps=r['steps'],failure=r['failure']))
    visual=[]
    for folder in sorted(base.glob('viewer_*')):
        if not folder.is_dir() or not (folder/'interception.json').exists():continue
        e=read(folder/'interception.json');r=read(folder/'report.json')
        if e['physical_valid']:
            action=e['action'];row=paired(folder,base/('reference_'+action))
            with np.load(base/selected[action]/'trace.npz') as a,np.load(folder/'trace.npz') as b:
                row['bitwise_vs_headless']={k:bool(np.array_equal(a[k],b[k])) for k in a.files}
            visual.append(row)
        else:visual.append(dict(run=folder.name,valid=False,steps=r['steps'],failure=r['failure']))
    out=dict(matrix=matrix,selected_center_runs=selected,failed_attempts=failures,visual_attempts=visual,repetitions=repeat_results,center_exact_vs_h3a=center_h3a,
        previous_experiments_count=len(protected),previous_experiments_changed=changed,stable_count=len(stable),stable_changed=stable_changed,
        note='Distances are measured native solver geometry. Repeated nominal traces do not establish robustness to perturbations.')
    dump(base/'coverage.json',out)
    with (base/'coverage.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.writer(f);writer.writerow(['action','reference_result','center_category','contact_bodies','incoming_min_gap_m','peak_force_n','valid','contact_solver_s'])
        for action,v in matrix.items():
            c=v['center'];writer.writerow([action,v['reference']['official_result'],c['category'],';'.join(c['contact_bodies']),c['incoming_min_gap_m'],c['peak_force_n'],c['valid'],c['contact_solver_s']])
    print(json.dumps({a:dict(category=v['center']['category'],gap=v['center']['incoming_min_gap_m'],contacts=v['center']['contact_samples'],valid=v['center']['valid'],pair=v['pair']) for a,v in matrix.items()},indent=2))

if __name__=='__main__':main()
