import cereal.messaging as messaging
from cereal import custom
from opendbc.car.structs import CarParams
from opendbc.car.hyundai.values import HyundaiFlags, HyundaiSafetyFlags
from panda import Panda
from openpilot.selfdrive.pandad import pandad as pandad_module
from openpilot.selfdrive.pandad.pandad import (
  EV9_LONG_PREINIT_H7_APP,
  EV9_LONG_PREINIT_LEGACY_STATUS_STRUCT,
  EV9_LONG_PREINIT_STATUS_STRUCT,
  EV9_LONG_PREINIT_STATUS_VERSION,
  EV9_LONG_PREINIT_TIMING_STRUCT,
  EV9_PREINIT_FLAG_BRIDGE_ACTIVE,
  EV9_PREINIT_IN_FLIGHT_STATES,
  EV9_PREINIT_STATE_ABORTED,
  EV9_PREINIT_STATE_ACTIVE,
  EV9_PREINIT_STATE_COLLECTING,
  ev9_long_preinit_active,
  ev9_long_preinit_flash_blocked,
  ev9_long_preinit_firmware_selected,
  ev9_long_preinit_must_preserve,
  ev9_long_preinit_reset_blocked,
  ev9_long_preinit_resident_signature,
  ev9_long_preinit_status_stable,
  get_ev9_long_preinit_status,
  get_ev9_long_preinit_panda,
  get_ignore_ignition_line,
  get_selected_firmware_name,
)


class FakeParams:
  def __init__(self, values):
    self.values = values

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get_int(self, key):
    return int(self.values.get(key, 0))

  def get(self, key, encoding=None):
    value = self.values.get(key)
    if encoding is not None and isinstance(value, bytes):
      return value.decode(encoding)
    return value


class FakePandaHandle:
  def __init__(self, pages):
    self.pages = pages
    self.read_counts = {}

  def controlRead(self, _request_type, request, page, _index, _length):
    assert request == 0xe9
    value = self.pages.get(page, b"")
    if isinstance(value, list):
      read_count = self.read_counts.get(page, 0)
      self.read_counts[page] = read_count + 1
      return value[min(read_count, len(value) - 1)]
    return value


class FakePanda:
  def __init__(self, pages):
    self._handle = FakePandaHandle(pages)


class FakeMcuConfig:
  def __init__(self, app_fn):
    self.app_fn = app_fn


class FakeMcuType:
  def __init__(self, app_fn):
    self.config = FakeMcuConfig(app_fn)


class FakeSelectionPanda:
  def __init__(self, internal, app_fn):
    self.internal = internal
    self.mcu_type = FakeMcuType(app_fn)

  def is_internal(self):
    return self.internal

  def get_mcu_type(self):
    return self.mcu_type


def ev9_preinit_v4_pages():
  status_values = [0] * 27
  status_values[0] = EV9_LONG_PREINIT_STATUS_VERSION
  status_values[1] = EV9_PREINIT_STATE_ACTIVE
  status_values[7] = 1
  status_values[13] = EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  status_values[22] = 120
  status_values[23] = 140
  status_values[26] = 180

  timing_values = [0] * 19
  timing_values[0] = EV9_LONG_PREINIT_STATUS_VERSION
  timing_values[1] = 1
  timing_values[2] = EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  timing_values[5] = 100
  timing_values[6] = 120
  timing_values[7] = 140
  timing_values[8] = 150
  timing_values[11] = 160
  return {
    0: EV9_LONG_PREINIT_STATUS_STRUCT.pack(*status_values),
    1: EV9_LONG_PREINIT_TIMING_STRUCT.pack(*timing_values),
  }


def ev9_preinit_params(**overrides):
  persistent_cp = CarParams(brand="hyundai", carFingerprint="KIA_EV9",
                            openpilotLongitudinalControl=True, pcmCruise=False,
                            flags=int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEERING |
                                      HyundaiFlags.CANFD_LKA_STEERING_ALT | HyundaiFlags.CANFD_ANGLE_STEERING),
                            carFw=[CarParams.CarFw(ecu=CarParams.Ecu.adas, address=0x730,
                                                  fwVersion=b"ev9-adas", brand="hyundai")])
  safety_configs = persistent_cp.init("safetyConfigs", 1)
  safety_configs[0].safetyModel = CarParams.SafetyModel.hyundaiCanfdEv9
  safety_configs[0].safetyParam = 0x495
  values = {
    "EV9LongPreinitPanda": True,
    "OpenpilotEnabledToggle": True,
    "AlphaLongitudinalEnabled": True,
    "CarParamsPersistent": persistent_cp.to_bytes(),
    "StarPilotCarParamsPersistent": custom.StarPilotCarParams.new_message().to_bytes(),
  }
  values.update(overrides)
  return FakeParams(values)


