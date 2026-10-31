"""Private live 4A viewer, reusing 7D and the original physical experiments."""
from . import bootstrap
import argparse,json,time,uuid
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import mujoco
from phase6a.presentation import PresentationConfig,ViewerClosed
from phase7d.presentation import MonumentalPresenter
from .run_trial import no_ball
from .runtime import components

VIEWS=('keeper','behind','execution','overview','goal','follow')


def camera_for(case,requested=None):
    return requested or ('keeper' if case=='no-ball' else 'behind')


class LivePresenter(MonumentalPresenter):
    """Only display state changes; original 7D pacing/guards/close remain intact."""
    last_body_state=None
    def after_step(self):
        body=getattr(self.runtime,'posture',None)
        state=getattr(body,'state','WAIT')
        if state!=self.last_body_state:
            self.last_body_state=state
            print(f'[cuerpo] {state} | sim {self.runtime.data.time:.3f}s',flush=True)
            self.set_status({**self.status,'phase':state})
        super().after_step()


def open_presenter(runtime,out,view,*,laboratory=False):
    p=LivePresenter(runtime,PresentationConfig(True,30.,True,1.,0.,0.,2.,False),out,'long',camera='behind' if view=='keeper' else view,
                    lod='none' if laboratory else 'medium')
    if view=='keeper':
        p.camera=dict(lookat=[4.2,0,.85],distance=2.35,azimuth=10.,elevation=-8.)
        p.view='keeper';p.apply_camera()
    p.set_status(dict(penalty=1,total=1,phase='READY',goals=0,saves=0,misses=0))
    p.sync('transition')
    return p


class NoBallObserver:
    presenter=None
    def __init__(self,out,view):self.out,self.view=out,view
    def bind(self,model,data,keeper,rail,posture):
        class World:
            def integration_state(_,d):
                spec=mujoco.mjtState.mjSTATE_INTEGRATION
                state=np.empty(mujoco.mj_stateSize(model,spec));mujoco.mj_getState(model,d,state,spec)
                return state
        runtime=World();runtime.model=model;runtime.data=data;runtime.rail=rail;runtime.posture=posture
        runtime.engine=SimpleNamespace(mujoco=mujoco,np=np)
        self.presenter=open_presenter(runtime,self.out,self.view,laboratory=True)
        self.presenter.pause('ready',1.);self.presenter.begin_episode()
    def after_step(self):self.presenter.after_step()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',choices=('no-ball','nominal'),default='no-ball')
    p.add_argument('--experimental',action='store_true');p.add_argument('--side',choices=('LEFT','RIGHT'),default='LEFT')
    p.add_argument('--action',default='right_inter_m080');p.add_argument('--camera',choices=VIEWS)
    p.add_argument('--output',type=Path)
    a=p.parse_args();view=camera_for(a.case,a.camera)
    out=(a.output or bootstrap.PROJECT/'experiments/keeper_saves/results'/('live_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])).resolve()
    if out.exists() or not out.is_relative_to(bootstrap.PROJECT):p.error('Choose a NEW output directory inside this RoboPenalty copy')
    out.mkdir(parents=True);presenter=None;observer=None;termination='completed';failure=None;physical_completed=False
    print(f'4A EN VIVO | {a.case} | {"EXPERIMENTAL" if a.experimental else "ESTABLE"} | camara {view}',flush=True)
    print('Cerrar con X o Ctrl+C. Objetivo 1x; no se omiten pasos fisicos. Salida: '+str(out),flush=True)
    try:
        if a.case=='no-ball':
            print(f'0..2 s: guardia; 2..5 s: {a.side if a.experimental else "guardia estable"}; 5..10 s: recuperacion.',flush=True)
            observer=NoBallObserver(out,view)
            result=no_ball(a.experimental,a.side,out/'no_ball.json',observer=observer)
            presenter=observer.presenter
            if not result['passed']:raise RuntimeError('Physical laboratory checks failed')
        else:
            from phase8c.catalog import Catalog
            catalog=Catalog(bootstrap.PROJECT/'phase8c/catalog_v1.json')
            if a.action not in catalog.actions:raise ValueError('Action not in unchanged 8C catalog')
            Runtime,_=components(catalog,experimental=a.experimental);runtime=Runtime()
            presenter=open_presenter(runtime,out,view);runtime.attach(presenter)
            result,selection,wall=runtime.execute('long','agent',out/'physical.json',lambda observation:a.action,lambda:None)
            label,error=runtime.evaluate(result,'long',a.action)
            presenter.set_status(dict(penalty=1,total=1,phase='FINISHED',goals=int(label=='goal'),saves=int(label=='save'),
                                      misses=int(label=='miss'),action=a.action,last_result=label))
            (out/'trial_outcome.json').write_text(json.dumps(dict(outcome=label,error=error,experimental=a.experimental,wall_s=wall)))
            print('Resultado fisico:',label,flush=True)
        physical_completed=True
        presenter.pause('finished',2.)
    except (ViewerClosed,KeyboardInterrupt) as exc:
        termination='viewer_closed' if isinstance(exc,ViewerClosed) else 'keyboard_interrupt'
        if physical_completed:
            termination='completed_'+termination
            print('Prueba fisica completada; visualizacion cerrada.',flush=True)
        else:print('Ensayo interrumpido; no se declara completado.',flush=True)
    except Exception as exc:
        failure=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        presenter=presenter or (observer.presenter if observer else None)
        if presenter:presenter.close()
        summary=dict(termination=termination,failure=failure,case=a.case,experimental=a.experimental,camera=view,
                     presentation=presenter.summary() if presenter else None)
        (out/'live.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print('Visor cerrado.',flush=True)


if __name__=='__main__':main()
