"""Parse Uniden R4/R8/R9 radar detector BLE notifications.

Pure parsing with no Bluetooth or StarPilot dependencies; see README.md in
this directory for the planned connection and how it shares the adapter.
"""
from __future__ import annotations

from dataclasses import dataclass

# Detector GATT characteristics, all in its vendor service.
ALERT_UUID = '6eb675ab-8bd1-1b9a-7444-621e52ec6823'      # notify: active alerts
TELEMETRY_UUID = '6c290d2e-1c03-aca1-ab48-a9b908bae79e'  # notify: voltage, GPS and POI
RESPONSE_UUID = '5987b4ef-3bfa-76a8-e642-92933c31434f'   # notify: command replies
SETTINGS_UUID = '2d86686a-53dc-25b3-0c4a-f0e10c8dee20'   # notify: settings
WRITE_UUID = '2c86686a-53dc-25b3-0c4a-f0e10c8dee20'      # write without response: commands
# Sent after subscribing; the detector then starts streaming alerts and telemetry.
HANDSHAKE = (b'BTreqGURL:', b'BTreqGWAP:')
# Advertised names look like R4@1234 or R8W@1234.
NAME_KEYS = ('R1@', 'R3@', 'R4@', 'R5@', 'R7@', 'R8@', 'R8W@', 'R9@', 'R4W@', 'R9W@', 'UNIDEN')

DIRECTIONS = {'F': 'front', 'S': 'side', 'R': 'rear'}
MUTE_STATUS = {'1': 'not muted', '2': 'muted', '3': 'mute memory', '4': 'auto mute memory',
               '5': 'blocked mute', '6': 'quiet ride mute'}
LASER_GUNS = {
  '0': 'Generic Laser', '1': 'LTI 20/20', '2': 'Stalker', '3': 'RIEGL', '4': 'Laser Ally', '5': 'Kustom',
  '6': 'Atlanta', '7': 'Laveg', '8': 'SL700', '9': 'SCS-102', '10': 'TraffiPat', '11': 'Truspeed S',
  '12': 'Stealth', '13': 'TruCam', '14': 'XLR', '15': 'DragonEye Compact', '16': 'DragonEye Full-Size',
  '17': 'PoliScan', '18': 'Traffistar s350', '19': 'Vitronic Poliscan',
}


def uniden_name(name: str) -> bool:
  upper = str(name or '').strip().upper()
  return any(key in upper for key in NAME_KEYS)


def _text(payload: str | bytes | bytearray) -> str:
  return payload if isinstance(payload, str) else bytes(payload).decode('latin-1', errors='replace')


def _at(parts: list[str], index: int) -> str | None:
  if index < len(parts):
    return parts[index].strip() or None
  return None


def _int(value: str | None) -> int | None:
  try:
    return int(value)
  except (TypeError, ValueError):
    return None


def _float(value: str | None) -> float | None:
  try:
    return float(value)
  except (TypeError, ValueError):
    return None


@dataclass(frozen=True)
class PoiAlert:
  kind: str | None = None
  distance: int | None = None
  speed_limit: int | None = None


@dataclass(frozen=True)
class Telemetry:
  voltage: float | None = None
  poi: PoiAlert | None = None
  heading: str | None = None
  speed: int | None = None
  altitude: int | None = None
  gps_status: str | None = None
  warning: str | None = None
  scan_count: int | None = None
  wifi: str | None = None
  brightness: str | None = None
  raw: str = ''

  @property
  def gps_locked(self) -> bool:
    return self.gps_status == 'C'


def parse_telemetry(payload: str | bytes | bytearray) -> Telemetry:
  text = _text(payload)
  fields = text.split('&')
  poi = heading = speed = altitude = gps_status = None
  poi_field = _at(fields, 1)
  if poi_field and poi_field != '0':
    parts = poi_field.split(',')
    poi = PoiAlert(_at(parts, 0), _int(_at(parts, 1)), _int(_at(parts, 2)))
  gps = _at(fields, 2)
  if gps and gps != '0':
    parts = gps.split(',')
    heading, speed, altitude, gps_status = _at(parts, 0), _int(_at(parts, 1)), _int(_at(parts, 2)), _at(parts, 3)
  warning = _at(fields, 3)
  return Telemetry(voltage=_float(_at(fields, 0)), poi=poi, heading=heading, speed=speed, altitude=altitude,
                   gps_status=gps_status, warning=warning if warning != '0' else None, scan_count=_int(_at(fields, 4)),
                   wifi=_at(fields, 5), brightness=_at(fields, 6), raw=text)


@dataclass(frozen=True)
class Alert:
  band: str = ''
  strength: int | None = None
  raw_signal: int | None = None
  frequency_ghz: float | None = None
  laser_gun: str | None = None
  direction: str | None = None
  mute_code: str | None = None
  receive_mode: str | None = None
  alert_id: str | None = None
  raw: str = ''

  @property
  def direction_name(self) -> str:
    return DIRECTIONS.get(self.direction or '', self.direction or 'unknown')

  @property
  def mute_status(self) -> str:
    return MUTE_STATUS.get(self.mute_code or '', 'unknown')

  @property
  def is_muted(self) -> bool:
    return self.mute_code in ('2', '3', '4', '5', '6')

  @property
  def description(self) -> str:
    if self.laser_gun:
      return self.laser_gun
    if self.band in ('RT3', 'RT4'):
      return 'Gatso'
    if self.frequency_ghz is not None:
      return f'{self.frequency_ghz:g} GHz'
    return self.band or 'unknown'


def parse_alerts(payload: str | bytes | bytearray) -> list[Alert]:
  alerts = []
  for segment in _text(payload).split('&'):
    segment = segment.strip()
    if not segment or segment == '0':
      continue
    fields = segment.split(',')
    if _at(fields, 0) == '0':
      continue
    band = (_at(fields, 2) or '').upper()
    frequency = _at(fields, 5)
    alerts.append(Alert(
      band=band, strength=_int(_at(fields, 3)), raw_signal=_int(_at(fields, 4)),
      frequency_ghz=None if band == 'LASER' else _float(frequency),
      laser_gun=LASER_GUNS.get(frequency or '', f'unknown laser ({frequency})') if band == 'LASER' else None,
      direction=_at(fields, 6), mute_code=_at(fields, 7), receive_mode=_at(fields, 8), alert_id=_at(fields, 1), raw=segment,
    ))
  return alerts


def strongest(alerts: list[Alert], bands: frozenset[str] = frozenset({'KA', 'K', 'LASER', 'MRCD', 'POP'})) -> Alert | None:
  """The strongest threat in ``bands``, as the earlier radar daemon selected it."""
  threats = [alert for alert in alerts if alert.band in bands and (alert.strength or 0) > 0]
  return max(threats, key=lambda alert: alert.strength or 0) if threats else None