def test_ev9_long_preinit_firmware_selection():
  assert get_selected_firmware_name(EV9_LONG_PREINIT_H7_APP, False, False, False, True) == \
    "panda_h7_ev9_long_preinit.bin.signed"
  assert get_selected_firmware_name(EV9_LONG_PREINIT_H7_APP, True, False, False, True) == \
    "panda_h7_ev9_long_preinit.bin.signed"
  assert get_selected_firmware_name(EV9_LONG_PREINIT_H7_APP, False, True, False, True) == \
    "panda_h7_ev9_long_preinit_hkg_remote.bin.signed"
  assert get_selected_firmware_name(EV9_LONG_PREINIT_H7_APP, False, False, True, True) == \
    "panda_h7_ev9_long_preinit_can_ignition_only.bin.signed"
  assert get_selected_firmware_name(EV9_LONG_PREINIT_H7_APP, False, True, True, True) == \
    "panda_h7_ev9_long_preinit_hkg_remote_can_ignition_only.bin.signed"
  assert get_selected_firmware_name("panda.bin.signed", False, False, False, True) == "panda.bin.signed"

  assert ev9_long_preinit_firmware_selected(FakeSelectionPanda(True, EV9_LONG_PREINIT_H7_APP), True)
  assert not ev9_long_preinit_firmware_selected(FakeSelectionPanda(False, EV9_LONG_PREINIT_H7_APP), True)
  assert not ev9_long_preinit_firmware_selected(FakeSelectionPanda(True, "panda.bin.signed"), True)

  mixed_pandas = [
    FakeSelectionPanda(True, EV9_LONG_PREINIT_H7_APP),
    FakeSelectionPanda(False, EV9_LONG_PREINIT_H7_APP),
    FakeSelectionPanda(False, "panda.bin.signed"),
  ]
  assert [ev9_long_preinit_firmware_selected(panda, True) for panda in mixed_pandas] == [True, False, False]


def test_ev9_long_preinit_recognizes_resident_signature(monkeypatch, tmp_path):
  firmware_path = tmp_path / "panda_h7_ev9_long_preinit.bin.signed"
  firmware_path.write_bytes(b"firmware")
  monkeypatch.setattr(pandad_module, "FW_PATH", str(tmp_path))
  monkeypatch.setattr(Panda, "get_signature_from_firmware", lambda _path: b"resident-signature")

  assert ev9_long_preinit_resident_signature(b"resident-signature")
  assert not ev9_long_preinit_resident_signature(b"stock-signature")


def test_ev9_long_preinit_cereal_status_schema():
  msg = messaging.new_message("pandaStates", 1)
  status = msg.pandaStates[0].ev9LongPreinitStatus
  status.resident = True
  status.valid = True
  status.version = EV9_LONG_PREINIT_STATUS_VERSION
  status.state = EV9_PREINIT_STATE_ACTIVE
  status.flags = EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  status.communicationType = 1
  status.timingFlags = EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  status.sessionRequestUs = 100
  status.suppressionConfirmedUs = 200

  assert status.resident
  assert status.valid
  assert status.version == EV9_LONG_PREINIT_STATUS_VERSION
  assert status.flags == EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  assert status.timingFlags == EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  assert status.sessionRequestUs == 100
  assert status.suppressionConfirmedUs == 200


def test_ev9_long_preinit_raw_v4_status_pages():
  status = get_ev9_long_preinit_status(FakePanda(ev9_preinit_v4_pages()))
  assert status["state"] == EV9_PREINIT_STATE_ACTIVE
  assert status["flags"] == EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  assert status["outcome_us"] == 180
  assert status["timing_valid"]
  assert status["timing_flags"] == EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  assert status["session_request_us"] == 100
  assert status["comm_control_response_us"] == 150
  assert status["suppression_confirmed_us"] == 160


