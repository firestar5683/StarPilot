"""Galaxy's local-only RoadScore operator API. Never discovers or contacts a bench."""
import json
import os
from pathlib import Path
import importlib.util
import sys
import threading
import time
from urllib.parse import urlsplit

PROFILES = [{"id": "prism", "name": "Prism"}, {"id": "aurora", "name": "Aurora"}]
STATES = {"COLD", "PREPARING", "READY", "GENERATING", "DEGRADED"}


def control_origin_allowed(origin, host, scheme, fetch_site=None):
  # Browser-owned Fetch Metadata preserves same-origin identity through Galaxy's
  # reverse tunnel, whose internal Host differs from the public page address.
  if fetch_site and fetch_site != 'same-origin':
    return False
  if not origin:
    return True
  try:
    source = urlsplit(origin)
    target = urlsplit(f'{scheme}://{host}')
    if source.scheme not in {'http', 'https'} or not source.hostname or source.username or source.password or source.path or source.query or source.fragment:
      return False
    source_port = source.port or (443 if source.scheme == 'https' else 80)
    target_port = target.port or (443 if target.scheme == 'https' else 80)
  except ValueError:
    return False
  if fetch_site == 'same-origin':
    return True
  return (source.scheme, source.hostname, source_port) == (target.scheme, target.hostname, target_port)


def read_json(path):
  try:
    value = json.loads(path.read_text())
    return value if isinstance(value, dict) else {}
  except (OSError, ValueError):
    return {}


def validate_settings(data):
  if not isinstance(data, dict) or set(data) - {"profile", "latency_ms"}:
    raise ValueError("Unsupported setting")
  if "profile" in data and data["profile"] not in {p["id"] for p in PROFILES}:
    raise ValueError("Unknown style")
  if "latency_ms" in data:
    value = data["latency_ms"]
    if type(value) is not int or not 0 <= value <= 1500:
      raise ValueError("Timing correction must be whole milliseconds from 0 to 1500")
  return data


def current_worker(root, proc=Path('/proc')):
  """Verify the current ACE child and its recorded resident power supervisor."""
  root=Path(root);worker_path=root/'generated/ace_worker_state.json'
  worker=read_json(worker_path);owner=read_json(root/'generated/resident_owner.json')
  try:
    pid=int(worker['pid']);parent=int(owner.get('power_worker_pid',0))
    if pid<=0:return {}
    def process(identity,suffix):
      directory=proc/str(identity)
      arguments=(directory/'cmdline').read_bytes().split(b'\0')
      if not any(argument.endswith(suffix.encode()) for argument in arguments):raise ValueError('Wrong process')
      fields=(directory/'stat').read_text().rsplit(') ',1)[1].split()
      if fields[0]=='Z':raise ValueError('Exited process')
      return fields
    child=process(pid,'/ace_worker.py')
    actual_parent=int(child[1]);supervisor=process(actual_parent,'/power_worker.py')
    resident_valid=actual_parent==parent and str(owner.get('process_start_ticks',''))==supervisor[19]
    if not resident_valid:
      service=read_json(root/'generated/worker_service.json')
      service_pid=int(service['pid']);service_process=process(service_pid,'/worker_service.py')
      if int(supervisor[1])!=service_pid or str(service['start_ticks'])!=service_process[19]:return {}
    recorded=worker.get('process_start_ticks',worker.get('start_ticks'))
    if recorded is not None and str(recorded)!=child[19]:return {}
    boot=next(int(line.split()[1]) for line in (proc/'stat').read_text().splitlines() if line.startswith('btime '))
    if worker_path.stat().st_mtime+1 < boot+int(child[19])/os.sysconf('SC_CLK_TCK'):return {}
    if type(worker.get('generation_seed')) is not int or not 0<=worker['generation_seed']<2**32:return {}
    if worker.get('profile') not in {'prism','aurora'}:return {}
    phase=str(worker.get('phase','')).upper()
    if phase not in {'PREPARING','READY','GENERATING','FAILED'}:return {}
    if phase=='READY':
      initial=read_json(root/'generated/ace_initial.json')
      if initial.get('generation_seed')!=worker['generation_seed'] or initial.get('prepared_profile')!=worker['profile']:return {}
      if (root/'generated/worker_ready').read_text().strip()!='ace':return {}
    return worker
  except (OSError,ValueError,KeyError,IndexError,StopIteration):return {}


