"""Local Unix-socket client for the persistent live supervisor. Never SSH."""
from dataclasses import asdict
import fcntl
import json
from pathlib import Path
import socket
import subprocess
import time


class TargetAdapter:
    def __init__(self,root):
        self.root=Path(root);self.socket=self.root/'generated/live_supervisor.sock';self.collector=None

    def _native(self):
        if not Path('/TICI').exists():raise RuntimeError('Live target supervision is available only on the comma')

    def _call(self,command,**payload):
        self._native()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(5);client.connect(str(self.socket));client.sendall((json.dumps({'command':command,**payload})+'\n').encode())
            data=b''
            while b'\n' not in data:
                part=client.recv(65536)
                if not part:raise RuntimeError('Live supervisor closed without a response')
                data+=part
                if len(data)>1024*1024:raise RuntimeError('Oversized live supervisor response')
        result=json.loads(data.split(b'\n',1)[0])
        if result.get('error'):raise RuntimeError(result['error'])
        return result

    def _ensure(self):
        self._native();self.socket.parent.mkdir(parents=True,exist_ok=True)
        with (self.socket.parent/'live_launch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            try:self._call('status');return
            except (OSError,RuntimeError):pass
            log=self.root/'results/live_supervisor.log';log.parent.mkdir(parents=True,exist_ok=True)
            with log.open('ab') as stream:
                child=subprocess.Popen(['/usr/local/venv/bin/python',str(self.root/'prototype/live_target_daemon.py'),'--root',str(self.root)],stdout=stream,stderr=stream,stdin=subprocess.DEVNULL,start_new_session=True)
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                if child.poll() is not None:raise RuntimeError('Live supervisor failed to start; inspect live_supervisor.log')
                try:self._call('status');return
                except OSError:time.sleep(.05)
            raise RuntimeError('Live supervisor startup timed out')

    def status(self):
        if not Path('/TICI').exists():return dict(available=False,enabled=False,state='COLD',can_enable=False,reason='Live target is unavailable on this host')
        try:return self._call('status')
        except (FileNotFoundError,ConnectionRefusedError):return dict(available=True,enabled=False,state='COLD',reason='Live supervisor is stopped')

    def health_and_authorization(self):
        self._native()
        try:
            result=self._call('health')
            from live_supervisor import Observation,Authorization
            return Observation(**result['observation']),Authorization(**result['authorization'])
        except (FileNotFoundError,ConnectionRefusedError):
            from live_health import LiveHealth
            if self.collector is None:self.collector=LiveHealth(self.root)
            return self.collector.collect()

    def enable(self,observation=None,authorization=None):
        self._ensure();return self._call('enable')

    def prepare_diagnostic(self):
        self._ensure();return self._call('diagnostic')

    def confirm_driver_ready(self,session_id,*,audible=False):
        return self._call('driver_ready',session_id=session_id,audible=audible)

    def stop_owned(self):
        # No daemon spawn for OFF. The service prioritizes the stop signal.
        if not Path('/TICI').exists():return self.status()
        try:return self._call('stop')
        except (FileNotFoundError,ConnectionRefusedError):return self.status()


def create(root):return TargetAdapter(root)
