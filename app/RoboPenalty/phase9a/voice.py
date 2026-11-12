"""Explicit one-shot jobs; audio/ASR thread sees a ticket, never MuJoCo or agents."""
import json
from pathlib import Path
import queue
import threading
import time
from audio import capture,resolve_input
from phase9a.commands import interpret,normalize
from phase9a.language import COMMAND_MODEL, resolve_shot
from phase9a.whisper_api import DEFAULT_TRANSCRIPTION_MODEL, VoiceError, WhisperAPI

class VoiceInput:
    def __init__(self,bus,config,output=None,*,capture_fn=capture,model_factory=None,
                 backend='openai',transcription_model=DEFAULT_TRANSCRIPTION_MODEL,recognizer=None):
        self.bus,self.config,self.output=bus,config,Path(output) if output else None
        self.capture_fn,self.model_factory=capture_fn,model_factory
        self.backend=backend
        self.recognizer=(recognizer or WhisperAPI(transcription_model)) if backend=='openai' else None
        self.jobs=queue.Queue(1);self.stop=threading.Event();self.cancel=threading.Event();self.capture_closed=threading.Event();self.capture_closed.set()
        self.lock=threading.Lock();self.busy=False;self.metrics=[];self.model=None
        self.capture_counter=0;self.active_capture=None
        self.thread=threading.Thread(target=self.run,name='phase9a-voice',daemon=False)

    def status(self,text,job):
        if self.valid(job):
            self.bus.submit_voice(text,None,*job,kind='status')

    def request(self,ticket):
        if ticket is None:return False,'No se espera una orden de tiro'
        with self.lock:
            if self.stop.is_set():return False,'Voz cerrada'
            if self.busy:return False,'Microfono/ASR ocupado; puede usar texto'
            self.capture_counter+=1
            self.active_capture=str(self.capture_counter)
            self.busy=True;self.cancel.clear();self.capture_closed.clear()
            self.jobs.put_nowait((self.bus.epoch(),ticket,self.active_capture))
        return True,'Captura solicitada; espere ESCUCHANDO'

    def cancel_request(self):
        with self.lock:
            self.active_capture=None
            self.cancel.set()

    def is_current(self,capture_id):
        with self.lock:
            return capture_id is not None and capture_id==self.active_capture

    def start(self):self.thread.start()

    def valid(self,job):
        generation,ticket,capture_id=job
        return (not self.stop.is_set() and self.is_current(capture_id)
                and self.bus.epoch()==generation and self.bus.active_ticket()==ticket)

    def prepare(self,job):
        if self.recognizer:
            self.recognizer.prepare()
        elif self.model is None:
            if not Path(self.config.model).is_dir():
                raise VoiceError('Modelo Whisper local no disponible')
            self.status('Cargando Whisper local CPU/int8; micrófono cerrado',job)
            factory=self.model_factory
            if factory is None:
                from faster_whisper import WhisperModel
                factory=WhisperModel
            self.model=factory(self.config.model,device='cpu',compute_type='int8',cpu_threads=self.config.cpu_threads,num_workers=1,local_files_only=True)

    def process_capture(self,job,record):
        record['stage']='cancelled_before_capture'
        if not self.valid(job):return
        self.prepare(job)
        expected=resolve_input(self.config) if self.capture_fn is capture else None
        if not self.valid(job):return

        metadata={}
        start=time.perf_counter()
        try:
            samples,rms=self.capture_fn(
                self.config,self.cancel,metadata=metadata,expected_device=expected,
                on_ready=lambda:self.status('ESCUCHANDO: decí una sola orden de tiro',job),
            )
        finally:
            self.capture_closed.set()
        record.update(metadata,capture_wall_s=time.perf_counter()-start,rms=rms,samples=len(samples))
        if not self.valid(job):
            record.update(stage='cancelled_after_capture',cancelled=True)
            return
        if not len(samples) or rms<=self.config.min_rms:
            record['stage']='below_rms_threshold'
            self.status('No oí una orden. Escribí /voz para volver a grabar o elegí el tiro por texto.',job)
            return

        self.status('TRANSCRIBIENDO. Micrófono cerrado.',job)
        start=time.perf_counter()
        if self.recognizer:
            text=self.recognizer.transcribe(samples)
        else:
            segments,info=self.model.transcribe(samples,language='es',task='transcribe',beam_size=1,vad_filter=True,condition_on_previous_text=False)
            text=' '.join(s.text.strip() for s in segments).strip()
            record['duration_after_vad_s']=getattr(info,'duration_after_vad',None)
        record.update(text=text,normalized=normalize(text),asr_wall_s=time.perf_counter()-start)
        if not self.valid(job):
            record.update(stage='cancelled_after_asr',cancelled_after_asr=True)
            return
        if not text:
            record['stage']='empty_transcription'
            self.status('No oí una orden. Escribí /voz para volver a grabar o elegí el tiro por texto.',job)
            return

        intent=interpret(text,exhibition=self.bus.exhibition)
        if intent is None and self.recognizer:
            self.status(f'Oí {text!r}. Interpretando la orden con {COMMAND_MODEL}.',job)
            record['command_model']=COMMAND_MODEL
            start=time.perf_counter()
            intent=resolve_shot(self.recognizer.client,text,exhibition=self.bus.exhibition)
            record['interpretation_wall_s']=time.perf_counter()-start
        record['intent']=intent
        submitted=self.valid(job) and self.bus.submit_voice(text,intent,*job)
        record['stage']='decoded' if submitted else 'discarded'

    def run(self):
        while not self.stop.is_set():
            try:job=self.jobs.get(timeout=.1)
            except queue.Empty:continue
            generation,ticket,capture_id=job
            record=dict(generation=generation,ticket=ticket,capture_id=capture_id,backend=self.backend,
                        model=self.recognizer.model if self.recognizer else self.config.model,
                        source='real_microphone' if self.capture_fn is capture else 'test_double',text='',intent=None)
            try:
                self.process_capture(job,record)
            except Exception as exc:
                reason=str(exc) if isinstance(exc,(VoiceError,ValueError,ImportError)) else type(exc).__name__
                record.update(stage='error',error=type(exc).__name__,message=reason)
                self.status(f'ERROR VOZ: {reason}. Podés elegir el tiro por texto.',job)
            finally:
                self.capture_closed.set();self.metrics.append(record)
                try:
                    if self.output:
                        self.output.mkdir(parents=True,exist_ok=True)
                        (self.output/'voice_metrics.json').write_text(json.dumps(self.metrics,indent=2),encoding='utf-8')
                except OSError:
                    self.status('No se pudo guardar el informe de voz.',job)
                finally:
                    with self.lock:self.busy=False
    def close(self):
        self.stop.set();self.cancel_request()
        if self.thread.ident:self.thread.join(timeout=10.)
        joined=not self.thread.is_alive()
        if joined:
            self.capture_closed.set();self.model=None
            if self.recognizer:self.recognizer.close()
        return joined
