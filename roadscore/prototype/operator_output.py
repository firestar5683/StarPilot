"""Parked, attended output calibration. No models or route data; no import-time audio.

The Galaxy process owns this adapter. Session/operator file leases serialize it
against playback, composer handoff, and official judging. All tests inject sinks.
"""
from collections import deque
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import secrets
from statistics import median
import subprocess
import threading
import time

BPM = 100
INTERVAL = 60 / BPM
COUNT_IN = 8
COUNT = 24
RATE = 48000


def read(path):
  try:
    value = json.loads(Path(path).read_text())
    return value if isinstance(value, dict) else {}
  except (OSError, ValueError):
    return {}


@contextmanager
def lease(path):
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  with Path(path).open('a') as handle:
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
      yield
    finally:
      fcntl.flock(handle, fcntl.LOCK_UN)


def busy(path):
  try:
    with lease(path):
      return False
  except BlockingIOError:
    return True


def real_offroad():
  env=os.environ.copy()
  for key in ('OPENPILOT_PREFIX','PARAMS_ROOT','ZMQ'):env.pop(key,None)
  try:
    code='from openpilot.common.params import Params; p=Params(); print(int(p.get_bool("IsOffroad") and not p.get_bool("IsOnroad")))'
    return subprocess.check_output(['/usr/local/venv/bin/python','-c',code],cwd='/data/openpilot',env=env,text=True,timeout=3).strip()=='1'
  except (OSError,subprocess.SubprocessError):return False


def describe_output(selected,status):
  from bluetooth_output import ADDRESS
  address=selected.get('address','').upper()
  if selected.get('enabled') is not True or not ADDRESS.fullmatch(address):return None
  device=next((d for d in status.get('devices',[]) if d.get('address','').upper()==address),None)
  connected=bool(status.get('enabled') and status.get('powered') and device and device.get('connected') and device.get('audio'))
  return dict(id='bluealsa:'+address,address=address,name=device.get('name',address) if device else address,
              connected=connected,muted=False,bluetooth=True,physical_latency_ms=None)


def selected_output():
  from bluetooth_output import real_selection
  try:
    from openpilot.starpilot.system.bluetooth.protocol import BluetoothClient
    selected=real_selection()
    status=BluetoothClient(timeout=2).status()
    return describe_output(selected,BluetoothClient.serialize_status(status))
  except (OSError,ValueError,ImportError,subprocess.SubprocessError):return None


def playback_process_active(proc=Path('/proc')):
  try:
    for path in proc.iterdir():
      if not path.name.isdigit():continue
      try:cmd=(path/'cmdline').read_bytes().replace(b'\0',b' ')
      except OSError:continue
      if any(name in cmd for name in (b'/prototype/app.py',b'/prototype/stored_score.py')):return True
  except OSError:return True
  return False


def correction(root, identity):
  value = read(Path(root) / 'generated/output_timing.json').get(identity, 0)
  return value if type(value) is int and 0 <= value <= 1500 else 0


def robust_offset(pairs):
  if len(pairs) < 8:
    raise ValueError('At least eight different beats are required')
  differences = [tap - click for click, tap in pairs]
  center = median(differences)
  mad = median(abs(value - center) for value in differences)
  accepted = [value for value in differences if abs(value - center) <= max(35, 4.4478 * mad)]
  if len(accepted) < 8 or len(accepted) < len(pairs) * .65:
    raise ValueError('Tap rhythm was inconsistent; retry')
  spread = median(abs(value - median(accepted)) for value in accepted)
  if spread > 80:
    raise ValueError('Tap timing varied too much; retry')
  raw = round(median(accepted))
  return dict(latency_ms=max(0, min(1500, raw)), raw_offset_ms=raw, accepted_taps=len(accepted),
              rejected_taps=len(pairs) - len(accepted), spread_ms=round(spread), includes_human_tap_bias=True)


class ClickSink:
  """Own a separate local process so each session binds ALSA before PortAudio loads."""
  def __init__(self,on_click,count=COUNT):
    self.on_click=on_click;self.count=count;self.process=None;self.failed=False;self.closed=False
    self.output=selected_output()
    if not self.output or not self.output['connected']:raise ValueError('Selected Bluetooth speaker is disconnected')

  def start(self):
    env=os.environ.copy()
    for key in ('OPENPILOT_PREFIX','PARAMS_ROOT','ZMQ'):env.pop(key,None)
    self.process=subprocess.Popen(['/usr/local/venv/bin/python',str(Path(__file__).with_name('operator_click_process.py')),
                                  '--address',self.output['address'],'--count',str(self.count)],
                                 stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env=env)
    def collect():
      try:
        for line in self.process.stdout:
          value=json.loads(line)
          if value.get('error'):self.failed=True
          if 'beat' in value:self.on_click(value['beat'],value['server_ms'])
        if self.process.wait()!=0 and not self.closed:self.failed=True
      except (OSError,ValueError):self.failed=True
    threading.Thread(target=collect,daemon=True).start()

  def close(self):
    self.closed=True
    if self.process and self.process.poll() is None:
      self.process.terminate()
      try:self.process.wait(timeout=2)
      except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)


