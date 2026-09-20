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
TEST_COUNT = 12
COUNT_IN = 8
COUNT = 20
REFINE_COUNT = 24
REFINE_METHOD = 'coarse-anchored-rhythm-v1'
TIMING_REFERENCE = 'portaudio-dac-residual-v1'
MARKER_COUNT = COUNT - COUNT_IN
METHOD = 'irregular-marker-reaction-v1'
MARKER_INTERVALS = (1.8, 2.4, 2.1, 2.7, 1.9, 2.5, 2.2, 2.8, 2.0, 2.6, 2.3)
MARKER_OFFSETS = (8.6,)
for _interval in MARKER_INTERVALS:
  MARKER_OFFSETS += (round(MARKER_OFFSETS[-1] + _interval, 3),)
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


def real_offroad(params=Path('/data/params/d')):
  # Native Params uses /data/params + /d and getBool compares exact bytes to "1".
  # Explicit paths deliberately ignore the replay process's Params namespace.
  try:
    return (params/'IsOffroad').read_bytes()==b'1' and (params/'IsOnroad').read_bytes()==b'0'
  except OSError:return False


def real_bluetooth_selection(params=Path('/data/params/d')):
  try:
    return {'enabled':(params/'BluetoothEnabled').read_bytes()==b'1',
            'address':(params/'BluetoothAudioAddress').read_text().strip()}
  except (OSError,UnicodeError):return {'enabled':False,'address':''}


def describe_output(selected,status):
  from bluetooth_output import ADDRESS
  address=selected.get('address','').upper()
  if selected.get('enabled') is not True or not ADDRESS.fullmatch(address):return None
  device=next((d for d in status.get('devices',[]) if d.get('address','').upper()==address),None)
  connected=bool(status.get('enabled') and status.get('powered') and device and device.get('connected') and device.get('audio'))
  return dict(id='bluealsa:'+address,address=address,name=device.get('name',address) if device else address,
              connected=connected,muted=False,bluetooth=True,physical_latency_ms=None)


def selected_output():
  try:
    from openpilot.starpilot.system.bluetooth.protocol import BluetoothClient
    selected=real_bluetooth_selection()
    status=BluetoothClient(timeout=2).status()
    return describe_output(selected,BluetoothClient.serialize_status(status))
  except (OSError,ValueError,ImportError,subprocess.SubprocessError):return None


def playback_process_active(proc=Path('/proc')):
  try:
    for path in proc.iterdir():
      if not path.name.isdigit():continue
      try:cmd=(path/'cmdline').read_bytes().replace(b'\0',b' ')
      except OSError:continue
      if any(name in cmd for name in (b'/prototype/app.py',b'/prototype/stored_score.py',b'/prototype/native_prepared_showcase.py')):return True
      if b'/prototype/mac_showcase.py' in cmd and b'--audio-worker' in cmd:return True
  except OSError:return True
  return False


def correction_record(root, identity):
  path=Path(root)/'generated/output_timing.json'
  values=read(path);value=values.get(identity)
  if (isinstance(value,dict) and value.get('timing_reference')==TIMING_REFERENCE and
      type(value.get('latency_ms')) is int and 0<=value['latency_ms']<=1500):
    return {**value,'status':'dac-residual-estimate'}
  if type(value) is int and 0<=value<=1500:
    result=read(Path(root)/'generated/calibration_latest_result.json')
    if (result.get('method')==REFINE_METHOD and result.get('output',{}).get('id')==identity and
        type(result.get('latency_ms')) is int and result['latency_ms']==value and
        type(result.get('accepted_taps')) is int and result['accepted_taps']>=8):
      migrated=dict(latency_ms=value,timing_reference=TIMING_REFERENCE,saved_wall=time.time(),
                    source='matching saved two-stage DAC-relative refinement',
                    migrated_legacy_value=value,calibration_created_wall=result.get('created_wall'),
                    calibration_method=result['method'])
      values[identity]=migrated
      try:
        temporary=path.with_name(path.name+f'.{os.getpid()}.{threading.get_ident()}.tmp')
        temporary.write_text(json.dumps(values));temporary.replace(path)
      except OSError:
        return dict(latency_ms=0,status='legacy-unverified',legacy_latency_ms=value,migration_error='Could not persist timing reference')
      return {**migrated,'status':'dac-residual-estimate'}
    return dict(latency_ms=0,status='legacy-unverified',legacy_latency_ms=value)
  return dict(latency_ms=0,status='uncalibrated')


def correction(root, identity):
  return correction_record(root,identity)['latency_ms']


