from dataclasses import replace

from openpilot.starpilot.conditional_mode.policy import Authority, ConditionalModePolicy, ManualIntent, ModeChoice, SceneEvidence
from openpilot.starpilot.conditional_mode.stop import StopLightDetector
from openpilot.starpilot.conditional_mode.tests.test_stop import frame


def prime():
  detector = StopLightDetector()
  for tick in range(30):
    result = detector.step(frame(tick))
  assert result.light_detected and detector.committed
  return detector


def test_acquired_stop_survives_fresh_invalid_geometry_until_valid_clear():
  detector = prime()
  for tick in range(30, 140):
    result = detector.step(frame(tick, horizon=None, speed=4.27))
    assert result.light_detected and detector.committed
  for tick in range(140, 160):
    result = detector.step(frame(tick, horizon=192., speed=4.27))
  assert not result.light_detected and not detector.committed


def test_traffic_and_turn_cannot_abandon_short_committed_stop():
  for changes in ({'traffic': True}, {'left': True, 'steering': 45.}):
    detector = prime()
    for tick in range(30, 140):
      result = detector.step(frame(tick, horizon=6.684, speed=4.27, **changes))
      assert result.light_detected and detector.committed


def test_unknown_source_and_cold_invalid_geometry_cannot_authorize_commit():
  detector = StopLightDetector()
  assert detector.step(frame(0, horizon=None)).light_detected is None
  assert not detector.committed
  detector = prime()
  assert detector.step(replace(frame(30), traffic_mode=None)).light_detected is None
  assert detector.committed
  assert not detector.standstill_committed


def test_manual_chill_and_personality_mode_change_do_not_override_committed_stop():
  policy = ConditionalModePolicy()
  authority = Authority(True, True, False, True, True, True)
  for tick, choice in enumerate((ModeChoice.CEM, ModeChoice.CCM, ModeChoice.CEM)):
    now = 100. + tick * .05
    scene = SceneEvidence(observed_mono_s=now, speed_mps=4.27, committed_stop=True)
    result = policy.step(now, choice, ManualIntent.FORCE_CHILL, authority, scene)
    assert result.requested_experimental and result.reason.value == 'cem_stop'
  scene = replace(scene, observed_mono_s=now+.05, committed_stop=False)
  result = policy.step(now+.05, ModeChoice.CEM, ManualIntent.FORCE_CHILL, authority, scene)
  assert not result.requested_experimental and result.reason.value == 'manual_chill'


def test_pedal_override_releases_acquired_stop_without_authority_recreation():
  detector = prime()
  result = detector.step(frame(30, horizon=6.684, speed=4.27, pedal=True))
  assert not result.light_detected and not detector.committed


def test_standstill_commit_survives_unknowns_and_requires_continuous_clear_evidence():
  detector = prime()
  detector.step(frame(30, speed=0., standstill=True, horizon=6., model_should_stop=True))
  assert detector.standstill_committed
  for tick in range(31, 45):
    observation = detector.step(replace(frame(tick), traffic_mode=None))
    assert observation.light_detected is None
    assert detector.standstill_committed
  for tick in range(45, 65):
    detector.step(frame(tick, speed=0., standstill=True, horizon=192., model_should_stop=True))
    assert detector.standstill_committed
  for tick in range(65, 71):
    detector.step(frame(tick, speed=0., standstill=True, horizon=192., model_should_stop=False))
  detector.step(replace(frame(71), traffic_mode=None))
  for tick in range(72, 79):
    detector.step(frame(tick, speed=0., standstill=True, horizon=192., model_should_stop=False))
    assert detector.standstill_committed  # Unknown time contributes no clear dwell.
  for tick in range(79, 86):
    detector.step(frame(tick, speed=0., standstill=True, horizon=192., model_should_stop=False))
  assert not detector.committed and not detector.standstill_committed
