"""Native replay UI view of acknowledged demo controls; never publishes messages."""
import json
import math
import time
from pathlib import Path

from cue_timing import audible_state, REFERENCE
from demo_engagement import MODES, SIGNAL_MODES


def isolated_replay(environ):
  return (environ.get('ROADSCORE_REPLAY_UI_CONTROLS') == '1'
          and environ.get('SIMULATION') == '1'
          and not environ.get('ZMQ')
          and environ.get('OPENPILOT_PREFIX') == 'roadscore_replay')


class ReplayUIControls:
  def __init__(self, status_path, *, enabled=False, clock=time.monotonic):
    self.path = Path(status_path)
    self.enabled, self.clock = enabled, clock
    self.session = None

  def read(self):
    if not self.enabled:
      return 'recorded', 'recorded'
    try:
      state = json.loads(self.path.read_text())
      now = self.clock()
      stamp = state.get('command_wall')
      session = state.get('presentation_session_id')
      if (state.get('input_mode') != 'replay' or state.get('compute') == 'none'
          or state.get('presentation_timing_reference') != REFERENCE
          or not isinstance(session, str) or not session
          or type(stamp) not in (int, float) or not math.isfinite(stamp)
          or not 0 <= now - stamp <= 2):
        return 'recorded', 'recorded'
      if self.session is not None and session != self.session:
        return 'recorded', 'recorded'
      audible = audible_state(state, now)
      age = audible.get('presentation_display_lateness_ms')
      if type(age) not in (int, float) or not math.isfinite(age) or not 0 <= age <= 2000:
        return 'recorded', 'recorded'
      demo = audible.get('replay_demo', {})
      mode, signal = demo.get('mode'), demo.get('signal_mode')
      if mode in MODES and signal in SIGNAL_MODES:
        self.session = session
        return mode, signal
    except (OSError, ValueError, AttributeError):
      pass
    return 'recorded', 'recorded'


class ReplayStateView:
  """Copy only UI-facing fields; original readers and freshness stay intact."""
  def __init__(self, subscriber, controls):
    self.subscriber, self.controls = subscriber, controls
    self.mode = self.signal_mode = 'recorded'
    self.changed = False
    self.copies = {}

  def __getattr__(self, name):
    return getattr(self.subscriber, name)

  @property
  def updated(self):
    if self.changed:
      return {**self.subscriber.updated, 'selfdriveState': True}
    return self.subscriber.updated

  def update(self, *args, **kwargs):
    result = self.subscriber.update(*args, **kwargs)
    selection = self.controls.read()
    # An operator override must not hide missing replay data.
    if not all(self.subscriber.valid.get(s, False) and self.subscriber.alive.get(s, False)
               for s in ('selfdriveState', 'carState')):
      selection = ('recorded', 'recorded')
    self.changed = selection[0] != self.mode
    self.mode, self.signal_mode = selection
    self.copies.clear()
    return result

  def __getitem__(self, service):
    original = self.subscriber[service]
    engagement = self.mode != 'recorded' and service in ('selfdriveState', 'starpilotCarState')
    signals = self.signal_mode != 'recorded' and service == 'carState'
    if not (engagement or signals):
      return original
    if service not in self.copies:
      message = original.as_builder()
      if service == 'selfdriveState':
        message.enabled = message.active = self.mode == 'engaged'
        message.state = 'enabled' if self.mode == 'engaged' else 'disabled'
      elif service == 'starpilotCarState':
        message.alwaysOnLateralEnabled = self.mode == 'disengaged'
        message.pauseLateral = False
      else:
        message.leftBlinker = self.signal_mode == 'left'
        message.rightBlinker = self.signal_mode == 'right'
      self.copies[service] = message
    return self.copies[service].as_reader()

  def apply_native_mode(self, state):
    if self.mode != 'recorded' and state.started:
      # This demo deliberately shows native AOL mode when full engagement is off.
      # These are UI instance fields, not real driving Params.
      state.always_on_lateral_active = self.mode == 'disengaged'
      state.switchback_mode_enabled = False

  def snapshot(self):
    return {'mode': self.mode, 'signal_mode': self.signal_mode,
            'session_id': self.controls.session, 'scope': 'isolated-replay-ui'}
