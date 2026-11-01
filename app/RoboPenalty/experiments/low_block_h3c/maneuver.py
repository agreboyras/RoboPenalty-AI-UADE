"""Bounded reference residual. Inputs contain no preset or future trajectory."""
import numpy as np

PROTOCOL=dict(physics_dt=.002,decision_dt=.02,ramp_s=.30,recovery_s=.35,max_hold_from_trigger_s=1.8,
    min_vx=.8,min_predicted_y=.18,max_predicted_y=.50,plane_x=4.1,max_eta_s=1.5,
    max_reference_residual_speed_rad_s=.6,max_reference_residual_acceleration_rad_s2=6.,
    permitted_amplitudes_rad=(.04,.08))

def smooth(x):
    x=float(np.clip(x,0.,1.));return x*x*x*(10.-15.*x+6.*x*x)

class LowBlock:
    def __init__(self,names,amplitude=.04,enabled=True):
        if amplitude not in PROTOCOL['permitted_amplitudes_rad']:raise ValueError('Uncalibrated amplitude')
        self.names=list(names);self.amplitude=amplitude;self.enabled=enabled
        self.trigger=None;self.release=None;self.release_weight=0.;self.count=0;self.rows=[];self.state='WAITING'

    def observe(self,t,position,velocity):
        p=np.asarray(position);v=np.asarray(velocity);prediction=None
        if not np.isfinite(np.r_[p,v,t]).all():raise ValueError('Nonfinite observation')
        if v[0]>=PROTOCOL['min_vx'] and p[0]<PROTOCOL['plane_x']:
            eta=(PROTOCOL['plane_x']-p[0])/v[0];prediction=float(p[1]+v[1]*eta)
            evidence=0<eta<=PROTOCOL['max_eta_s'] and PROTOCOL['min_predicted_y']<=prediction<=PROTOCOL['max_predicted_y'] and p[2]<=.25
        else:evidence=False
        if self.enabled and self.trigger is None:
            self.count=self.count+1 if evidence else 0
            if self.count>=2:self.trigger=float(t);self.state='RAMP'
        if self.trigger is not None and self.release is None:
            if p[0]>=4.4 or v[0]<-.2 or t-self.trigger>=PROTOCOL['max_hold_from_trigger_s']:
                self.release=float(t);self.release_weight=smooth((t-self.trigger)/PROTOCOL['ramp_s']);self.state='RECOVERY'
        self.rows.append(dict(t=float(t),position=p.tolist(),velocity=v.tolist(),evidence=bool(evidence),predicted_y=prediction,state=self.state))

    def residual(self,t):
        out=np.zeros(29)
        if not self.enabled or self.trigger is None:return out
        if self.release is None:
            weight=smooth((t-self.trigger)/PROTOCOL['ramp_s'])
            self.state='RAMP' if t-self.trigger<PROTOCOL['ramp_s'] else 'HOLD'
        else:
            weight=self.release_weight*(1.-smooth((t-self.release)/PROTOCOL['recovery_s']))
            self.state='RECOVERY' if t-self.release<PROTOCOL['recovery_s'] else 'DONE'
        out[self.names.index('right_hip_roll_joint')]=-self.amplitude*weight
        out[self.names.index('right_ankle_roll_joint')]=self.amplitude*weight
        return out
