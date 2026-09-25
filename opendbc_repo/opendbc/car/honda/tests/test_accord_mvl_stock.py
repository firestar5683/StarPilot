import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.honda.accord_mvl_stock import qualified
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC


def final_cp(alpha=False, release=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x1A3] = 8
  return CarInterface.get_params(CAR.HONDA_ACCORD_11G, fingerprint, [], alpha, release, False)


@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (True, True)))
def test_factory_keeps_stock_acc_without_long_handover(alpha, release):
  cp = final_cp(alpha, release)
  assert cp.safetyConfigs[0].safetyParam == 80
  assert cp.pcmCruise and not cp.openpilotLongitudinalControl
  assert not cp.alphaLongitudinalAvailable
  assert qualified(cp)
  assert CarInterface(cp).CC.accord_mvl_stock is not None
  for word in (16, 18, 82, 112, 114):
    cp.safetyConfigs[0].safetyParam = word
    assert not qualified(cp)
  cp = final_cp()
  cp.alternativeExperience = 32
  assert not qualified(cp)


def test_real_parser_controller_camera_button_cadence_and_override_exclusion():
  cp = final_cp()
  ci = CarInterface(cp)
  ci.update([])
  packer = CANPacker(DBC[CAR.HONDA_ACCORD_11G][Bus.pt])
  parser = CANParser(DBC[CAR.HONDA_ACCORD_11G][Bus.pt], [("SCM_BUTTONS", 0)], 2)
  pulses = []
  for frame in range(620):
    now = 1_000_000_000 + frame * 10_000_000
    setting = 1 if 530 <= frame < 540 else 0
    ambient = frame % 256
    source = packer.make_can_msg("SCM_BUTTONS", 0, {
      "CRUISE_BUTTONS": 0, "CRUISE_SETTING": setting, "AMBIENT_LIGHT_MAYBE": ambient})
    camera_hud = packer.make_can_msg("LKAS_HUD", 2, {"LKAS_READY": 1})
    ci.update((now, [source, camera_hud]))
    assert ci.CS.scm_ambient_light == ambient
    assert ci.CS.lkas_hud["LKAS_READY"] == 1
    control = structs.CarControl(enabled=20 <= frame < 610)
    control.cruiseControl.cancel = frame == 560
    control.cruiseControl.resume = frame == 564
    _, messages = ci.apply(control.as_reader(), now)
    camera = [message for message in messages if message[0] == 0x296 and message[2] == 2]
    expected = control.enabled and frame % 4 == 0 and not control.cruiseControl.cancel and not control.cruiseControl.resume
    assert len(camera) == int(expected)
    assert not any(message[0] in (0x1DF, 0x1EF, 0x310, 0x18DAB0F1, 0x6CD5558, 0x6CD5559,
                                  0xF31AA52, 0xF31AA5C, 0x1A45AA4E) for message in messages)
    if camera:
      parser.update((now, camera))
      assert parser.vl["SCM_BUTTONS"]["AMBIENT_LIGHT_MAYBE"] == ambient
      assert parser.vl["SCM_BUTTONS"]["CRUISE_BUTTONS"] == 0
      actual_setting = parser.vl["SCM_BUTTONS"]["CRUISE_SETTING"]
      if actual_setting == 1:
        pulses.append(frame)
      if setting == 1 and frame > 508:
        assert actual_setting == 0
  assert pulses == [500, 504, 508]


@pytest.mark.parametrize("alpha,release", ((False, False), (True, False), (True, True)))
def test_actual_card_publication_and_disabled_controls_remains_stock80(alpha, release, monkeypatch):
  from opendbc.car.honda.tests.test_stock_startup import exercise_startup
  exercise_startup(CAR.HONDA_ACCORD_11G, alpha, release, False, 80, monkeypatch)