def robust_offset(pairs):
  if len(pairs) < 8:
    raise ValueError('At least eight different markers are required')
  differences = [tap - click for click, tap in pairs]
  center = median(differences)
  mad = median(abs(value - center) for value in differences)
  accepted = [value for value in differences if abs(value - center) <= max(35, 4.4478 * mad)]
  if len(accepted) < 8 or len(accepted) < len(pairs) * .65:
    raise ValueError('Tap timing was inconsistent; retry')
  spread = median(abs(value - median(accepted)) for value in accepted)
  if spread > 80:
    raise ValueError('Tap timing varied too much; retry')
  raw = round(median(accepted))
  return dict(latency_ms=max(0, min(1500, raw)), raw_offset_ms=raw, accepted_taps=len(accepted),
              rejected_taps=len(pairs) - len(accepted), spread_ms=round(spread), includes_human_tap_bias=True)


def rhythm_pair(clicks, at, coarse):
  interval_ms=INTERVAL*1000
  margin=max(60,3*coarse.get('spread_ms',0))
  if margin>=interval_ms/2:raise ValueError('Coarse estimate is too uncertain; repeat the chimes')
  approximate=at-coarse['latency_ms']
  candidates=[(index,click) for index,click in clicks.items() if COUNT_IN<=index<REFINE_COUNT]
  if not candidates:raise ValueError('Wait for the third bar before tapping')
  index,click=min(candidates,key=lambda pair:abs(approximate-pair[1]))
  if abs(approximate-click)>=interval_ms/2-margin:
    raise ValueError('Whole-beat choice is ambiguous; repeat the chimes, then tap with the rhythm')
  if not 0<=at-click<=1500:raise ValueError('Rhythmic offset is outside 0–1500 ms; repeat calibration')
  return index,click


