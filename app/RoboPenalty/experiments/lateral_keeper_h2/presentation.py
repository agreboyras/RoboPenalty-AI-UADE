from experiments.free_keeper_stadium_h1.presentation import FreeKeeperPresenter


class ManeuverPresenter(FreeKeeperPresenter):
    def select_camera(self,name):
        if name!='keeper':return super().select_camera(name)
        self.view=name
        self.camera=dict(lookat=[4.2,4.,.65],distance=3.8,azimuth=165.,elevation=-12.)
        self.camera_events.append(dict(view=name,time_sim_s=float(self.runtime.data.time)))
        self.apply_camera()

    def overlay(self):
        s=self.status
        self.handle.set_texts((self.mj.mjtFontScale.mjFONTSCALE_100,self.mj.mjtGridPos.mjGRID_TOPLEFT,
            'HITO 2 LABORATORIO\nControl\nFase\nLado\nTiempo simulado',
            f'SIN AGENTE NI ATAJADA\n{s.get("owner","policy")}\n{s.get("phase","BALANCE")}\n{s.get("side","-")}\n{self.runtime.data.time:.2f}s'))

    def capture_keeper(self,label):
        from presentation import png_write
        with self.mj.Renderer(self.runtime.model,height=640,width=960) as renderer:
            cam=self.mj.MjvCamera();self.mj.mjv_defaultCamera(cam)
            cam.lookat[:]=[4.2,4.,.65];cam.distance=3.8;cam.azimuth=165.;cam.elevation=-12.
            renderer.update_scene(self.runtime.data,camera=cam)
            self.visual_scene.populate(renderer.scene,replace=False)
            png_write(self.output/f'{label}.png',renderer.render())