def test_ev9_long_preinit_uses_panda_python_v4_reader():
  panda = object.__new__(Panda)
  panda._handle = FakePandaHandle(ev9_preinit_v4_pages())
  status = Panda.get_ev9_long_preinit_status(panda)
  assert status["valid"]
  assert status["version"] == EV9_LONG_PREINIT_STATUS_VERSION
  assert status["flags"] == EV9_PREINIT_FLAG_BRIDGE_ACTIVE
  assert status["timing_valid"]
  assert status["suppression_confirmed_us"] == 160


def test_ev9_long_preinit_rejects_incoherent_timing_pages():
  pages = ev9_preinit_v4_pages()
  changed_status = list(EV9_LONG_PREINIT_STATUS_STRUCT.unpack(pages[0]))
  changed_status[1] = 5
  pages[0] = [pages[0], EV9_LONG_PREINIT_STATUS_STRUCT.pack(*changed_status)]

  status = get_ev9_long_preinit_status(FakePanda(pages))
  assert not status["valid"]
  assert not status["timing_valid"]


def test_ev9_long_preinit_raw_legacy_status_preserves_active_owner():
  status_values = [0] * 26
  status_values[0] = 3
  status_values[1] = EV9_PREINIT_STATE_ACTIVE
  status = get_ev9_long_preinit_status(FakePanda({
    0: EV9_LONG_PREINIT_LEGACY_STATUS_STRUCT.pack(*status_values),
  }))
  assert status["version"] == 3
  assert status["flags"] == 0
  assert ev9_long_preinit_must_preserve(status)


def test_ev9_long_preinit_requires_all_persistent_gates():
  assert get_ev9_long_preinit_panda(ev9_preinit_params())

  for key in ("EV9LongPreinitPanda", "OpenpilotEnabledToggle", "AlphaLongitudinalEnabled"):
    assert not get_ev9_long_preinit_panda(ev9_preinit_params(**{key: False}))

  assert not get_ev9_long_preinit_panda(ev9_preinit_params(StarPilotCarParamsPersistent=None))
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(StarPilotCarParamsPersistent=b""))
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(StarPilotCarParamsPersistent=b"not-capnp"))
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(CarParamsPersistent=None))
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(
    CarParamsPersistent=CarParams(brand="hyundai", carFingerprint="HYUNDAI_IONIQ_6",
                                  openpilotLongitudinalControl=True).to_bytes()))
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(
    CarParamsPersistent=CarParams(brand="hyundai", carFingerprint="KIA_EV9",
                                  openpilotLongitudinalControl=False, pcmCruise=True).to_bytes()))
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(
    CarParamsPersistent=CarParams(brand="hyundai", carFingerprint="KIA_EV9",
                                  openpilotLongitudinalControl=True, pcmCruise=False).to_bytes()))

  with CarParams.from_bytes(ev9_preinit_params().get("CarParamsPersistent")) as reader:
    wrong_model = reader.as_builder()
    wrong_model.safetyConfigs[0].safetyModel = CarParams.SafetyModel.hyundaiCanfd
    wrong_model_bytes = wrong_model.to_bytes()
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(CarParamsPersistent=wrong_model_bytes))

  with CarParams.from_bytes(ev9_preinit_params().get("CarParamsPersistent")) as reader:
    wrong_param = reader.as_builder()
    wrong_param.safetyConfigs[0].safetyParam = int(wrong_param.safetyConfigs[0].safetyParam) | \
      int(HyundaiSafetyFlags.CAMERA_SCC)
    wrong_param_bytes = wrong_param.to_bytes()
  assert not get_ev9_long_preinit_panda(ev9_preinit_params(CarParamsPersistent=wrong_param_bytes))

  with CarParams.from_bytes(ev9_preinit_params().get("CarParamsPersistent")) as reader:
    optional_aol = reader.as_builder()
    optional_aol.safetyConfigs[0].safetyParam |= 0x800
    optional_aol_bytes = optional_aol.to_bytes()
  assert get_ev9_long_preinit_panda(ev9_preinit_params(CarParamsPersistent=optional_aol_bytes))


