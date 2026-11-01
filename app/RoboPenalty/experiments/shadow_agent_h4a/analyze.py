"""Post-episode reporting only. Never imported by Agent or its controller."""
import argparse
import csv
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('outputs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();rows=[]
    for folder in a.outputs:
        s=json.loads((folder/'summary.json').read_text());r=s['latest_incoming']
        cf=s['counterfactual_aside_errors'];actual=s['actual_unobstructed_errors']
        def last(seq,key):return seq[-1][key] if seq else None
        rows.append(dict(action=s['action'],detected_s=s['detected_s'],latency_s=s['detection_latency_s'],
            recommendation=r['action'] if r else None,
            observation_s=r['observation']['time_s'] if r else None,
            eta_s=r['prediction']['eta_s'] if r else None,
            y_m=r['prediction']['y_w'] if r else None,z_m=r['prediction']['z_w'] if r else None,
            actual_y_error_m=last(actual,'y_error_m'),actual_z_error_m=last(actual,'z_error_m'),
            actual_arrival_error_s=last(actual,'arrival_error_s'),
            aside_y_error_m=last(cf,'y_error_m'),aside_z_error_m=last(cf,'z_error_m'),
            aside_arrival_error_s=last(cf,'arrival_error_s'),
            first_aside_y_error_m=cf[0]['y_error_m'] if cf else None,
            first_aside_arrival_error_s=cf[0]['arrival_error_s'] if cf else None,
            result=s['physical_result'],category=s['category'],physical_valid=s['physical_valid'],
            readonly=s['readonly_state'],exact=all(s['exact_baseline'].values()),steps=s['steps']))
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
    with (a.output/'comparison.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    print(json.dumps(rows,indent=2))
    return 0 if all(r['physical_valid'] and r['readonly'] and r['exact'] and r['steps']==7000 for r in rows) else 2


if __name__=='__main__':raise SystemExit(main())
