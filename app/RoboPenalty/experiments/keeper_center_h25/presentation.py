from experiments.lateral_keeper_h2.presentation import ManeuverPresenter
import numpy as np


class CenterPresenter(ManeuverPresenter):
    record_phases=False

    def __init__(self,*args,**kwargs):
        self.previous_phase=None
        super().__init__(*args,**kwargs)

    def select_camera(self,name):
        if name!='keeper':return super().select_camera(name)
        self.view=name;self.camera=dict(lookat=[4.45,0.,.60],distance=3.9,azimuth=165.,elevation=-13.)
        self.camera_events.append(dict(view=name,time_sim_s=float(self.runtime.data.time)))
        self.apply_camera()

    def overlay(self):
        s=self.status
        self.handle.set_texts((self.mj.mjtFontScale.mjFONTSCALE_100,self.mj.mjtGridPos.mjGRID_TOPLEFT,
            'HITO 2.5 CENTRO DEL ARCO\nFase\nLado\nTiempo\nPelota',
            f'PRUEBA MANUAL\n{s.get("phase","BALANCE")}\n{s.get("side","-")}\n{self.runtime.data.time:.2f}s\nSIN ORDEN DE TIRO'))

    def set_status(self,status):
        phase=status.get('phase')
        if self.record_phases and self.previous_phase is not None and phase!=self.previous_phase:
            self.capture_keeper('end_'+self.previous_phase)
        self.previous_phase=phase
        super().set_status(status)

    def capture_keeper(self,label):
        from presentation import png_write
        before=self.runtime.integration_state(self.runtime.data)
        with self.mj.Renderer(self.runtime.model,height=640,width=960) as renderer:
            cam=self.mj.MjvCamera();self.mj.mjv_defaultCamera(cam)
            cam.lookat[:]=[4.45,0.,.60];cam.distance=3.9;cam.azimuth=165.;cam.elevation=-13.
            renderer.update_scene(self.runtime.data,camera=cam)
            self.visual_scene.populate(renderer.scene,replace=False)
            # Include actual state/time: inherited H2 capture times may map to a different fast phase.
            png_write(self.output/f'{self.runtime.data.time:06.3f}_{label}_{self.previous_phase}.png',renderer.render())
        if not np.array_equal(before,self.runtime.integration_state(self.runtime.data)):
            raise RuntimeError('Capture changed state')