class ClickSink:
  """Own a separate local process so each session binds ALSA before PortAudio loads."""
  def __init__(self,on_click,count=COUNT):
    self.on_click=on_click;self.count=count;self.process=None;self.failed=False;self.closed=False
    self.error=None;self.stderr_tail='';self.log_path=Path(__file__).resolve().parents[1]/'generated/calibration-last-error.log'
    self.output=selected_output()
    if not self.output or not self.output['connected']:raise ValueError('Selected Bluetooth speaker is disconnected')

  def start(self):
    env=os.environ.copy()
    for key in ('OPENPILOT_PREFIX','PARAMS_ROOT','ZMQ'):env.pop(key,None)
    self.process=subprocess.Popen(['/usr/local/venv/bin/python',str(Path(__file__).with_name('operator_click_process.py')),
                                  '--address',self.output['address'],'--count',str(self.count)],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    def stderr_reader():
      try:
        while True:
          chunk=self.process.stderr.read(4096)
          if not chunk:break
          self.stderr_tail=(self.stderr_tail+chunk)[-16384:]
          self.log_path.parent.mkdir(parents=True,exist_ok=True)
          self.log_path.write_text(self.stderr_tail)
      except OSError:pass
    diagnostic_thread=threading.Thread(target=stderr_reader,daemon=True);diagnostic_thread.start()
    def collect():
      try:
        for line in self.process.stdout:
          value=json.loads(line)
          if value.get('error'):
            self.error=str(value['error'])[-1500:];self.failed=True
          if 'beat' in value:self.on_click(value['beat'],value['server_ms'],value)
        code=self.process.wait();diagnostic_thread.join(timeout=.2)
        if code!=0 and not self.closed:
          self.error=self.error or f'Calibration audio process exited with status {code}. '+self.stderr_tail.strip()[-1500:]
          self.failed=True
      except (OSError,ValueError) as error:
        self.error=f'Calibration output protocol failed: {error}';self.failed=True
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
    self.last_error=None;self.failed_token=None

  def operator_lease(self):
    return lease(self.root / 'generated/operator.lock')

  def safe(self):
    if not self.offroad():
      raise ValueError('Park before changing RoadScore')

  def status(self, output=None, supplied=False):
    output = output if supplied else self.output_provider()
    muted = (self.root / '.session-muted').exists() or os.environ.get('ROADSCORE_FORCE_MUTE') == '1'
    active = playback_process_active() or busy(self.root / 'generated/session.lock')
    worker = read(self.root / 'generated/ace_worker_state.json')
    try:
      worker_busy = str(worker.get('phase', '')).upper() in ('PREPARING', 'GENERATING') and b'ace_worker.py' in Path(f"/proc/{int(worker['pid'])}/cmdline").read_bytes()
    except (OSError, KeyError, ValueError):
      worker_busy = False
    active = active or worker_busy
    locked = busy(self.root / 'generated/operator.lock') and self.session is None
    return dict(ok=True, error=(getattr(self.session['sink'],'error',None) if self.session else None) or self.last_error, calibrating=self.session is not None, output=output, latency_ms=correction(self.root, output['id']) if output else None,
                judging_locked=locked, playback_active=active and self.session is None,
                calibration=bool(output and output['connected'] and not output['muted'] and not muted),
                timing_compensation=bool(output), timing_correction=correction_record(self.root,output['id']) if output else None, session_muted=muted)

  def _close(self):
    session, self.session = self.session, None
    if session:
      if session['sink'].failed:
        self.failed_token=session['token'];self.last_error=getattr(session['sink'],'error',None) or 'Calibration audio process failed; inspect generated/calibration-last-error.log'
        try:(self.root/'generated/calibration_failure.json').write_text(json.dumps({'error':self.last_error,'wall':time.time()}))
        except OSError:pass
      try:
        session['sink'].close()
      finally:
        session['session_lease'].__exit__(None, None, None)
        session['operator_lease'].__exit__(None, None, None)

  def _check_session(self, token):
    # Potentially slow BlueZ IPC must not serialize the tap/poll handlers.
    output=self.output_provider();parked=self.offroad();playing=playback_process_active()
    with self.lock:
      session = self.session
      if session is None or session['token'] != token:
        return False
      if (not parked or self.clock() > session['deadline'] or
          self.clock() - session['last_client'] > 7 or not output or output['id'] != session['output']['id'] or
          output['muted'] or not output['connected'] or playing or session['sink'].failed or
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
    if action=='status':
      output=self.output_provider()
      with self.lock:return self.status(output=output,supplied=True)
    with self.lock:
      if action == 'clock':
        return dict(ok=True, server_ms=self.clock() * 1000)
      if action == 'calibration_cancel':
        if self.session and data.get('session') == self.session['token']:
          self._close()
          return dict(ok=True)
        raise ValueError('Calibration expired; start again')
      self.safe()
      if action in ('calibration_start', 'calibration_refine', 'test'):
        if data != {'attended': True}:
          raise ValueError('Confirm attended audio')
        if self.session:
          raise ValueError('A calibration is already active')
        state = self.status()
        if state['judging_locked'] or state['playback_active'] or not state['calibration']:
          raise ValueError('Audio is busy, muted or unavailable')
        coarse=None
        if action=='calibration_refine':
          coarse=read(self.root/'generated/calibration_coarse_result.json') or read(self.root/'generated/calibration_latest_result.json')
          if (coarse.get('method')!=METHOD or coarse.get('output',{}).get('id')!=state['output']['id'] or
              not 0<=time.time()-coarse.get('created_wall',0)<=600 or type(coarse.get('latency_ms')) is not int or
              not 0<=coarse['latency_ms']<=1500 or coarse.get('accepted_taps',0)<8):
            raise ValueError('First complete the chimes on this speaker; coarse estimates expire after ten minutes')
        count=TEST_COUNT if action=='test' else REFINE_COUNT if coarse else COUNT
        operator = self.operator_lease()
        operator.__enter__()
        session_lease = lease(self.root / 'generated/session.lock')
        try:
          session_lease.__enter__()
        except BaseException:
          operator.__exit__(None, None, None)
          raise
        self.last_error=None;self.failed_token=None
        token = secrets.token_hex(16)
        clicks = {};click_timing={}
        def record_click(index,at,details=None):
          clicks[index]=at
          if details:click_timing[index]=details
        try:
          sink = self.sink_factory(record_click, count=count)
          if self.output_provider() != state['output']:
            sink.close()
            raise ValueError('Output changed before calibration began')
          self.session = dict(token=token, sink=sink, clicks=clicks, click_timing=click_timing, taps={}, output=state['output'],
                              operator_lease=operator, session_lease=session_lease, last_client=self.clock(),
                              deadline=self.clock() + (15 if action == 'test' else 60), test=action == 'test', coarse=coarse)
          sink.start()
        except BaseException:
          if self.session:
            self._close()
          else:
            session_lease.__exit__(None, None, None); operator.__exit__(None, None, None)
          raise
        threading.Thread(target=self._watch, args=(token,), daemon=True).start()
        return dict(ok=True, session=token, interval_ms=round(INTERVAL * 1000), beats=count,
                    count_in=COUNT_IN,bpm=BPM,beats_per_bar=4,method=REFINE_METHOD if coarse else METHOD,
                    marker_count=0 if coarse else MARKER_COUNT,target_taps=16 if coarse else MARKER_COUNT,
                    min_taps=8 if coarse else MARKER_COUNT,coarse_offset_ms=coarse['latency_ms'] if coarse else None,
                    marker_offsets_ms=[] if coarse else [round(at*1000) for at in MARKER_OFFSETS],
                    instructions=('Listen for two bars, then tap steadily with the heard beat. Missed beats are allowed.' if coarse else
                                  'Listen to two bars without tapping. Then tap once at the START of each two-tone marker; wait through the silence. The estimate includes your reaction time.'))
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
          values = read(path); values[output['id']] = dict(latency_ms=value,timing_reference=TIMING_REFERENCE,
                                                         saved_wall=time.time(),source='operator-confirmed DAC residual estimate')
          temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(values)); temp.replace(path)
        return dict(ok=True, latency_ms=value)
      session = self.session
      if not session or data.get('session') != session['token']:
        if data.get('session')==self.failed_token and self.last_error:raise ValueError(self.last_error)
        raise ValueError('Calibration expired; start again')
      if session['sink'].failed:
        self._close();raise ValueError(self.last_error)
      session['last_client'] = self.clock()
      if action == 'calibration_cancel':
        self._close(); return dict(ok=True)
      if action == 'calibration_poll':
        delay = correction(self.root, session['output']['id']) if session['test'] else 0
        return dict(ok=True, clicks=[{'beat': index, 'server_ms': at + delay, 'kind':('rhythm' if session.get('coarse') else 'marker') if index>=COUNT_IN and not session['test'] else 'count_in'} for index, at in list(session['clicks'].items())], test=session['test'])
      if action == 'calibration_tap':
        at, uncertainty = data.get('server_ms'), data.get('uncertainty_ms')
        if type(at) not in (int, float) or not math.isfinite(at) or type(uncertainty) not in (int, float) or not 0 <= uncertainty <= 25:
          raise ValueError('Clock synchronization is too uncertain; retry')
        if abs(at - self.clock() * 1000) > 2000:
          raise ValueError('Stale tap')
        if session['test']:raise ValueError('Test mode does not collect taps')
        if session.get('pairing_error'):raise ValueError(session['pairing_error'])
        if session.get('coarse'):
          index,click=rhythm_pair(session['clicks'],at,session['coarse'])
          if index in session['taps']:raise ValueError('This beat already has a tap')
          session['taps'][index]=(click,at)
          return dict(ok=True,accepted_taps=len(session['taps']),paired_beat=index)
        if COUNT_IN not in session['clicks'] or at<session['clicks'][COUNT_IN]:
          raise ValueError('Listen for two full bars; tap only the two-tone markers after the count-in')
        index=COUNT_IN+len(session['taps'])
        if index>=COUNT or index not in session['clicks']:
          raise ValueError('Wait for the next two-tone marker')
        click=session['clicks'][index]
        previous=max((tap for _,tap in session['taps'].values()),default=float('-inf'))
        if at-previous<INTERVAL*1000*.45:
          raise ValueError('Tap once per marker')
        if not 0<=at-click<=1500:
          session['pairing_error']='A marker was missed or tapped outside its 0–1500 ms window; restart the measurement'
          raise ValueError(session['pairing_error'])
        session['taps'][index] = (click, at)
        return dict(ok=True, accepted_taps=len(session['taps']))
      if action == 'calibration_result':
        try:
          if session.get('pairing_error'):raise ValueError(session['pairing_error'])
          if not session.get('coarse') and len(session['taps'])!=MARKER_COUNT:raise ValueError('Tap all twelve markers before finishing; restart if a marker was missed')
          result = robust_offset(list(session['taps'].values()))
          result.update(method=METHOD,bpm=BPM,count_in_beats=COUNT_IN,marker_count=MARKER_COUNT,
                        beat_pairing='sequential absolute marker timestamps; no modulo pairing',whole_beat_ambiguity_possible=False,
                        measurement='Bluetooth/output delay plus human reaction time; not a physical latency measurement',
                        output=session['output'],created_wall=time.time(),timing_reference=TIMING_REFERENCE,
                        timing_instrumentation_complete=all(index in session['click_timing'] for index in session['taps']),
                        pairs=[dict(marker=index,server_ms=click,tap_ms=tap,offset_ms=tap-click,
                                               timing=session['click_timing'].get(index))
                               for index,(click,tap) in session['taps'].items()])
          if session.get('coarse'):
            coarse=session['coarse'];interval_ms=round(INTERVAL*1000)
            phase=result['raw_offset_ms']%interval_ms
            branch=phase+round((coarse['latency_ms']-phase)/interval_ms)*interval_ms
            margin=max(60,3*coarse.get('spread_ms',0),3*result['spread_ms'])
            if abs(branch-coarse['latency_ms'])>=interval_ms/2-margin or not 0<=branch<=1500:
              raise ValueError('Whole-beat choice is ambiguous; repeat the chimes and rhythm')
            result.update(latency_ms=branch,raw_offset_ms=branch,method=REFINE_METHOD,marker_count=0,
                          beat_pairing='nearest coarse-corrected rhythmic beat; no sequential tap shift',
                          whole_beat_ambiguity_possible=True,
                          phase_offset_ms=phase,coarse_offset_ms=coarse['latency_ms'],
                          coarse_result=coarse,branch_margin_ms=interval_ms/2-abs(branch-coarse['latency_ms']),
                          measurement='Coarse-anchored rhythmic tap estimate; human timing bias remains, not a physical latency measurement',
                          branch_assumption='Coarse reaction bias and rhythmic tap error must differ by less than half a beat; borderline estimates are rejected')
          else:
            path=self.root/'generated/calibration_coarse_result.json'
            temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result));temp.replace(path)
          path=self.root/'generated/calibration_latest_result.json'
          temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result));temp.replace(path)
        finally:
          self._close()
        return dict(ok=True, **result)
      raise ValueError('Unknown output operation')


