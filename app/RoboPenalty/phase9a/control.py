from dataclasses import replace
import time
from control import Control as PreviousControl
from phase9a.commands import LABELS
from phase9a.language import COMMAND_MODEL

HELP=('Iniciar partido; modo dirigido/automatico; patea al centro/a la izquierda/a la derecha/'
      'a la derecha abierta/a la esquina derecha; /voz (o Enter) con --voice; '
      'estado; mostrar marcador; pausar partida; reanudar partida; salir. '
      'Izquierda = centro-izquierda. La llegada depende de la fisica.')

class Control(PreviousControl):
    shot_labels = LABELS
    shot_prompt = 'Izquierda disponible: centro-izquierda'
    help_text = HELP
    def __init__(self,bus,mode='directed',emit=print):
        super().__init__(bus,False,emit);self.mode=mode;self.awaiting_shot=False;self.pending_shot=None;self.voice=None
        self.text_input=None
    def open_selection(self):
        self.assert_owner();self.awaiting_shot=True;self.pending_shot=None;self.cancel_input()
        return self.bus.open_window()
    def close_selection(self):
        self.assert_owner();self.awaiting_shot=False;self.bus.close_window()
        self.cancel_input()
    def cancel_input(self):
        if self.voice:self.voice.cancel_request()
        if self.text_input:self.text_input.cancel_request()
    def can_select_shot(self):
        return (self.mode=='directed' and self.awaiting_shot and self.phase=='PREPARING'
                and not self.paused and self.pending_shot is None)
    def should_interpret_text(self,message):
        return (self.text_input is not None and message.source=='text' and message.kind=='command'
                and self.can_select_shot() and message.ticket==self.bus.active_ticket()
                and message.text.strip() and (message.intent is None or message.intent.startswith('shot:')))
    def current_voice(self,message):
        return (self.voice and self.awaiting_shot and not self.paused
                and message.ticket==self.bus.active_ticket()
                and self.voice.is_current(message.capture_id))
    def process(self,message):
        self.assert_owner()
        intent=message.intent
        if message.source=='voice':
            if not self.current_voice(message):return False,'Orden de voz vencida; repetila para el penal actual'
            if intent=='listen':return False,'Usá /voz en la consola para volver a grabar'
        if intent is None and (message.source=='voice' or message.kind=='interpreted_text'):
            options=', '.join(self.shot_labels.values())
            return False,f'Necesito una aclaración. Elegí un solo destino: {options}. Escribí otro tiro o usá /voz.'
        if intent=='help':return True,self.help_text
        if intent=='state':return True,f'Modo {self.mode.upper()} | estado {self.phase} | penal {self.penalty} | esperando tiro={self.awaiting_shot} | {self.score}'
        if intent and intent.startswith('mode:'):
            mode=intent.split(':',1)[1]
            safe=self.phase in ('READY','FINISHED') or (self.phase=='PREPARING' and self.awaiting_shot)
            if not safe or self.pending_shot or self.paused:return False,'Modo solo entre penales o esperando seleccion, sin pausa ni tiro elegido'
            if self.mode!=mode:self.close_selection();self.mode=mode
            return True,f'Modo {mode.upper()}; arquero autonomo'
        if intent=='listen':
            if not self.awaiting_shot or self.mode!='directed' or self.paused:return False,'Microfono solo mientras se espera una orden dirigida'
            if not self.voice:return False,'Voz no habilitada; use --voice o continue por texto'
            if self.text_input and self.text_input.pending is not None:
                return False,'Esperá el resultado de la orden escrita'
            return self.voice.request(self.bus.active_ticket())
        if intent=='unsupported:left_corner':return False,'No hay esquina izquierda validada en 8C. Izquierda disponible: centro-izquierda; repita una orden valida'
        if intent=='unsupported:left_open':
            return False,'El tiro abierto izquierdo está disponible en la exhibición. Ejecutá jugar_dirigido.ps1 -ArqueroLibre -Voz, o elegí centro-izquierda en esta tanda.'
        if intent and intent.startswith('shot:'):
            if not self.can_select_shot():
                return False,'Tiro permitido solo al esperar seleccion en modo dirigido; no se guarda para otro penal'
            if getattr(message,'ticket',None)!=self.bus.active_ticket():return False,'Orden antigua o recibida fuera de esta ventana; repita'
            action=intent.split(':',1)[1]
            if action not in self.shot_labels:return False,'Accion fuera del catalogo 8C'
            self.pending_shot=dict(action=action,text=message.text,source=message.source,ticket=message.ticket)
            if message.capture_id is not None:self.pending_shot['capture_id']=message.capture_id
            self.close_selection()
            return True,f'Accion seleccionada: {self.shot_labels[action]}. Arquero autonomo. La trayectoria depende del contacto fisico'
        accepted,reason=super().handle(intent)
        if intent in ('stop','reset') and accepted:self.close_selection()
        if intent=='pause' and accepted:self.cancel_input()
        return accepted,reason
    def pump(self):
        self.assert_owner()
        while True:
            m=self.bus.drain()
            interpretation_error=None
            if m is None:
                result=self.text_input.poll() if self.text_input else None
                if result is None:break
                original,intent,interpretation_error=result
                if not self.can_select_shot() or original.ticket!=self.bus.active_ticket():continue
                m=replace(original,intent=intent,kind='interpreted_text')
            if m.generation!=self.bus.epoch():continue
            if m.kind=='typing':
                if self.voice and self.can_select_shot() and m.ticket==self.bus.active_ticket():
                    self.voice.cancel_request()
                continue
            if m.kind=='status':
                if m.source=='voice' and not self.current_voice(m):continue
                self.emit(f'[microfono] {m.text}',flush=True);self.events.append(dict(kind='status',text=m.text));continue
            before=dict(phase=self.phase,penalty=self.penalty,mode=self.mode,awaiting_shot=self.awaiting_shot)
            if self.should_interpret_text(m):
                if self.text_input.request(m):
                    if self.voice:self.voice.cancel_request()
                    self.emit(f'[texto] Interpretando {m.text!r} con {COMMAND_MODEL}.',flush=True)
                    continue
                accepted,reason=False,'Esperá el resultado de la orden escrita anterior'
            elif interpretation_error and m.intent is None:
                accepted,reason=False,f'{interpretation_error}. Probá con un comando de tiro exacto.'
            else:
                accepted,reason=self.process(m)
                if interpretation_error:
                    reason=f'{interpretation_error}. Parser local: {reason}'
            event=dict(kind='command',text=m.text,intent=m.intent,source=m.source,capture_id=m.capture_id,
                ticket=getattr(m,'ticket',None),accepted=accepted,reason=reason,state_before=before,
                phase=self.phase,penalty=self.penalty,mode=self.mode,paused=self.paused,
                queue_age_s=time.perf_counter()-m.created,score=dict(self.score),generation=m.generation)
            if m.kind=='interpreted_text':
                event.update(command_model=COMMAND_MODEL,interpretation_error=interpretation_error)
            self.events.append(event)
            self.emit(f'[{m.source}] {m.text!r} -> {m.intent or "desconocido"} | {"ACEPTADO" if accepted else "RECHAZADO"}: {reason}',flush=True)
    def reset(self):
        self.close_selection();self.pending_shot=None;super().reset()
