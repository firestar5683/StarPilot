"""Navigation-only action owner for the projected Home and Work widgets."""
import time

from openpilot.starpilot.navigation.owner import NavigationOwner
from openpilot.starpilot.system.android_auto.projection_layout import FAVORITE_WIDGETS, FAVORITE_SIZE
from openpilot.starpilot.ui.onroad_customization import widget_order


class ProjectionFavorites:
  def __init__(self, authorized, owner=None):
    self.authorized = authorized
    self.owner = owner if owner is not None else NavigationOwner()
    self.document = None
    self.error = ''
    self._read_at = float('-inf')
    self._press = None

  def refresh(self, *, force=False):
    now = time.monotonic()
    if not force and now - self._read_at < 1:
      return
    self._read_at = now
    try:
      self.document = self.owner.read()
    except (OSError, ValueError):
      self.document = None
      self.cancel()

  def action(self, key):
    doc = self.document
    if doc is None or key not in FAVORITE_WIDGETS:
      return None
    label = key.removeprefix('nav_')
    place = next((row for row in doc['favorites'] if row.get('label') == label), None)
    if place is None:
      return None
    active = doc['destination'] is not None and doc['destination']['id'] == place['id']
    if not active and not (doc['enabled'] and doc['token']):
      return None
    return ('end' if active else 'start', doc['revision'], place)

  @staticmethod
  def bounds(key, state):
    if state.alert.size != 'none':
      return None
    placed = state.customization['layouts']['large'].get(key)
    return placed if placed is not None and placed['enabled'] else None

  def hit(self, x, y, state):
    order = state.customization.get('widgetOrder', {}).get('large')
    if order is None:
      order = [*widget_order(state.customization, 'large'), *FAVORITE_WIDGETS]
    for key in reversed(order):
      if key in FAVORITE_WIDGETS and (placed := self.bounds(key, state)) is not None:
        if placed['x'] <= x < placed['x'] + FAVORITE_SIZE[0] and placed['y'] <= y < placed['y'] + FAVORITE_SIZE[1]:
          return key
    return None

  def touch(self, kind, x, y, state, drive):
    if kind == 'cancel' or not self.authorized():
      self.cancel()
      return
    if kind == 'down':
      self.cancel()
      self.refresh(force=True)
      key = self.hit(x, y, state)
      if key is not None and (action := self.action(key)) is not None:
        self.error = ''
        self._press = (key, x, y, action, drive)
      return
    if self._press is None:
      return
    key, px, py, action, pressed_drive = self._press
    if abs(x - px) > 15 or abs(y - py) > 15 or drive != pressed_drive or self.hit(x, y, state) != key:
      self.cancel()
      return
    if kind != 'up':
      return
    self.cancel()
    # A changed destination or relabeled favorite must never turn a held tap
    # into a different command. The owner's revision check covers concurrent writers.
    self.refresh(force=True)
    if self.action(key) != action:
      return
    command, revision, place = action
    def authorized():
      return self.authorized() and self.bounds(key, state) is not None
    try:
      if command == 'end':
        self.owner.clear(revision, authorized)
      else:
        self.owner.select(place, revision, authorized)
    except (OSError, ValueError, PermissionError):
      self.error = 'Try again'
    self.refresh(force=True)

  def cancel(self):
    self._press = None

  def close(self):
    self.cancel()
    self.owner.close()
