"""Finite reference trajectory; the unchanged PD is the only torque producer."""
import numpy as np

PROTOCOL=dict(transfer_s=2.,takeover_end_s=2.2,preparation_end_s=3.,
    push_end_s=3.55,extension_end_s=4.2,final_blend_end_s=4.8,duration_s=6.,
    transfer_trial_duration_s=3.,minimum_pelvis_toward_m=.20,
    minimum_wrist_toward_m=.30,minimum_arm_relative_toward_m=.10,
    max_penetration_m=.02,abort_penetration_m=.03,max_joint_excess_rad=.03,
    abort_joint_excess_rad=.10,max_joint_speed_rad_s=20.,abort_joint_speed_rad_s=40.,
    max_reference_speed_rad_s=3.,max_reference_acceleration_rad_s2=20.)


def smooth(t):
    t=np.clip(t,0.,1.)
    return t*t*t*(10-15*t+6*t*t)


def interpolate(a,b,t):return a+smooth(t)*(b-a)


def targets(start,names,side):
    """LEFT is world +Y; the keeper faces -X, so it uses its right arm."""
    if side not in ('LEFT','RIGHT'):raise ValueError(side)
    sign=1. if side=='LEFT' else -1.
    arm='right' if side=='LEFT' else 'left'
    prepare=np.array(start,copy=True)
    def setq(q,name,v):q[names.index(name+'_joint')]=v
    for leg in ('left','right'):
        for part,delta in [('knee',.18),('hip_pitch',-.09),('ankle_pitch',-.09)]:
            prepare[names.index(f'{leg}_{part}_joint')]+=delta
        setq(prepare,leg+'_shoulder_roll',.55 if leg=='left' else -.55)
        setq(prepare,leg+'_shoulder_pitch',.25)
        setq(prepare,leg+'_elbow',.70)
    setq(prepare,'waist_pitch',.04)
    push=prepare.copy()
    for leg in ('left','right'):
        setq(push,leg+'_knee',.22);setq(push,leg+'_hip_pitch',-.10)
        setq(push,leg+'_ankle_pitch',-.12);setq(push,leg+'_hip_roll',sign*.08)
        setq(push,leg+'_ankle_roll',-sign*.20)
    setq(push,'waist_roll',sign*.15)
    setq(push,arm+'_shoulder_roll',-1.15 if arm=='right' else 1.15)
    setq(push,arm+'_shoulder_pitch',-.15);setq(push,arm+'_elbow',.30)
    extend=push.copy()
    for leg in ('left','right'):
        setq(extend,leg+'_hip_roll',sign*.10);setq(extend,leg+'_ankle_roll',-sign*.24)
        setq(extend,leg+'_hip_pitch',-.20)
    setq(extend,'waist_roll',sign*.22)
    setq(extend,arm+'_shoulder_roll',-1.45 if arm=='right' else 1.45)
    setq(extend,arm+'_elbow',.18)
    return prepare,push,extend


class Maneuver:
    def __init__(self,names,side,mode,ranges):
        self.names=list(names);self.side=side;self.mode=mode;self.ranges=np.asarray(ranges)
        self.state='BALANCE';self.start=None;self.final=None;self.transitions=[]
        self.handoff_reference_jump=None

    def reference(self,t,policy_target,actual):
        old=self.state
        if self.mode=='balance' or t<PROTOCOL['transfer_s']-1e-9:
            result=np.asarray(policy_target).copy();self.state='BALANCE'
        else:
            if self.start is None:
                self.start=np.asarray(policy_target).copy()
                self.handoff_reference_jump=float(np.max(abs(self.start-policy_target)))
                if self.mode!='transfer':self.prepare,self.push,self.extend=targets(self.start,self.names,self.side)
            if self.mode=='transfer':self.state='OWN_HOLD';result=self.start.copy()
            elif t<2.2:self.state='TAKEOVER';result=self.start.copy()
            elif t<3.:self.state='PREPARING';result=interpolate(self.start,self.prepare,(t-2.2)/.8)
            elif t<3.55:self.state='LATERAL_PUSH';result=interpolate(self.prepare,self.push,(t-3.)/.55)
            elif t<4.2:self.state='EXTENDING';result=interpolate(self.push,self.extend,(t-3.55)/.65)
            else:
                if self.final is None:self.final=np.clip(actual,self.ranges[:,0]+.02,self.ranges[:,1]-.02)
                self.state='FINALIZING' if t<4.8 else 'FINISHED_HOLD'
                result=interpolate(self.extend,self.final,(t-4.2)/.6)
        if np.any(result<self.ranges[:,0]) or np.any(result>self.ranges[:,1]):
            raise ValueError('Reference outside original joint limits')
        if self.state!=old:self.transitions.append(dict(time_s=t,state=self.state))
        return result
