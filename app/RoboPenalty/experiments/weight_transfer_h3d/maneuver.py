"""Measured-load state machine. Outputs joint references, never torques or root poses."""
import numpy as np

# Frozen after baseline diagnosis and before any transfer trial.
PROTOCOL=dict(start_after_settle_s=2.,transfer_rad=.12,transfer_ramp_s=.35,transfer_timeout_s=.45,
    transfer_test_hold_s=1.2,knee_lift_rad=.12,hip_pitch_lift_rad=-.06,ankle_pitch_lift_rad=-.06,
    lift_ramp_s=.20,lift_timeout_s=.30,block_extra_roll_rad=.08,block_ramp_s=.22,block_duration_s=.45,recovery_s=.50,
    partial_share=.30,right_baseline_fraction=.65,left_weight_fraction=.55,partial_sustain_s=.04,
    release_right_baseline_fraction=.10,release_clearance_m=.002,release_sustain_s=.02,
    deadline_s=.874,minimum_useful_point_displacement_m=.02,minimum_gain_vs_baseline_m=.015,
    point_height_range_m=(.03,.23),reference_speed_rad_s=1.5,reference_acc_rad_s2=20.)

def smooth(x):
    x=float(np.clip(x,0.,1.));return x*x*x*(10.-15*x+6*x*x)

def partial(load,right_baseline,weight):
    l,r=map(float,load);return l>=.55*weight and r<=.65*right_baseline and l+r>1 and r/(l+r)<=.30

class Transfer:
    def __init__(self,names,mode,weight):
        self.names=list(names);self.mode=mode;self.weight=weight;self.start=None;self.baseline=None;self.state='WAITING'
        self.phase_start=None;self.partial_since=None;self.partial_confirmed=None;self.free_since=None;self.events=[]
        self.recover_from=np.zeros(29);self.protocol=dict(PROTOCOL)

    def event(self,t,state,**data):self.events.append(dict(t=float(t),elapsed_s=float(t-self.start),state=state,**data))

    def begin_recovery(self,t,reason):
        self.recover_from=self.residual(t).copy();self.state='RECOVERY';self.phase_start=t;self.event(t,self.state,reason=reason)

    def observe(self,t,last,arrays):
        if self.start is None:
            if t<2.-1e-9 or last is None:return
            times=np.array(arrays['time']);window=(times>=1.5)&(times<2.)
            if window.sum()<200:raise ValueError('Missing measured stable baseline')
            load=np.array(arrays['load'])[window].mean(axis=0)
            self.baseline=dict(left_n=float(load[0]),right_n=float(load[1]),point=np.array(arrays['point'])[window].mean(axis=0).tolist())
            self.start=float(t);self.phase_start=t;self.state='TRANSFER';self.event(t,self.state)
        times=np.array(arrays['time']);load_rows=np.array(arrays['load']);mask=times>=t-.04-1e-9
        load=load_rows[mask].mean(axis=0) if mask.any() else last['load']
        good=partial(load,self.baseline['right_n'],self.weight)
        self.partial_since=t if good and self.partial_since is None else self.partial_since if good else None
        if self.partial_confirmed is None and self.partial_since is not None and t-self.partial_since>=.04-1e-9:
            self.partial_confirmed=t;self.event(t,'PARTIAL_UNLOAD',left_n=float(load[0]),right_n=float(load[1]))
        if self.state=='TRANSFER':
            if self.mode=='transfer':
                if t-self.start>=1.2-1e-9:self.begin_recovery(t,'transfer_only_test_complete')
            elif self.partial_confirmed is not None and t-self.start>=.35-1e-9:
                self.state='LIFT';self.phase_start=t;self.event(t,self.state)
            elif t-self.start>=.45-1e-9:self.begin_recovery(t,'no_early_partial_unload')
        elif self.state=='LIFT':
            released=load[1]<=.10*self.baseline['right_n'] and last['clearance'][1]>=.002 and load[0]>=.55*self.weight
            self.free_since=t if released and self.free_since is None else self.free_since if released else None
            if self.free_since is not None and t-self.free_since>=.02-1e-9 and t-self.phase_start>=.20-1e-9:
                self.state='BLOCK';self.phase_start=t;self.event(t,self.state,right_clearance_m=float(last['clearance'][1]),right_n=float(load[1]))
            elif t-self.phase_start>=.30-1e-9:self.begin_recovery(t,'foot_not_released')
        elif self.state=='BLOCK' and t-self.phase_start>=.45-1e-9:self.begin_recovery(t,'block_test_complete')
        elif self.state=='RECOVERY' and t-self.phase_start>=.50-1e-9:
            self.state='DONE';self.event(t,self.state)

    def residual(self,t):
        q=np.zeros(29)
        def add(name,value):q[self.names.index(name+'_joint')]+=value
        if self.start is None or self.state in ('WAITING','DONE'):return q
        if self.state=='RECOVERY':return self.recover_from*(1-smooth((t-self.phase_start)/.50))
        transfer=smooth((t-self.start)/.35)*.12
        for side in ('left','right'):
            add(side+'_hip_roll',-transfer);add(side+'_ankle_roll',transfer)
        if self.state in ('LIFT','BLOCK'):
            lift=smooth((t-self.phase_start)/.20) if self.state=='LIFT' else 1.
            add('right_knee',.12*lift);add('right_hip_pitch',-.06*lift);add('right_ankle_pitch',-.06*lift)
        if self.state=='BLOCK':
            b=.08*smooth((t-self.phase_start)/.22);add('right_hip_roll',-b);add('right_ankle_roll',b)
        return q
