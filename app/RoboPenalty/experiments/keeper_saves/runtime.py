"""Optional instance-level hook, installed before 8C's motor observer runs."""
from . import bootstrap
import json
from pathlib import Path
from portability.resources import components as stable_components
from .posture_targets import ReachPosturePD,effective_caps
from .metrics import MotorMonitor


def components(catalog,*,experimental=False):
    Base,Selector=stable_components(catalog,'dynamic')
    if not experimental:return Base,Selector  # No wrapper or altered clipping when disabled.
    class Runtime(Base):
        def __init__(self):
            super().__init__()
            original_run=self.engine.run;original_mj=self.engine.mujoco;owner=self
            class Probe:
                def __getattr__(self,key):return getattr(original_mj,key)
                def mj_step(self,m,d,*args,**kwargs):
                    result=original_mj.mj_step(m,d,*args,**kwargs)
                    if owner.experiment_monitor is not None:
                        pd=owner.posture
                        owner.experiment_monitor.sample(d,pd.reference,pd.velocity,d.ctrl[owner.keeper.actuators])
                    return result
            self.experiment_monitor=None;self.engine.mujoco=Probe()
            def run(args):
                pd=ReachPosturePD(self.model,self.keeper,self.rail,'dynamic')
                self.posture=pd;self.engine.body_pd=pd
                # Same source vector as the existing runner; effective plant limits remain authoritative.
                import yaml
                deploy=bootstrap.PROJECT.parent/'RoboNaldo_Deploy'
                caps=effective_caps(self.model,self.keeper,yaml.safe_load((deploy/'deploy_mujoco/config/mujoco_freekick.yaml').read_text())['tau_limit'])
                self.experiment_monitor=MotorMonitor(self.model,self.keeper,self.rail,caps)
                try:return original_run(args)
                finally:
                    Path(args.output).parent.joinpath('experimental_motors.json').write_text(json.dumps(self.experiment_monitor.summary()),encoding='utf-8')
                    self.experiment_monitor=None
            self.engine.run=run
    return Runtime,Selector
