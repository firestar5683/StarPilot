"""AAComma satellite acquisition tracking, read only while the map needs a fix."""

SATELLITE_WINDOW = 5.0


def acquisition_progress(satellites):
  return max(0.04, min(1.0, (satellites or 0) / 6))


class GpsAcquisition:
  def __init__(self, sm_factory=None):
    self._sm_factory = sm_factory
    self._sm = None
    self._by_source = {}
    self._external = None
    self.since = None

  def reset(self):
    self._by_source.clear()
    self._external = None
    self.since = None

  def update(self, now):
    if self.since is None:
      self.since = now
    if self._sm is None:
      if self._sm_factory is not None:
        self._sm = self._sm_factory()
      else:
        from openpilot.cereal import messaging
        self._sm = messaging.SubMaster(['gpsLocationExternal', 'qcomGnss'])
    sm = self._sm
    sm.update(0)
    if sm.updated['gpsLocationExternal'] and sm.valid['gpsLocationExternal']:
      self._external = (max(0, int(sm['gpsLocationExternal'].satelliteCount)), now)
    if sm.updated['qcomGnss'] and sm.valid['qcomGnss']:
      gnss = sm['qcomGnss']
      if gnss.which() == 'measurementReport':
        report = gnss.measurementReport
        tracked = sum(1 for sv in report.sv if int(getattr(sv.observationState, 'raw', sv.observationState)) in (4, 5))
        self._by_source[int(getattr(report.source, 'raw', report.source))] = (tracked, now)

  def satellites(self, now):
    if self._external is not None and 0 <= now - self._external[1] < SATELLITE_WINDOW:
      return self._external[0]
    recent = [count for count, at in self._by_source.values() if 0 <= now - at < SATELLITE_WINDOW]
    return sum(recent) if recent else None
