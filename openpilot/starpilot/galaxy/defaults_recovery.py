"""Recovery through canonical feature rows and their existing guarded owners."""
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
import secrets
import threading

from openpilot.starpilot.galaxy.settings import PAGES, TTL, SettingsChanged, _session_key
from openpilot.starpilot.ui.feature_settings_state import row_default


def equivalent(current, default):
  if current == default:
    return True
  try:
    left, right = Decimal(current), Decimal(default)
    return left.is_finite() and right.is_finite() and left == right
  except (InvalidOperation, TypeError, ValueError):
    return False


@dataclass(frozen=True)
class RecoveryView:
  session: bytes
  generation: bytes
  cp_raw: bytes | None
  expires: float
  rows: tuple


class DefaultsRecovery:
  def __init__(self, gateway):
    self.gateway = gateway
    self.lock = threading.Lock()
    self.views = {}
    self.intents = {}

  def snapshot(self, token, generation):
    cp_raw = self.gateway.context.sample().cp_raw
    seen, choices, rows = set(), [], []
    for page in sorted(PAGES):
      ctx = self.gateway.context.sample()
      if ctx.cp_raw != cp_raw:
        raise SettingsChanged('Vehicle changed')
      state = self.gateway._state(page, ctx)
      for row in state.rows:
        request = row_default(replace(row, available=True))
        if request is None or request.key in seen or equivalent(row.value, row.default_value) or (row.source is None and row.related_source is None):
          continue
        seen.add(request.key)
        index = len(choices)
        choices.append((page, row))
        rows.append({'id': index, 'page': page, 'label': row.label, 'current': row.value,
                     'default': row.default_value, 'modified': True, 'available': row.available, 'reason': row.reason,
                     'resetAvailable': ctx.parked and row_default(row, allow_inactive=True) is not None})
    if len(choices) > 128:
      raise SettingsChanged('Too many settings to reset together')
    view = secrets.token_urlsafe(24)
    with self.lock:
      now = self.gateway.clock()
      self.views = {k: v for k, v in self.views.items() if v.expires > now}
      if len(self.views) >= 16:
        self.views.pop(next(iter(self.views)))
      self.views[view] = RecoveryView(_session_key(token), generation, cp_raw, now + TTL, tuple(choices))
    return {'view': view, 'rows': rows, 'count': len(rows), 'resettableCount': sum(row['resetAvailable'] for row in rows),
            'scope': 'Saved settings available for this vehicle. Runtime and hardware state are excluded.'}

  def preview(self, view, selected, token, generation):
    with self.lock:
      saved = self.views.get(view)
      if (saved is None or saved.expires <= self.gateway.clock() or saved.session != _session_key(token) or
          saved.generation != generation or not isinstance(selected, list) or not selected or
          any(type(i) is not int or not 0 <= i < len(saved.rows) for i in selected) or len(selected) != len(set(selected))):
        raise SettingsChanged('Settings recovery selection expired')
      rows = tuple(sorted((saved.rows[i] for i in selected), key=lambda item: item[1].default_value == "Off"))
      if any(row_default(row, allow_inactive=True) is None for _, row in rows):
        raise SettingsChanged('Selected settings cannot be reset for this vehicle')
      intent = secrets.token_urlsafe(24)
      self.intents[intent] = (saved, rows)
      if len(self.intents) > 16:
        self.intents.pop(next(iter(self.intents)))
    return {'intent': intent, 'question': f'Reset {len(rows)} selected settings to their current StarPilot defaults?',
            'labels': [row.label for _, row in rows], 'count': len(rows)}

  def confirm(self, intent, token, generation, *, session_valid=lambda: True):
    with self.lock:
      value = self.intents.pop(intent, None)
    if value is None:
      raise SettingsChanged('Settings recovery confirmation expired')
    saved, rows = value
    ctx = self.gateway.context.sample()
    if (saved.expires <= self.gateway.clock() or saved.session != _session_key(token) or saved.generation != generation or
        ctx.cp_raw != saved.cp_raw or not ctx.parked or not session_valid()):
      raise SettingsChanged('Settings recovery requires the same vehicle and offroad mode')
    for page, row in rows:
      if row not in self.gateway._state(page, ctx).rows or row_default(row, allow_inactive=True) is None:
        raise SettingsChanged('Saved settings or defaults changed')
    applied = []
    for page, original in rows:
      state = self.gateway.page(page, token, generation)
      with self.gateway.lock:
        fresh = self.gateway.views[state['view']].rows
      candidates = [(i, row) for i, row in enumerate(fresh) if row_default(row, allow_inactive=True) is not None and
                    row_default(row, allow_inactive=True).key == row_default(original, allow_inactive=True).key]
      if len(candidates) != 1:
        return {'saved': False, 'applied': applied, 'reason': 'Settings became unavailable', 'refresh': True}
      index, row = candidates[0]
      if equivalent(row.value, row.default_value):
        continue
      if row.value != original.value or row.default_value != original.default_value:
        return {'saved': False, 'applied': applied, 'reason': 'Saved settings changed during reset', 'refresh': True}
      try:
        pending = self.gateway.preview(state['view'], index, 0, token, generation, reset_default=True, recovery_default=True)
        saved = self.gateway.confirm(pending['intent'], token, generation, session_valid=session_valid)
      except (SettingsChanged, OSError, ValueError):
        return {'saved': False, 'applied': applied, 'reason': 'Saved settings changed during reset', 'refresh': True}
      if not saved:
        return {'saved': False, 'applied': applied, 'reason': 'Setting could not be reset', 'refresh': True}
      applied.append(original.label)
    return {'saved': True, 'applied': applied, 'refresh': True}
