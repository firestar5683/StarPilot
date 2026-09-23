"""Persistent local live ownership and watchdog; separate from offroad bench service."""
from dataclasses import asdict
import argparse
import fcntl
import json
import os
from pathlib import Path
import queue
import signal
import socketserver
import threading
import time
import uuid
from live_supervisor import LiveSupervisor,blocked_reason
from live_owned_processes import OwnedLiveProcesses


class Engine:
    def __init__(self,root,collector,owned=None,*,clock=time.monotonic):
        self.root=Path(root);self.collector=collector;self.owned=owned or OwnedLiveProcesses(root)
        self.clock=clock;self.auto_play=False;self.diagnostic=False;self.audible=False;self.stop_event=threading.Event();self.commands=queue.Queue()
        self.owned.cancel_check=self.stop_event.is_set
        self.supervisor=LiveSupervisor(self._prepare,self._app,self.owned.stop_owned,clock=clock)
        self.observation=None;self.authorization=None;self.health_error='No live observations yet';self.started=None;self.last_recorded=0.;self.diagnostic_ready_at=None

    def _prepare(self,session_id):self.started=self.clock();self.owned.prepare(session_id,diagnostic=self.diagnostic)
    def _app(self,session_id):self.owned.start_app(session_id,audible=self.audible)

    def request_stop(self):
        self.stop_event.set();self.owned.signal_stop()

    def refresh(self):
        try:self.observation,self.authorization=self.collector.collect();self.health_error=''
        except Exception as error:self.observation=None;self.authorization=None;self.health_error=str(error)

    def diagnostic_ok(self):
        snapshot=self.collector.last_snapshot
        return (self.observation is not None and self.observation.parked is True
                and 0<=self.clock()-self.observation.monotonic<=1.
                and self.observation.model_fresh is True and self.observation.car_fresh is True
                and self.observation.driving_model_local is True
                and snapshot.get('diagnostic_healthy') is True)

    def status(self):
        return {**self.supervisor.status(),'available':True,'diagnostic':self.diagnostic,'health_error':self.health_error,
                'parked':bool(self.observation is not None and self.observation.parked and 0<=self.clock()-self.observation.monotonic<=1.),
                'can_prepare_diagnostic':not self.supervisor.enabled and self.diagnostic_ok(),
                'metrics':self.collector.last_snapshot}

    def command(self,payload):
        action=payload.get('command')
        if action=='stop':self.request_stop();return {**self.status(),'state':'STOPPING'}
        if action=='status':return self.status()
        if action=='health':
            if self.observation is None:raise RuntimeError(self.health_error)
            return {'observation':asdict(self.observation),'authorization':asdict(self.authorization)}
        if action not in ('enable','diagnostic','driver_ready'):raise ValueError('Unknown live action')
        if self.stop_event.is_set():raise RuntimeError('Owned live processes are stopping')
        self.refresh()
        if action=='enable' and type(payload.get('auto_play',False)) is not bool:raise ValueError('auto_play must be boolean')
        if action=='driver_ready':
            if type(payload.get('audible',False)) is not bool:raise ValueError('audible must be boolean')
            if self.diagnostic:raise RuntimeError('Diagnostic preparation cannot start playback or authorize driving')
            self.audible=payload.get('audible',False)
            return self.supervisor.confirm_driver_ready(payload.get('session_id'),self.observation,self.authorization)
        if self.supervisor.enabled:
            if action=='enable' and self.diagnostic and self.supervisor.state=='READY':
                reason=blocked_reason(self.observation,self.authorization,self.clock(),require_parked=True)
                if reason:raise RuntimeError(reason)
                self.auto_play=payload.get('auto_play',False);self.audible=self.auto_play
                self.diagnostic=False;self.owned.diagnostic=False;self.supervisor.reason=('Starting prepared music' if self.auto_play else 'Verified live preparation; explicit current driver-ready confirmation required')
                if getattr(self.owned,'folder',None) is not None:
                    (self.owned.folder/'production_authorization.json').write_text(json.dumps({'wall':time.time(),'session_id':self.supervisor.session_id,'authorization':asdict(self.authorization)}))
                return self.status()
            raise RuntimeError('A live session already exists; stop it before changing mode')
        self.diagnostic=action=='diagnostic';self.auto_play=action=='enable' and payload.get('auto_play',False);self.audible=self.auto_play;self.diagnostic_ready_at=None
        if self.diagnostic:
            if not self.diagnostic_ok():raise RuntimeError('Fresh healthy parked diagnostic preflight is required')
            # This authorizes only muted worker preparation, not production capability.
            self.supervisor.session_id=uuid.uuid4().hex;self.supervisor.enabled=True;self.supervisor.driver_ready=False
            self.supervisor.state='PREPARING';self.supervisor.reason='Parked diagnostic: music disabled, driving not authorized'
            try:self._prepare(self.supervisor.session_id)
            except Exception:self.supervisor.stop('Diagnostic preparation failed');raise
            return self.status()
        return self.supervisor.enable(self.observation,self.authorization)

    def tick(self):
        if self.stop_event.is_set():
            self.supervisor.stop()
            while True:
                try:_,reply=self.commands.get_nowait();reply.put({'error':'Canceled by operator stop'})
                except queue.Empty:break
            self.stop_event.clear();self.diagnostic=False
        self.refresh()
        if not self.supervisor.enabled:return
        health=self.owned.health()
        if getattr(self.owned,'folder',None) is not None and self.clock()-self.last_recorded>=1.:
            with (self.owned.folder/'health.jsonl').open('a') as stream:stream.write(json.dumps({'wall':time.time(),'session_id':self.supervisor.session_id,'diagnostic':self.diagnostic,'metrics':self.collector.last_snapshot})+'\n')
            self.last_recorded=self.clock()
        if self.diagnostic:
            if not self.diagnostic_ok() or not health['worker_healthy']:
                self.supervisor.stop('Parked diagnostic health failed');return
            if health['accepted_ready']:
                if self.diagnostic_ready_at is None:self.diagnostic_ready_at=self.clock()
                if self.clock()-self.diagnostic_ready_at>120:
                    self.supervisor.stop('Parked diagnostic observation window completed');return
                self.supervisor.state='READY';self.supervisor.reason='Diagnostic accepted audio ready; music disabled, no driving authorization'
        else:
            if self.supervisor.state=='LIVE' and not health['app_ready']:
                self.supervisor.stop('Live app status is stale or playback has stopped');return
            self.supervisor.tick(self.observation,self.authorization,**health)
            if self.auto_play and self.supervisor.state=='READY' and not self.stop_event.is_set():
                self.supervisor.confirm_driver_ready(self.supervisor.session_id,self.observation,self.authorization)
            if self.supervisor.state=='STARTING' and self.clock()-getattr(self.owned,'app_started',self.clock())>30:
                self.supervisor.stop('Live app failed to establish current input/playback readiness')
        if self.started is not None and self.clock()-self.started>1500 and self.supervisor.state=='PREPARING':
            self.supervisor.stop('Preparation timed out')