class Operator:
  def __init__(self, root=Path('/data/roadscore'), device=None, offroad=lambda: False):
    self.root = root
    self.offroad = offroad
    self.device = Path('/TICI').exists() if device is None else device
    self.lock = threading.Lock()
    self.preparing = False
    self.error = None
    self.output_owner = None
    self.output_init_lock = threading.Lock()

  def target(self, action, **payload):
    if not self.device:
      raise ValueError('Target output is available only on the comma')
    with self.output_init_lock:
      if self.output_owner is None:
        path = self.root / 'prototype/operator_output.py'
        if str(path.parent) not in sys.path:sys.path.insert(0,str(path.parent))
        spec = importlib.util.spec_from_file_location('roadscore_operator_output', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.output_owner = module.OutputOwner(self.root, self.offroad)
    return self.output_owner.dispatch(action, **payload)

  def status(self, offroad):
    settings = read_json(self.root / 'generated/operator_settings.json')
    worker=current_worker(self.root)
    live=bool(worker)
    try:
      output = self.target('status') if self.device else {}
    except (OSError, ValueError):
      output = {}
    # Without the output owner, playback/judging state cannot be proved safe.
    locked = output.get('judging_locked', True) or output.get('playback_active', True)
    phase = str(worker.get('phase','')).upper()
    state = ('DEGRADED' if phase == 'FAILED' else 'COLD') if not live else {'PREPARING': 'PREPARING', 'READY': 'READY', 'FAILED': 'DEGRADED', 'GENERATING': 'GENERATING'}.get(phase, 'COLD')
    if live and (self.root/'generated/busy').exists():state='GENERATING'
    if output.get('state') in STATES:
      state = output['state']
    return dict(available=self.device and self.root.exists(), state=state, profiles=PROFILES,
                profile=worker.get('profile') if live else settings.get('profile', 'prism'),
                selected_profile=settings.get('profile', 'prism'),
                composer='ace' if live else None, backend='Chestnut' if live else None,
                generation_seed=worker.get('generation_seed') if live else None,
                offroad=bool(offroad), locked=bool(locked), preparing=self.preparing,
                can_prepare=False,
                can_edit=False, can_calibrate=offroad and not locked and output.get('calibration', False),
                can_adjust=offroad and not locked and not output.get('calibrating', False) and output.get('timing_compensation', False),
                calibrating=output.get('calibrating', False), session_muted=output.get('session_muted', True), output=output.get('output'), latency_ms=output.get('latency_ms'), error=self.error or output.get('error'))

  def operate(self, action, data, offroad):
    if not offroad and action != 'calibration_cancel':
      raise ValueError('RoadScore controls are available while parked')
    with self.lock:
      if action == 'clock':
        return self.target('clock')
      if action in {'calibration_start', 'calibration_tap', 'calibration_result', 'calibration_cancel', 'calibration_poll', 'test'}:
        if action == 'calibration_start' and data != {'attended': True}:
          raise ValueError('Confirm that you are ready to hear the clicks')
        if action == 'calibration_tap':
          if set(data) != {'session', 'server_ms', 'uncertainty_ms'} or not isinstance(data['session'], str) or len(data['session']) > 100 or type(data['server_ms']) not in (int, float) or not 0 <= data['server_ms'] < 1e15:
            raise ValueError('Invalid tap')
        elif action in {'calibration_result', 'calibration_cancel', 'calibration_poll'}:
          if set(data) != {'session'} or not isinstance(data['session'], str) or len(data['session']) > 100:
            raise ValueError('Invalid session')
        elif action == 'test' and data != {'attended': True}:
          raise ValueError('Confirm attended audio test')
        return self.target(action, **data)
      status = self.status(offroad)
      if status['locked']:
        raise ValueError('Controls are locked during playback/judging or while output status is unavailable')
      if action == 'settings':
        data = validate_settings(data)
        if 'profile' in data:raise ValueError('Style changes are unavailable during this demo; use the normal launcher')
        if 'latency_ms' in data:
          if not status['can_adjust']:
            raise ValueError('Output timing compensation is unavailable')
          self.target('set_latency', latency_ms=data['latency_ms'])
        path = self.root / 'generated/operator_settings.json'
        with self.output_owner.operator_lease():
          self.output_owner.safe()
          previous = read_json(path)
          previous.update(data)
          path.parent.mkdir(parents=True, exist_ok=True)
          temporary = path.with_suffix('.tmp')
          temporary.write_text(json.dumps(previous))
          temporary.replace(path)
        return {'ok': True}
      if action == 'prepare':
        raise ValueError('Prepare from the normal RoadScore launcher; Galaxy preparation is not enabled')
      raise ValueError('Unknown RoadScore operation')


def register(app, params):
  from flask import jsonify, request
  prototype=Path('/data/roadscore/prototype')
  if str(prototype) not in sys.path:sys.path.insert(0,str(prototype))
  from operator_output import real_offroad
  operator = Operator(offroad=real_offroad)

  @app.route('/api/roadscore/status')
  def roadscore_status():
    response = jsonify(operator.status(real_offroad()))
    response.headers['Cache-Control'] = 'no-store'
    return response

  @app.route('/api/roadscore/<action>', methods=['POST'])
  def roadscore_operation(action):
    origin = request.headers.get('Origin')
    if not control_origin_allowed(origin, request.host, request.scheme, request.headers.get('Sec-Fetch-Site')):
      return jsonify(error='Cross-origin controls are not allowed'), 403
    if not request.is_json:
      return jsonify(error='JSON request required'), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
      return jsonify(error='Expected an object'), 400
    if action == 'clock':
      if data:
        return jsonify(error='Clock request takes no arguments'), 400
      # Read-only synchronization must not include subprocess or output-lock delays.
      response = jsonify(ok=True, server_ms=time.monotonic() * 1000)
      response.headers['Cache-Control'] = 'no-store'
      return response
    try:
      return jsonify(operator.operate(action, data, real_offroad()))
    except (ValueError, OSError) as error:
      return jsonify(error=str(error)), 409
    except Exception:
      app.logger.exception('RoadScore operator action failed')
      return jsonify(error='RoadScore output is unavailable; check the local service'), 503