PRESENTATION_FIELDS = ('phase', 'kind', 'amount', 'activation', 'strength', 'section', 'next_section',
                       'gesture_active', 'gesture_queued', 'turn_signal_music', 'lead', 'predicted_peak', 'scheduled',
                       'signal_shaker', 'core_apex', 'alert_accent', 'engagement_presentation', 'motion_presentation', 'curve_reaction', 'replay_demo')


def recent_presentation_timeline(queue, command_wall, now):
  """Preserve cue selection from two seconds before this status onward.

  Readers can sample their clock before reading the newly published status.
  Keep a lookback matching replay controls' freshness window, the latest cue
  already due at its start, and every later cue. DAC corrections can reorder
  entries, so neither insertion order nor audio sequence determines expiry.
  """
  timeline = list(queue)
  if type(command_wall) not in (int, float) or not math.isfinite(command_wall) or command_wall > now:
    return timeline
  cutoff = command_wall - 2.
  due = [entry for entry in timeline if entry['audible_wall'] <= cutoff]
  if not due:
    return timeline
  # max() keeps the first equal timestamp, just like cue_timing.audible_state.
  selected = max(due, key=lambda entry: entry['audible_wall'])
  return [entry for entry in timeline if entry is selected or entry['audible_wall'] > cutoff]


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
    self.last_sequence=None
    if output_provider is selected_output:
      def monitor():
        while True:
          self.output = output_provider()
          time.sleep(2)
      threading.Thread(target=monitor, daemon=True).start()
      self.provider = lambda: self.output

  def apply(self, snapshot, rendered=None):
    now = self.clock()
    if now - self.last_check > 2:
      output = self.provider()
      identity = output.get('id') if output else None
      if identity != self.identity:
        self.queue.clear(); self.shown = {};self.last_sequence=None
      self.identity = identity
      self.record = correction_record(self.root,identity) if identity else dict(latency_ms=0,status='uncalibrated')
      self.delay_ms = self.record['latency_ms']
      self.last_check = now
    if rendered is not None:
      sequence=rendered['sequence']
      if sequence!=self.last_sequence:
        self.last_sequence=sequence
        due=rendered['dac_wall']+self.delay_ms/1000
        self.queue.append(dict(audible_wall=due,sequence=sequence,
                               callback_wall=rendered['callback_wall'],dac_wall=rendered['dac_wall'],
                               cues={key:rendered['cues'][key] for key in PRESENTATION_FIELDS if key in rendered['cues']}))
    else:
      # Callers without callback timing retain an explicitly unverified compatibility path.
      self.queue.append(dict(audible_wall=now+self.delay_ms/1000,sequence=None,
                             cues={key:snapshot[key] for key in PRESENTATION_FIELDS if key in snapshot}))
    due=[entry for entry in self.queue if entry['audible_wall']<=now]
    if due:self.shown=max(due,key=lambda entry:entry['audible_wall'])['cues']
    while len(self.queue)>64:self.queue.popleft()
    display = dict(snapshot)
    for key in PRESENTATION_FIELDS:display.pop(key,None)
    display.update(self.shown)
    display['presentation_latency_ms']=self.delay_ms
    display['presentation_timing_reference']='portaudio-dac-plus-residual-v1' if rendered is not None else 'unverified-observation-clock'
    display['presentation_clock']='device-monotonic-seconds'
    display['presentation_correction']=self.record
    display['presentation_timeline']=recent_presentation_timeline(self.queue,snapshot.get('command_wall'),now)
    return display
