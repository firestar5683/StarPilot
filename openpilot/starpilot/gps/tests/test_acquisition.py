from types import SimpleNamespace as NS

from openpilot.starpilot.gps.acquisition import GpsAcquisition, acquisition_progress


class GnssMaster:
  def __init__(self):
    self.updated = {'gpsLocationExternal': False, 'qcomGnss': False}
    self.valid = {'gpsLocationExternal': True, 'qcomGnss': True}
    self.messages = {}

  def update(self, _timeout):
    pass

  def __getitem__(self, key):
    return self.messages[key]

  def measurement(self, source, states):
    self.updated = {'gpsLocationExternal': False, 'qcomGnss': True}
    self.messages['qcomGnss'] = NS(which=lambda: 'measurementReport',
                                  measurementReport=NS(source=source, sv=[NS(observationState=state) for state in states]))


def test_qualcomm_counts_only_tracked_satellites_and_expires_each_constellation():
  sm = GnssMaster()
  acquisition = GpsAcquisition(sm_factory=lambda: sm)
  acquisition.update(10)
  assert acquisition.satellites(10) is None and acquisition.since == 10
  sm.measurement(0, [5, 5, 4, 1, 0])
  acquisition.update(11)
  sm.measurement(1, [5, 2])
  acquisition.update(12)
  assert acquisition.satellites(12) == 4
  assert acquisition.satellites(16.5) == 1
  assert acquisition.satellites(17) is None


def test_ublox_preferred_count_expiry_invalid_reports_and_reset():
  sm = GnssMaster()
  acquisition = GpsAcquisition(sm_factory=lambda: sm)
  sm.measurement(0, [5, 4, 0])
  acquisition.update(10)
  sm.updated = {'gpsLocationExternal': True, 'qcomGnss': False}
  sm.messages['gpsLocationExternal'] = NS(satelliteCount=9)
  acquisition.update(11)
  assert acquisition.satellites(11) == 9
  sm.valid['gpsLocationExternal'] = False
  acquisition.update(15)
  assert acquisition.satellites(16) is None
  acquisition.reset()
  assert acquisition.since is None and acquisition.satellites(11) is None


def test_progress_matches_aacomma():
  assert acquisition_progress(None) == acquisition_progress(0) == .04
  assert acquisition_progress(3) == .5
  assert acquisition_progress(6) == acquisition_progress(12) == 1


def test_qualcomm_reads_real_capnp_enums():
  from openpilot.cereal import log
  gnss = log.QcomGnss.new_message()
  report = gnss.init('measurementReport')
  report.source = 'glonass'
  satellites = report.init('sv', 3)
  for satellite, state in zip(satellites, ('track', 'trackVerify', 'search'), strict=True):
    satellite.observationState = state
  sm = GnssMaster()
  sm.updated['qcomGnss'] = True
  sm.messages['qcomGnss'] = gnss
  acquisition = GpsAcquisition(sm_factory=lambda: sm)
  acquisition.update(10)
  assert acquisition.satellites(10) == 2
