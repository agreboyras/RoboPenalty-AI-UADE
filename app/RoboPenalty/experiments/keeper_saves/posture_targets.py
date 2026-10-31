"""Reference extension only. The inherited PD remains the sole torque producer."""
from . import bootstrap
import numpy as np
from phase8b3.posture import PosturePD


def effective_caps(model,keeper,software):
    caps=np.asarray(software,dtype=float).copy()
    for i,(joint,actuator) in enumerate(zip(keeper.joints,keeper.actuators)):
        if model.actuator_ctrllimited[actuator]:
            caps[i]=min(caps[i],min(abs(model.actuator_ctrlrange[actuator])))
        if model.jnt_actfrclimited[joint]:
            caps[i]=min(caps[i],min(abs(model.jnt_actfrcrange[joint])))
    return caps


def extend(target,names,side,amount=1.):
    """LEFT/RIGHT are world +/-Y, opposite the anatomical side of the facing G1."""
    result=np.array(target,copy=True)
    if side not in ('LEFT','RIGHT'):return result
    arm='right' if side=='LEFT' else 'left'
    sign=-1 if side=='LEFT' else 1
    goals={f'{arm}_shoulder_roll_joint':sign*.95,
           f'{arm}_shoulder_pitch_joint':-.30,f'{arm}_elbow_joint':.40,
           'waist_roll_joint':sign*.08}
    for name,value in goals.items():
        i=names.index(name);result[i]+=amount*(value-result[i])
    return result


class ReachPosturePD(PosturePD):
    EXTENSION=.5  # Selected by geometric comparison; full amplitude is not automatically better.
    def __init__(self,*args,fixture_side=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fixture_side=fixture_side;self.fixture_time=0.;self.effective_limits=None

    def target(self,base):
        target=super().target(base)
        # Timed reference fixture is used ONLY in the ball-absent laboratory test.
        # Real FreeKick trials use the unchanged causal direction from PosturePD.
        if self.fixture_side is not None:
            side=self.fixture_side if 2.<=self.fixture_time<5. else 'WAIT'
            self.state=side if side!='WAIT' else ('RECOVERY' if self.fixture_time>=5 else 'WAIT')
        else:side=self.state
        target=extend(target,self.names,side,self.EXTENSION)
        ranges=self.model.jnt_range[self.keeper.joints]
        if np.any(target<ranges[:,0]+.02) or np.any(target>ranges[:,1]-.02):
            raise ValueError('Experimental reference outside safe joint range')
        return target

    def command(self,data,base,torque_limits):
        self.fixture_time=float(data.time)
        caps=effective_caps(self.model,self.keeper,torque_limits)
        self.effective_limits=caps.tolist()
        return super().command(data,base,caps)
