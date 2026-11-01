"""Bounded RPC to the existing private Torch environment; no motor writes."""
import json
from pathlib import Path
import queue
import subprocess
import threading
import time


class PolicyClient:
    def __init__(self, python, deploy, output, cwd):
        self.log=(Path(output)/'policy_stderr.log').open('w',encoding='utf-8')
        self.process=subprocess.Popen([str(python),'-X','utf8','-u','-B','-m',
            'experiments.free_keeper_stadium_h1.policy_worker','--deploy',str(deploy)],
            cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,
            text=True,encoding='utf-8',bufsize=1)
        self.messages=queue.Queue(); self.seq=0; self.closed=False; self.latencies=[]
        def read():
            try:
                for line in self.process.stdout: self.messages.put(line)
            finally: self.messages.put(None)
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
        try:self.metadata=self.receive(60.)
        except BaseException:self.close(force=True);raise

    def receive(self,timeout=10.):
        try:line=self.messages.get(timeout=timeout)
        except queue.Empty:raise TimeoutError('Locomotion inference timed out; physics will not advance')
        if line is None:raise RuntimeError('Locomotion process exited; see policy_stderr.log')
        return json.loads(line)

    def request(self,op,**values):
        self.seq+=1;start=time.perf_counter()
        self.process.stdin.write(json.dumps(dict(op=op,seq=self.seq,**values),allow_nan=False)+'\n')
        self.process.stdin.flush();answer=self.receive()
        if answer['seq']!=self.seq:raise RuntimeError('Stale inference response')
        self.latencies.append(time.perf_counter()-start)
        return answer

    def close(self,force=False):
        if self.closed:return
        self.closed=True
        try:
            if not force and self.process.poll() is None:
                self.final=self.request('stop')
            self.process.stdin.close()
            self.process.wait(timeout=10.)
        except BaseException:
            self.process.kill();self.process.wait(timeout=5.)
            if not force:raise
        finally:
            self.reader.join(timeout=3.);self.process.stdout.close();self.log.close()
