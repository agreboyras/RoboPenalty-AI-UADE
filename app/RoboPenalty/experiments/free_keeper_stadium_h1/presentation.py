"""Private overlay only: the unchanged 7D stadium draws the same physical world."""
from . import bootstrap
from phase7d.presentation import MonumentalPresenter


class FreeKeeperPresenter(MonumentalPresenter):
    def overlay(self):
        s=self.status;d=self.runtime.data
        left='HITO 1 EXPERIMENTAL\nEstado\nTiro\nResultado\nTiempo simulado\nArquero'
        right=f'BASE LIBRE\n{s.get("phase","READY")}\n{s.get("action","-")}\n{s.get("last_result","-")}\n{d.time:.2f} s\nLOCOMOCION CERO: SIN ATAJADA'
        self.handle.set_texts((self.mj.mjtFontScale.mjFONTSCALE_100,
            self.mj.mjtGridPos.mjGRID_TOPLEFT,left,right))
