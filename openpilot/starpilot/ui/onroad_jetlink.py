"""Jetlink status card shared by the native and Android Auto screens."""
import pyray as rl

from openpilot.starpilot.models.jetlink_status import JetlinkStatus
from openpilot.starpilot.ui.onroad_customization import JETLINK_SIZE, JETLINK_WIDGET
from openpilot.starpilot.ui.presentation import FontRole

# 'prepared' onroad is modeld still loading: a join that failed reads 'failed' (jetlink_status.join_failed)
LABELS = {'off': 'JetLink off', 'active': 'Remote model active', 'waiting': 'Ready to switch', 'prepared': 'Starting model',
          'preparing': 'Device connected', 'reconnecting': 'Reconnecting', 'failed': 'JetLink failed',
          'connecting': 'Device connected', 'detected': 'Device detected', 'disconnected': 'No device connected',
          'unavailable': 'JetLink unavailable'}
DETAILS = {'off': 'Local model', 'waiting': 'Local model • waiting to disengage', 'prepared': 'Local model • starting remote model',
           'preparing': 'Local model • waiting for model', 'reconnecting': 'Local model • restoring connection',
           'failed': 'Local model • check JetLink', 'connecting': 'Local model • waiting for app',
           'detected': 'Local model • waiting for USB', 'disconnected': 'Local model • connect device',
           'unavailable': 'Local model • check JetLink'}
STAGES = {'download': 'Downloading model', 'downloading': 'Downloading model', 'upload': 'Sending model',
          'patch': 'Preparing model', 'parse': 'Reading model', 'convert': 'Converting model',
          'compile': 'Compiling model', 'build': 'Building model', 'load': 'Loading model', 'warm': 'Warming up model',
          'finding_model': 'Finding model', 'model_missing': 'Model not downloaded',
          'download_stalled': 'Download stalled', 'downloaded_waiting_host': 'Waiting for device'}
REASONS = {'reconnect_lost': 'link lost', 'reconnect_cable': 'link keeps dropping, check cable',
           'reconnect_behind': 'device too slow', 'reconnect_load_failed': 'model failed to load',
           'reconnect_bad_output': 'bad model output'}


def status_lines(status):
  step = LABELS.get(status.state, 'JetLink unavailable')
  detail = DETAILS.get(status.state, 'Local model • check JetLink')
  if status.state in ('preparing', 'connecting') and status.stage in STAGES:
    step = STAGES[status.stage]
    detail = 'Local model • device connected'
    if status.percent is not None:
      detail = f'Local model • {status.percent}% transferred'
  if status.state == 'reconnecting' and status.stage in REASONS:
    detail = REASONS[status.stage]
  if status.state != 'active':
    step = f"{step} • {detail.removeprefix('Local model • ')}"
  return 'JetLink', step


GREEN = rl.Color(70, 200, 110, 255)
ORANGE = rl.Color(255, 150, 60, 255)
ACCENT = rl.Color(199, 174, 247, 255)
GRAY = rl.Color(140, 136, 152, 255)
TEXT = rl.Color(245, 242, 252, 255)
MUTED = rl.Color(184, 178, 200, 255)
DOT = {'off': GRAY, 'active': GREEN, 'waiting': ACCENT, 'failed': ORANGE, 'unavailable': ORANGE, 'disconnected': GRAY}


class JetlinkStatusWidget:
  def __init__(self, fonts):
    self.fonts = fonts
    self.status = JetlinkStatus()

  def _fit(self, text, role, size, width):
    measured = self.fonts.measure(text, role, size)
    return size * width / measured.width if measured.width > width else size

  def render(self, state):
    placed = state.customization['layouts']['large'].get(JETLINK_WIDGET)
    status = self.status
    if not placed or not placed['enabled'] or state.alert.size != 'none':
      return
    if placed.get('hideDisconnected', False) and status.state in ('off', 'disconnected'):
      return
    rect = rl.Rectangle(placed['x'], placed['y'], *JETLINK_SIZE)
    h = rect.height
    rl.draw_rectangle_rounded(rect, 1.0, 16, rl.Color(15, 13, 23, round(235 * placed.get('opacity', 85) / 100)))
    rl.draw_circle_v(rl.Vector2(rect.x + h / 2, rect.y + h / 2), 9, DOT.get(status.state, ACCENT))
    right = rect.x + rect.width - 30
    if status.state == 'active' and status.latency_ms is not None:
      value, unit = f'{status.latency_ms:.1f}', 'ms'
      unit_w = self.fonts.measure(unit, FontRole.NORMAL, 22).width
      value_w = self.fonts.measure(value, FontRole.SEMI_BOLD, 34).width
      self.fonts.draw(unit, FontRole.NORMAL, 22, right - unit_w, rect.y + h / 2 - 6, MUTED)
      right -= unit_w + 8
      self.fonts.draw(value, FontRole.SEMI_BOLD, 34, right - value_w, rect.y + h / 2 - 18, TEXT)
      right -= value_w + 16
    left = rect.x + h - 6
    width = right - left
    title, detail = status_lines(status)
    self.fonts.draw(title, FontRole.SEMI_BOLD, self._fit(title, FontRole.SEMI_BOLD, 28, width), left, rect.y + 12, TEXT)
    self.fonts.draw(detail, FontRole.NORMAL, self._fit(detail, FontRole.NORMAL, 22, width), left, rect.y + 46, MUTED)