class OutputOwner:
  def __init__(self, root, offroad, sink_factory=ClickSink, output_provider=selected_output, clock=time.monotonic):
    self.root, self.offroad, self.sink_factory, self.output_provider, self.clock = Path(root), offroad, sink_factory, output_provider, clock
    self.lock = threading.RLock()
    self.session = None

  def operator_lease(self):
    return lease(self.root / 'generated/operator.lock')

  def safe(self):
    if not self.offroad():
      raise ValueError('Park before changing RoadScore')

  def status(self):
    output = self.output_provider()
    muted = (self.root / '.session-muted').exists() or os.environ.get('ROADSCORE_FORCE_MUTE') == '1'
    active = playback_process_active() or busy(self.root / 'generated/session.lock')
    worker = read(self.root / 'generated/ace_worker_state.json')
    try:
      worker_busy = str(worker.get('phase', '')).upper() in ('PREPARING', 'GENERATING') and b'ace_worker.py' in Path(f"/proc/{int(worker['pid'])}/cmdline").read_bytes()
    except (OSError, KeyError, ValueError):
      worker_busy = False
    active = active or worker_busy
    locked = busy(self.root / 'generated/operator.lock') and self.session is None
    return dict(ok=True, calibrating=self.session is not None, output=output, latency_ms=correction(self.root, output['id']) if output else None,
                judging_locked=locked, playback_active=active and self.session is None,
                calibration=bool(output and output['connected'] and not output['muted'] and not muted),
                timing_compensation=bool(output), session_muted=muted)

  def _close(self):
    session, self.session = self.session, None
    if session:
      try:
        session['sink'].close()
      finally:
        session['session_lease'].__exit__(None, None, None)
        session['operator_lease'].__exit__(None, None, None)

  def _check_session(self, token):
    with self.lock:
      session = self.session
      if session is None or session['token'] != token:
        return False
      output = self.output_provider()
      if (not self.offroad() or self.clock() > session['deadline'] or
          self.clock() - session['last_client'] > 7 or not output or output['id'] != session['output']['id'] or
          output['muted'] or not output['connected'] or playback_process_active() or session['sink'].failed or
          (self.root / '.session-muted').exists() or os.environ.get('ROADSCORE_FORCE_MUTE') == '1'):
        self._close()
        return False
      return True

  def _watch(self, token):
    # No callback-side IO; cancellation does not depend on browser cleanup.
    while True:
      time.sleep(.25)
      if not self._check_session(token):
        return

  def dispatch(self, action, **data):
    with self.lock:
      if action == 'status':
        return self.status()
      if action == 'clock':
        return dict(ok=True, server_ms=self.clock() * 1000)
      if action == 'calibration_cancel':
        if self.session and data.get('session') == self.session['token']:
          self._close()
          return dict(ok=True)
        raise ValueError('Calibration expired; start again')
      self.safe()
      if action in ('calibration_start', 'test'):
        if data != {'attended': True}:
          raise ValueError('Confirm attended audio')
        if self.session:
          raise ValueError('A calibration is already active')
        state = self.status()
        if state['judging_locked'] or state['playback_active'] or not state['calibration']:
          raise ValueError('Audio is busy, muted or unavailable')
        operator = self.operator_lease()
        operator.__enter__()
        session_lease = lease(self.root / 'generated/session.lock')
        try:
          session_lease.__enter__()
        except BaseException:
          operator.__exit__(None, None, None)
          raise
        token = secrets.token_hex(16)
        clicks = {}
        try:
          sink = self.sink_factory(lambda index, at: clicks.__setitem__(index, at), count=4 if action == 'test' else COUNT)
          if self.output_provider() != state['output']:
            sink.close()
            raise ValueError('Output changed before calibration began')
          self.session = dict(token=token, sink=sink, clicks=clicks, taps={}, output=state['output'],
                              operator_lease=operator, session_lease=session_lease, last_client=self.clock(),
                              deadline=self.clock() + (15 if action == 'test' else 40), test=action == 'test')
          sink.start()
        except BaseException:
          if self.session:
            self._close()
          else:
            session_lease.__exit__(None, None, None); operator.__exit__(None, None, None)
          raise
        threading.Thread(target=self._watch, args=(token,), daemon=True).start()
        return dict(ok=True, session=token, interval_ms=round(INTERVAL * 1000), beats=COUNT,count_in=COUNT_IN,bpm=BPM,beats_per_bar=4)
      if action == 'set_latency':
        value = data.get('latency_ms')
        if type(value) is not int or not 0 <= value <= 1500:
          raise ValueError('Correction must be 0–1500 whole milliseconds')
        if self.session:
          raise ValueError('Finish calibration before saving')
        with self.operator_lease(), lease(self.root / 'generated/session.lock'):
          self.safe()
          output = self.output_provider()
          if not output or not output['connected']:
            raise ValueError('Output disconnected')
          path = self.root / 'generated/output_timing.json'
          values = read(path); values[output['id']] = value
          temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(values)); temp.replace(path)
        return dict(ok=True, latency_ms=value)
      session = self.session
      if not session or data.get('session') != session['token']:
        raise ValueError('Calibration expired; start again')
      session['last_client'] = self.clock()
      if action == 'calibration_cancel':
        self._close(); return dict(ok=True)
      if action == 'calibration_poll':
        delay = correction(self.root, session['output']['id']) if session['test'] else 0
        return dict(ok=True, clicks=[{'beat': index, 'server_ms': at + delay} for index, at in list(session['clicks'].items())], test=session['test'])
      if action == 'calibration_tap':
        at, uncertainty = data.get('server_ms'), data.get('uncertainty_ms')
        if type(at) not in (int, float) or not math.isfinite(at) or type(uncertainty) not in (int, float) or not 0 <= uncertainty <= 25:
          raise ValueError('Clock synchronization is too uncertain; retry')
        if abs(at - self.clock() * 1000) > 2000:
          raise ValueError('Stale tap')
        if session['test']:raise ValueError('Test mode does not collect taps')
        if COUNT_IN not in session['clicks'] or at<session['clicks'][COUNT_IN]:
          raise ValueError('Listen for two full bars; start tapping on bar three')
        index=COUNT_IN+len(session['taps'])
        if index>=COUNT or index not in session['clicks']:
          raise ValueError('Wait for the next beat')
        click=session['clicks'][index]
        previous=max((tap for _,tap in session['taps'].values()),default=float('-inf'))
        if at-previous<INTERVAL*1000*.45:
          raise ValueError('Tap once per beat')
        if not 0<=at-click<=1500:
          raise ValueError('Beat sequence was missed; restart with the two-bar count-in')
        session['taps'][index] = (click, at)
        return dict(ok=True, accepted_taps=len(session['taps']))
      if action == 'calibration_result':
        try:
          result = robust_offset(list(session['taps'].values()))
          result.update(bpm=BPM,count_in_beats=COUNT_IN,beat_pairing='sequential after two-bar count-in',whole_beat_ambiguity_possible=True)
        finally:
          self._close()
        return dict(ok=True, **result)
      raise ValueError('Unknown output operation')


