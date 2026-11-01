import numpy as np
from experiments.lateral_keeper_h2.maneuver import Maneuver as Original,interpolate

# Declared before trials. Same joint goals and PD; only reference timing changes.
FAST_V1=np.array([2.,2.4,2.85,3.25,4.25,6.])
FAST_REAL=np.array([2.,2.5,3.,3.5,4.5,6.])
ORIGINAL_CLOCK=np.array([2.2,3.,3.55,4.2,4.8,6.])


class TimedManeuver:
    def __init__(self,names,side,mode,ranges,variant='original',component='full'):
        self.original=Original(names,side,mode,ranges)
        self.variant=variant;self.component=component;self.state='BALANCE';self.landing_set=False

    def __getattr__(self,key):return getattr(self.original,key)

    def reference(self,t,policy_target,actual):
        knots=FAST_V1 if self.variant=='fast_v1' else FAST_REAL
        clock=t if self.variant=='original' or t<2 else float(np.interp(t,knots,ORIGINAL_CLOCK))
        before=len(self.original.transitions)
        result=self.original.reference(clock,policy_target,actual)
        if self.variant=='fast' and self.original.final is not None:
            if not self.landing_set:
                arm='right' if self.original.side=='LEFT' else 'left'
                i=self.original.names.index(arm+'_elbow_joint')
                self.original.final[i]=1.0
                self.landing_set=True
            result=interpolate(self.original.extend,self.original.final,(clock-4.2)/.6)
        self.state=self.original.state
        if len(self.original.transitions)>before:
            self.original.transitions[-1].update(time_s=t,reference_clock_s=clock)
        if self.component!='full' and t>=2:
            keep=np.zeros(29,dtype=bool)
            if self.component=='legs_torso':keep[:15]=True
            elif self.component=='arms':keep[15:]=True
            else:raise ValueError('Unknown component experiment')
            result=np.where(keep,result,self.original.start)
        return result
