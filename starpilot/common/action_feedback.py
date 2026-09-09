"""Short-lived Bluetooth action receipts. Never replay or execute UI messages."""
from time import monotonic

DISPLAY_SECONDS = 3.0
MODE_NAMES = ('Chill', 'Experimental', 'Conditional Experimental', 'Conditional Chill')
MODE_CHIPS = ('Chill', 'Exp', 'CEM', 'CCM')
PERSONALITY_NAMES = ('Aggressive', 'Standard', 'Relaxed')


def visible_receipt(status, now):
  if not isinstance(status, dict):
    return None
  receipt = status.get('last_action')
  if not isinstance(receipt, dict):
    return None
  try:
    age = now - float(receipt['at'])
    if not 0 <= age < DISPLAY_SECONDS:
      return None
    if receipt.get('state') not in ('confirmed', 'requested', 'pending', 'blocked', 'unconfirmed'):
      return None
    if not all(isinstance(receipt.get(k), str) for k in ('title', 'value')):
      return None
    choices = receipt.get('choices', [])
    if not isinstance(choices, list) or len(choices) > 4 or not all(isinstance(v, str) for v in choices):
      return None
    if type(receipt.get('selected', -1)) is not int:
      return None
  except (TypeError, ValueError, KeyError):
    return None
  return receipt


class ActionFeedback:
  def __init__(self, params, memory, clock=monotonic):
    self.params, self.memory, self.clock = params, memory, clock
    self.receipt = None
    self._sequence = 0
    self._pending = None

  def _show(self, token, title, value, state, choices=(), selected=-1):
    # A slow reply to an earlier press must not overwrite the most recent press.
    if token == self._sequence:
      self.receipt = dict(id=token, at=self.clock(), title=title[:80], value=value[:100],
                          state=state, choices=list(choices), selected=selected)

  def execute(self, slot_index, dispatch):
    from openpilot.starpilot.common.favorite_slots import (
      FAVORITE_SLOT_COUNT, load_favorite_slots, FAVORITE_ACTION_LABELS,
      get_catalog_param_map, get_favorite_param_value, get_param_enum_options, is_favorite_action_key,
    )
    from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_CYCLE_PERSONALITY
    from openpilot.starpilot.common.longitudinal_mode_actions import ACTION_TARGETS, LEGACY_MODE_ACTIONS, MODE_ORDER, request_mode_action
    from openpilot.starpilot.system.wheel_controls.wheel_controlsd import load_controller_action_slots
    slots = load_favorite_slots(self.params) if slot_index < FAVORITE_SLOT_COUNT else load_controller_action_slots(self.params)
    index = slot_index if slot_index < FAVORITE_SLOT_COUNT else slot_index - FAVORITE_SLOT_COUNT
    if not 0 <= index < len(slots):
      return False
    slot = slots[index]
    key = slot.get('key')
    self._sequence += 1
    token = self._sequence
    self._pending = None
    meta = get_catalog_param_map().get(key, {})
    title = FAVORITE_ACTION_LABELS.get(key) or meta.get('label') or slot.get('label') or 'Controller action'
    if not key or not slot.get('enabled'):
      self._show(token, title, 'Not configured', 'blocked')
      return False

    if key in ACTION_TARGETS or key in LEGACY_MODE_ACTIONS:
      title = 'Speed control / selected'
      self._show(token, title, 'Changing mode...', 'pending')
      def completed(mode):
        if mode in MODE_ORDER:
          index = MODE_ORDER.index(mode)
          self._show(token, title, MODE_NAMES[index], 'confirmed', MODE_CHIPS, index)
        else:
          self._show(token, title, 'Change not confirmed', 'unconfirmed')
      accepted = request_mode_action(key, on_result=completed)
      if not accepted:
        self._show(token, title, 'Busy: try again', 'blocked')
      return accepted

    expected = None
    options = get_param_enum_options(key)
    if not is_favorite_action_key(key):
      before = get_favorite_param_value(key, self.params)
      if isinstance(before, bool):
        expected = not before
      elif options:
        values = [o.get('value') for o in options]
        if before in values:
          expected = values[(values.index(before) + 1) % len(values)]
    try:
      accepted = dispatch(key, self.params, self.memory, value=slot.get('value'))
    except Exception:
      self._show(token, title, 'Change not confirmed', 'unconfirmed')
      raise
    if not accepted:
      self._show(token, title, 'Not available right now', 'blocked')
    elif key == CONTROLLER_ACTION_CYCLE_PERSONALITY:
      index = self.params.get_int('LongitudinalPersonality')
      if index in range(3):
        self._show(token, 'Driving personality / selected', PERSONALITY_NAMES[index], 'confirmed', PERSONALITY_NAMES, index)
      else:
        self._show(token, title, 'Change not confirmed', 'unconfirmed')
    elif expected is not None:
      self._show(token, title, 'Applying...', 'pending')
      self._pending = (token, title, key, expected, options, self.clock() + 1.5)
      self.update()
    else:
      # Counters, engagement and selfie are requests to other processes, not
      # acknowledgements. Never claim their effect has already happened.
      value = 'Requested'
      if slot.get('value') is not None:
        value = f"{slot['value']:g} {'km/h' if self.params.get_bool('IsMetric') else 'mph'} requested"
      self._show(token, title, value, 'requested')
    return accepted

  def update(self):
    if not self._pending:
      return
    from openpilot.starpilot.common.favorite_slots import get_favorite_param_value
    token, title, key, expected, options, deadline = self._pending
    if get_favorite_param_value(key, self.params) == expected:
      choices = [str(o.get('label', o.get('value'))) for o in options]
      selected = next((i for i, o in enumerate(options) if o.get('value') == expected), -1)
      label = choices[selected] if selected >= 0 else ('On' if expected else 'Off')
      self._show(token, title, label, 'confirmed', choices, selected)
      self._pending = None
    elif self.clock() >= deadline:
      self._show(token, title, 'Change not confirmed', 'unconfirmed')
      self._pending = None
