"""Onroad GNSS health readout.

Built to measure RF desense from the external GPU's USB-C link: with the eGPU unplugged the
receiver demodulates satellite time from ~93% of tracked satellites and fixes immediately, and
with it plugged in that collapses to 0% while the tracked satellite count actually rises. Raw
satellite counts are therefore misleading on their own - the demodulation rate and C/No are what
show whether a cable, ferrite or antenna placement change helped.
"""
import pyray as rl

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight

WIDTH = 300
HEIGHT = 150
MARGIN = 30
PADDING = 14
TITLE_SIZE = 26
ROW_SIZE = 32

_BG = rl.Color(0, 0, 0, 180)
_LABEL = rl.Color(255, 255, 255, 140)
_GOOD = rl.Color(34, 197, 94, 255)
_WARN = rl.Color(234, 179, 8, 255)
_BAD = rl.Color(239, 68, 68, 255)

# Demodulation rate thresholds. Anything under ~40% has never produced a fix in logged drives.
SAT_TIME_GOOD = 60.0
SAT_TIME_WARN = 25.0

# Carrier-to-noise, in the modem's raw units (~2550 average with the eGPU unplugged and a clean
# fix; the desensed drives report 0 for every satellite, so any non-zero reading is progress).
CNO_GOOD = 2000.0
CNO_WARN = 800.0


def _grade(value: float, good: float, warn: float) -> rl.Color:
  if value >= good:
    return _GOOD
  if value >= warn:
    return _WARN
  return _BAD


class GnssHealth:
  """Bottom-right live GNSS quality readout."""

  def __init__(self):
    self._font = gui_app.font(FontWeight.SEMI_BOLD)
    self._sat_time_pct = 0.0
    self._cno = 0.0
    self._gps_sv = 0
    self._glonass_sv = 0
    self._has_fix = False

  def _update(self) -> None:
    sm = ui_state.sm

    # qcomgpsd publishes gpsLocation; gpsLocationExternal is only used by ublox/car-GPS devices,
    # so checking that socket alone leaves hasFix stuck False on this hardware.
    for service in ("gpsLocation", "gpsLocationExternal"):
      if sm.valid.get(service, False) and sm.recv_frame[service] > 0:
        self._has_fix = sm[service].hasFix
        break

    # qcomGnss multiplexes measurement/drMeasurement/svPoly, so only act on the variant that
    # carries per-satellite status rather than returning early on the others.
    if not sm.valid.get("qcomGnss", False):
      return

    gnss = sm["qcomGnss"]
    if gnss.which() != "measurementReport":
      return

    report = gnss.measurementReport
    svs = list(report.sv)
    source = str(report.source)

    # The two constellations arrive as separate reports at ~1Hz each. satelliteTimeIsKnown is only
    # meaningful for GPS here - the modem leaves it clear on GLONASS satellites and reports their
    # validity through the glonass* bits instead - so tracking one shared percentage made the
    # readout flip between 100% and 0% twice a second.
    is_glonass = "glonass" in source
    if is_glonass:
      self._glonass_sv = len(svs)
    else:
      self._gps_sv = len(svs)

    if svs and not is_glonass:
      known = sum(1 for sv in svs if sv.measurementStatus.satelliteTimeIsKnown)
      self._sat_time_pct = 100.0 * known / len(svs)

    if svs:
      noise = [sv.carrierNoise for sv in svs if sv.carrierNoise > 0]
      if noise:
        self._cno = sum(noise) / len(noise)

  def render(self, bounds: rl.Rectangle) -> None:
    self._update()

    x = bounds.x + bounds.width - WIDTH - MARGIN
    y = bounds.y + bounds.height - HEIGHT - MARGIN
    rect = rl.Rectangle(x, y, WIDTH, HEIGHT)
    rl.draw_rectangle_rounded(rect, 0.12, 10, _BG)

    tx = int(x + PADDING)
    ty = int(y + PADDING)

    rl.draw_text_ex(self._font, "GNSS", rl.Vector2(tx, ty), TITLE_SIZE, 0, _LABEL)
    fix_text = "FIX" if self._has_fix else "NO FIX"
    fix_color = _GOOD if self._has_fix else _BAD
    rl.draw_text_ex(self._font, fix_text, rl.Vector2(int(x + WIDTH - PADDING - 90), ty),
                    TITLE_SIZE, 0, fix_color)

    ty += 34
    rl.draw_text_ex(self._font, "time G", rl.Vector2(tx, ty), ROW_SIZE, 0, _LABEL)
    rl.draw_text_ex(self._font, f"{self._sat_time_pct:.0f}%", rl.Vector2(tx + 120, ty),
                    ROW_SIZE, 0, _grade(self._sat_time_pct, SAT_TIME_GOOD, SAT_TIME_WARN))

    ty += 36
    rl.draw_text_ex(self._font, "C/No", rl.Vector2(tx, ty), ROW_SIZE, 0, _LABEL)
    rl.draw_text_ex(self._font, f"{self._cno:.0f}", rl.Vector2(tx + 120, ty),
                    ROW_SIZE, 0, _grade(self._cno, CNO_GOOD, CNO_WARN))

    ty += 36
    rl.draw_text_ex(self._font, "sats", rl.Vector2(tx, ty), ROW_SIZE, 0, _LABEL)
    rl.draw_text_ex(self._font, f"{self._gps_sv}G {self._glonass_sv}R",
                    rl.Vector2(tx + 120, ty), ROW_SIZE, 0, rl.WHITE)
