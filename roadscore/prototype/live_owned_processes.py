"""Direct ACE/live-app child ownership; never uses benchmark power supervision."""
import fcntl
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import time
import threading


def read(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return {}


class OwnedLiveProcesses:
    def __init__(self, root, *, popen=subprocess.Popen, clock=time.monotonic):
        self.root=Path(root);self.popen=popen;self.clock=clock
        self.worker=None;self.app=None;self.lease=None;self.logs=[];self.session_id=None
        self.env=None;self.folder=None;self.seed=None;self.started=None;self.stop_requested=threading.Event();self.cancel_check=lambda:False

    def prepare(self, session_id, *, diagnostic=False):
        if self.worker is not None:raise RuntimeError('An owned worker already exists; stop it first')
        if self.cancel_check():raise RuntimeError('Live start canceled by operator stop')
        self.stop_requested.clear()
        generated=self.root/'generated';generated.mkdir(parents=True,exist_ok=True)
        self.lease=(generated/'native_session.lock').open('a')
        try:
            fcntl.flock(self.lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            # Refuse external GPU owner before touching shared preparation outputs.
            with (generated/'gpu.lock').open('a') as check:
                fcntl.flock(check,fcntl.LOCK_EX|fcntl.LOCK_NB)
            config=read(generated/'live_config.json')
            profile=config.get('profile','prism')
            if profile not in ('prism','aurora'):raise ValueError('Unsupported live profile')
            bank=Path(config.get('plan_bank','/data/roadscore-event-assets/conditioning/current'))
            from cached_composition import validate_bank,digest
            validate_bank(bank,profile=profile)
            self.bank_hash=digest(bank/'bank.json')
            runtime=read(self.root/'runtime.json')
            if runtime.get('identity')!='kpop_control':raise RuntimeError('Current ACE runtime configuration is unavailable')
            self.seed=secrets.randbits(32);self.session_id=session_id
            self.folder=self.root/'results'/'live'/session_id;self.folder.mkdir(parents=True,exist_ok=False)
            env=os.environ.copy()
            for key in ('OPENPILOT_PREFIX','PARAMS_ROOT','ZMQ','OPENPILOT_ZMQ_NAMESPACE','SIMULATION','NOBOARD','SKIP_FW_QUERY','ROADSCORE_PCM_RETURN','ROADSCORE_ORIGIN_FILE','ROADSCORE_REPLAY_PRIME','ROADSCORE_NATIVE_CUE_CLOCK','ROADSCORE_TEST_SHORT_STARTUP','AM_POWER_LIMIT'):
                env.pop(key,None)
            env.update(ROADSCORE_COMPOSER='ace',ROADSCORE_ACE_PROFILE=profile,ROADSCORE_COMPOSITION_POLICY='hook-cache-v1',
                       ROADSCORE_PLAN_BANK=str(bank),ROADSCORE_GENERATION_SEED=str(self.seed),ROADSCORE_SEED_ORIGIN='live-session',
                       ROADSCORE_RESIDENT='1',ROADSCORE_FORCE_MUTE='1',ROADSCORE_RENDER_MODE='gold-core',
                       ROADSCORE_PRESENTATION_POLICY='conservative-v3',ROADSCORE_INITIAL_BUFFER_SECONDS=str(config.get('initial_buffer_seconds',100)),
                       ROADSCORE_WORKER=str(self.root/'experiments/ace_chestnut_20260916/ace_worker.py'),TC_OPT='2')
            from startup_buffer import initial_target
            initial_target(env,'hook-cache-v1')
            cap=config.get('power_limit_watts')
            if cap is not None:
                import math
                if type(cap) not in (int,float) or not math.isfinite(cap) or cap<=0:raise ValueError('Invalid explicit live power cap')
                env['AM_POWER_LIMIT']=str(cap)
            self.env=env;self.started=self.clock();self.diagnostic=diagnostic
            (self.folder/'session.json').write_text(json.dumps({'session_id':session_id,'generation_seed':self.seed,'profile':profile,'bank_sha256':self.bank_hash,'diagnostic':diagnostic,'power_limit_watts':cap,'created_wall':time.time()},indent=2))
            log=(self.folder/'worker.log').open('ab');self.logs.append(log)
            if self.stop_requested.is_set() or self.cancel_check():raise RuntimeError('Stop requested during preparation launch')
            self.worker=self.popen(['bash',str(self.root/'prototype/run_worker.sh')],cwd=self.root,env=env,stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)
            if self.stop_requested.is_set() or self.cancel_check():raise RuntimeError('Stop requested while launching worker')
        except Exception:
            self.stop_owned();raise

    def accepted_ready(self):
        if self.worker is None or self.worker.poll() is not None:return False
        meta=read(self.root/'generated/ace_initial.json');state=read(self.root/'generated/ace_worker_state.json')
        return bool((self.root/'generated/worker_ready').exists() and state.get('pid')==self.worker.pid and state.get('phase')=='READY'
                    and meta.get('generation_seed')==self.seed and meta.get('prepared_profile')==self.env['ROADSCORE_ACE_PROFILE']
                    and meta.get('composition_policy')=='hook-cache-v1' and meta.get('conditioning_bank_sha256')==self.bank_hash
                    and meta.get('duration',0)>=float(self.env['ROADSCORE_INITIAL_BUFFER_SECONDS']))

    def start_app(self, session_id, *, audible=False):
        if session_id!=self.session_id or self.diagnostic or not self.accepted_ready():raise RuntimeError('No matching accepted live session')
        if self.app is not None:raise RuntimeError('Live app already started')
        # Preserve previous evidence, never delete an active archive.
        current=self.root/'results/current'
        if current.exists():current.rename(self.folder/'previous_current')
        current.mkdir()
        env=self.env.copy();env['ROADSCORE_FORCE_MUTE']='0' if audible else '1'
        env['PYTHONPATH']=':'.join(['/data/openpilot',str(self.root/'prototype'),'/data/roadscore-feasibility/venv/lib/python3.12/site-packages'])
        env['ROADSCORE_LIVE_SESSION_ID']=session_id
        log=(self.folder/'app.log').open('ab');self.logs.append(log)
        self.app=self.popen(['/usr/local/venv/bin/python','-u',str(self.root/'prototype/app.py'),'--root',str(self.root),'--input','live']+(['--audible'] if audible else []),cwd='/data/openpilot',env=env,stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)

    def health(self):
        return dict(worker_healthy=self.worker is not None and self.worker.poll() is None,
                    accepted_ready=self.accepted_ready(),app_healthy=self.app is None or self.app.poll() is None,
                    app_ready=self.app is not None and self.app.poll() is None and (self.root/'results/current/ready').exists())

    def signal_stop(self):
        self.stop_requested.set()
        # Handles belong to this object only; never pgrep/killall or inherited PIDs.
        for process in (self.app,self.worker):
            if process is not None and process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass

    def stop_owned(self):
        if self.folder is not None:
            (self.folder/'stop.json').write_text(json.dumps({'requested_wall':time.time(),'session_id':self.session_id,'diagnostic':getattr(self,'diagnostic',False)}))
        self.signal_stop()
        deadline=self.clock()+3
        for process in (self.app,self.worker):
            if process is not None:
                try:process.wait(timeout=max(.01,deadline-self.clock()))
                except subprocess.TimeoutExpired:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait(timeout=2)
        self.app=None;self.worker=None
        for log in self.logs:log.close()
        self.logs=[]
        if self.lease is not None:self.lease.close();self.lease=None