def serve(root):
    if not Path('/TICI').exists():raise RuntimeError('Live daemon is target-only')
    from live_health import LiveHealth
    generated=root/'generated';generated.mkdir(parents=True,exist_ok=True)
    with (generated/'live_daemon.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        engine=Engine(root,LiveHealth(root));engine.refresh()
        path=generated/'live_supervisor.sock';path.unlink(missing_ok=True)
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.connection.settimeout(5)
                try:
                    line=self.rfile.readline(65537)
                    if len(line)>65536:raise ValueError('Oversized live request')
                    payload=json.loads(line)
                    if payload.get('command')=='stop':result=engine.command(payload)
                    elif payload.get('command') in ('status','health'):result=engine.command(payload)
                    else:
                        if engine.stop_event.is_set():raise RuntimeError('Owned live processes are stopping')
                        reply=queue.Queue(maxsize=1);engine.commands.put((payload,reply));result=reply.get(timeout=4)
                except Exception as error:result={'error':str(error)}
                self.wfile.write((json.dumps(result)+'\n').encode())
        class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
        server=Server(str(path),Handler);os.chmod(path,0o600)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();quit_event=threading.Event()
        def shutdown(*_):quit_event.set();engine.request_stop()
        signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
        try:
            while not quit_event.is_set():
                engine.tick()
                try:payload,reply=engine.commands.get(timeout=.1)
                except queue.Empty:continue
                try:reply.put(engine.command(payload))
                except Exception as error:reply.put({'error':str(error)})
        finally:
            engine.supervisor.stop('Supervisor exiting');server.shutdown();server.server_close();path.unlink(missing_ok=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('/data/roadscore'));serve(parser.parse_args().root)