PRESENTATION_FIELDS = ('phase', 'kind', 'amount', 'activation', 'strength', 'section', 'next_section',
                       'gesture_active', 'gesture_queued', 'turn_signal_music', 'lead', 'predicted_peak', 'scheduled',
                       'signal_shaker', 'core_apex', 'alert_accent', 'engagement_presentation')


class PresentationDelay:
  """Delay only visual music cues. Health/counters and the entire causal core stay current."""
  def __init__(self, root, output_provider=selected_output, clock=time.monotonic):
    self.root, self.provider, self.clock = root, output_provider, clock
    self.queue = deque()
    self.shown = {}
    self.last_check = float('-inf')
    self.delay_ms = 0
    self.identity = None
    self.output = None
    if output_provider is selected_output:
      def monitor():
        while True:
          self.output = output_provider()
          time.sleep(2)
      threading.Thread(target=monitor, daemon=True).start()
      self.provider = lambda: self.output

  def apply(self, snapshot):
    now = self.clock()
    if now - self.last_check > 2:
      output = self.provider()
      identity = output.get('id') if output else None
      if identity != self.identity:
        self.queue.clear(); self.shown = {}
      self.identity = identity
      self.delay_ms = correction(self.root, identity) if identity else 0
      self.last_check = now
    cues = {key: snapshot[key] for key in PRESENTATION_FIELDS if key in snapshot}
    self.queue.append((now + self.delay_ms / 1000, cues))
    while self.queue and self.queue[0][0] <= now:
      _, self.shown = self.queue.popleft()
    display = dict(snapshot)
    for key in PRESENTATION_FIELDS:
      display.pop(key, None)
    display.update(self.shown)
    display['presentation_latency_ms'] = self.delay_ms
    return display