def test_ignore_ignition_line_is_gm_only():
  assert get_ignore_ignition_line(FakeParams({"CarMake": "gm", "IgnoreIgnitionLine": True}))
  assert not get_ignore_ignition_line(FakeParams({"CarMake": "hyundai", "IgnoreIgnitionLine": True}))
  assert not get_ignore_ignition_line(FakeParams({"CarMake": "gm", "IgnoreIgnitionLine": False}))


def test_ev9_long_preinit_does_not_fall_back_to_previous_route():
  params = ev9_preinit_params(
    CarParamsPersistent=CarParams(brand="mock", carFingerprint="MOCK").to_bytes(),
    CarParamsPrevRoute=CarParams(brand="hyundai", carFingerprint="KIA_EV9").to_bytes(),
  )
  assert not get_ev9_long_preinit_panda(params)


def test_ev9_long_preinit_preservation_states_and_flags():
  collecting = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_COLLECTING, "flags": 0}
  aborted = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_ABORTED, "flags": 0}
  active = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_ACTIVE, "flags": 0}

  assert not ev9_long_preinit_must_preserve(collecting)
  assert not ev9_long_preinit_must_preserve(aborted)
  assert ev9_long_preinit_active(active)
  assert ev9_long_preinit_must_preserve(active)
  for state in EV9_PREINIT_IN_FLIGHT_STATES:
    assert ev9_long_preinit_must_preserve({"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": state, "flags": 0})
  assert ev9_long_preinit_must_preserve({
    "version": EV9_LONG_PREINIT_STATUS_VERSION,
    "state": EV9_PREINIT_STATE_ABORTED,
    "flags": EV9_PREINIT_FLAG_BRIDGE_ACTIVE,
  })
  assert ev9_long_preinit_must_preserve({
    "version": 3,
    "state": EV9_PREINIT_STATE_ABORTED,
    "flags": 0,
    "comm_control_us": 1,
  })


def test_ev9_long_preinit_blocks_unsafe_flash():
  collecting = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_COLLECTING, "flags": 0}
  active = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_ACTIVE, "flags": 0}
  aborted = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_ABORTED, "flags": 0}

  assert ev9_long_preinit_flash_blocked(active, firmware_selected=False, ignition_on=False)
  assert ev9_long_preinit_flash_blocked(aborted, firmware_selected=True, ignition_on=True)
  # A disarmed resident image is still mutation-sensitive until the vehicle is
  # verified off, even in a nominally safe/terminal firmware state.
  assert ev9_long_preinit_flash_blocked(collecting, firmware_selected=False, ignition_on=True)
  assert ev9_long_preinit_flash_blocked(aborted, firmware_selected=False, ignition_on=True)
  assert ev9_long_preinit_flash_blocked(None, firmware_selected=False, ignition_on=True, resident_firmware=True)
  assert ev9_long_preinit_flash_blocked(None, firmware_selected=False, ignition_on=False, resident_firmware=True)
  assert ev9_long_preinit_flash_blocked(
    collecting, firmware_selected=False, ignition_on=False, status_stable=False,
  )
  assert not ev9_long_preinit_flash_blocked(aborted, firmware_selected=True, ignition_on=False)
  assert not ev9_long_preinit_flash_blocked(None, firmware_selected=False, ignition_on=True)

  assert ev9_long_preinit_status_stable(collecting, dict(collecting))
  assert not ev9_long_preinit_status_stable(collecting, active)


def test_ev9_long_preinit_blocks_cold_boot_reset():
  collecting = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_COLLECTING, "flags": 0}
  active = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_ACTIVE, "flags": 0}
  aborted = {"version": EV9_LONG_PREINIT_STATUS_VERSION, "state": EV9_PREINIT_STATE_ABORTED, "flags": 0}

  assert ev9_long_preinit_reset_blocked(collecting, firmware_selected=True)
  assert ev9_long_preinit_reset_blocked(collecting, firmware_selected=False, resident_firmware=True)
  assert ev9_long_preinit_reset_blocked(
    collecting, firmware_selected=False, ignition_on=False, status_stable=False,
  )
  assert ev9_long_preinit_reset_blocked(active, firmware_selected=False)
  assert not ev9_long_preinit_reset_blocked(aborted, firmware_selected=False)
