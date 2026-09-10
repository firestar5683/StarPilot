from itertools import product
from types import SimpleNamespace

from cereal import car
import pytest

from openpilot.selfdrive.pandad import pandad


class VehicleParams:
  def __init__(self, **values):
    self.values = values

  def get(self, key):
    return self.values.get(key)

  def get_bool(self, key):
    return bool(self.get(key))


def car_params(brand="tesla", fingerprint="TESLA_MODEL_3"):
  return car.CarParams.new_message(brand=brand, carFingerprint=fingerprint).to_bytes()


@pytest.mark.parametrize("h7,ignore,gm,hkg", list(product([False, True], repeat=4)))
def test_tesla_variant_overrides_stale_other_make_toggles(h7, ignore, gm, hkg):
  app_fn = "panda_h7.bin.signed" if h7 else "panda.bin.signed"
  expected = {
    (False, False): "panda_tesla_wake.bin.signed",
    (False, True): "panda_tesla_wake_can_ignition_only.bin.signed",
    (True, False): "panda_h7_tesla_wake.bin.signed",
    (True, True): "panda_h7_tesla_wake_can_ignition_only.bin.signed",
  }[h7, ignore]
  assert pandad.get_selected_firmware_name(app_fn, gm, hkg, ignore, tesla_wake=True) == expected


@pytest.mark.parametrize("gm,hkg,ignore,expected", [
  (False, False, False, "panda.bin.signed"),
  (False, False, True, "panda_can_ignition_only.bin.signed"),
  (True, False, False, "panda_remote.bin.signed"),
  (True, False, True, "panda_remote_can_ignition_only.bin.signed"),
  (False, True, False, "panda_hkg_remote.bin.signed"),
  (False, True, True, "panda_hkg_remote_can_ignition_only.bin.signed"),
  (True, True, False, "panda_hkg_remote.bin.signed"),
  (True, True, True, "panda_hkg_remote_can_ignition_only.bin.signed"),
])
@pytest.mark.parametrize("h7", [False, True])
def test_existing_firmware_selection_unchanged(gm, hkg, ignore, expected, h7):
  app_fn = "panda_h7.bin.signed" if h7 else "panda.bin.signed"
  if h7:
    expected = expected.replace("panda", "panda_h7", 1)
  assert pandad.get_selected_firmware_name(app_fn, gm, hkg, ignore) == expected


@pytest.mark.parametrize("values,expected", [
  ({}, False),
  ({"TeslaWakeOnCAN": True}, False),
  ({"TeslaWakeOnCAN": True, "CarMake": "Tesla"}, False),
  ({"CarParamsPersistent": car_params()}, False),
  ({"TeslaWakeOnCAN": True, "CarParamsPersistent": car_params()}, True),
  ({"TeslaWakeOnCAN": True, "CarMake": b"Tesla", "CarParamsPersistent": car_params(fingerprint="TESLA_MODEL_Y")}, True),
  ({"TeslaWakeOnCAN": True, "CarMake": "Toyota", "CarParamsPersistent": car_params()}, False),
  ({"TeslaWakeOnCAN": True, "CarModel": "TESLA_MODEL_X", "CarParamsPersistent": car_params()}, False),
  ({"TeslaWakeOnCAN": True, "CarParams": car_params("toyota", "TOYOTA_PRIUS"), "CarParamsPersistent": car_params()}, False),
  ({"TeslaWakeOnCAN": True, "CarParams": b"corrupt", "CarParamsPersistent": car_params()}, False),
  ({"TeslaWakeOnCAN": True, "CarParamsPersistent": b"corrupt"}, False),
  ({"TeslaWakeOnCAN": True, "CarParamsPersistent": car_params(fingerprint="TESLA_MODEL_X")}, True),
  ({"TeslaWakeOnCAN": True, "CarParamsPersistent": car_params(fingerprint="TESLA_MODEL_S_PREAP")}, False),
  ({"TeslaWakeOnCAN": True, "CarParamsPersistent": car_params(fingerprint="")}, False),
  ({"TeslaWakeOnCAN": True, "CarParamsPersistent": car_params("hyundai", "HYUNDAI_SONATA")}, False),
  ({"TeslaWakeOnCAN": True, "CarParamsCache": car_params(), "CarParamsPrevRoute": car_params()}, False),
])
def test_tesla_wake_requires_enabled_supported_vehicle_without_conflicting_identity(values, expected):
  assert hasattr(pandad, "get_tesla_wake_on_can"), "Tesla wake parameter reader is missing"
  assert pandad.get_tesla_wake_on_can(VehicleParams(**values)) is expected


def test_unregistered_tesla_param_defaults_off():
  class OldParams(VehicleParams):
    def get_bool(self, key):
      raise pandad.UnknownKeyName(key)

  assert hasattr(pandad, "get_tesla_wake_on_can"), "Tesla wake parameter reader is missing"
  assert pandad.get_tesla_wake_on_can(OldParams()) is False


def test_missing_tesla_firmware_never_falls_back_to_stock(monkeypatch, tmp_path):
  monkeypatch.setattr(pandad, "FW_PATH", str(tmp_path))
  panda = SimpleNamespace(get_mcu_type=lambda: SimpleNamespace(config=SimpleNamespace(app_fn="panda_h7.bin.signed")))
  with pytest.raises(FileNotFoundError, match="panda_h7_tesla_wake"):
    pandad.get_expected_firmware_path(panda, False, False, False, tesla_wake=True)


def test_selected_tesla_firmware_path_used(monkeypatch, tmp_path):
  monkeypatch.setattr(pandad, "FW_PATH", str(tmp_path))
  firmware = tmp_path / "panda_h7_tesla_wake_can_ignition_only.bin.signed"
  firmware.touch()
  panda = SimpleNamespace(get_mcu_type=lambda: SimpleNamespace(config=SimpleNamespace(app_fn="panda_h7.bin.signed")))
  assert pandad.get_expected_firmware_path(panda, False, False, True, tesla_wake=True) == str(firmware)


class FirmwarePanda:
  get_signature_from_firmware = staticmethod(pandad.Panda.get_signature_from_firmware)

  def __init__(self, app_fn="panda_h7.bin.signed"):
    self.app_fn = app_fn
    self.bootstub = False
    self.signature = b"old firmware"
    self.flashed = []

  def get_mcu_type(self):
    return SimpleNamespace(config=SimpleNamespace(app_fn=self.app_fn))

  def is_internal(self):
    return True

  def get_version(self):
    return "test"

  def get_signature(self):
    return self.signature

  def flash(self, fn):
    self.flashed.append(fn)
    self.signature = self.get_signature_from_firmware(fn)

  def __enter__(self):
    return self

  def __exit__(self, *args):
    pass


@pytest.mark.parametrize("enabled,filename", [
  (True, "panda_h7_tesla_wake.bin.signed"),
  (False, "panda_h7.bin.signed"),
])
def test_startup_flashes_and_verifies_selected_signature(monkeypatch, tmp_path, enabled, filename):
  device = FirmwarePanda()
  firmware = tmp_path / filename
  firmware.write_bytes(b"s" * 128)
  monkeypatch.setattr(pandad, "FW_PATH", str(tmp_path))
  class PandaFactory:
    get_signature_from_firmware = staticmethod(FirmwarePanda.get_signature_from_firmware)

    def __new__(cls, serial):
      assert serial == "test-panda"
      return device

  monkeypatch.setattr(pandad, "Panda", PandaFactory)
  assert pandad.flash_panda("test-panda", False, False, False, tesla_wake=enabled) is device
  assert device.flashed == [str(firmware)]
  assert device.signature == b"s" * 128
  pandad.flash_panda("test-panda", False, False, False, tesla_wake=enabled)
  assert device.flashed == [str(firmware)]


@pytest.mark.parametrize("available", [False, True])
def test_manual_updater_uses_tesla_image_and_never_flashes_stock_when_missing(monkeypatch, tmp_path, available):
  from openpilot.starpilot.common import starpilot_utilities as utilities
  from openpilot.selfdrive.pandad import rivian_long_flasher

  device = FirmwarePanda()
  firmware = tmp_path / "panda_h7_tesla_wake.bin.signed"
  if available:
    firmware.write_bytes(b"m" * 128)
  params = VehicleParams(TeslaWakeOnCAN=True, CarParamsPersistent=car_params())
  class PandaFactory:
    @staticmethod
    def list():
      return ["test-panda"]

    @staticmethod
    def usb_list():
      return []

    def __new__(cls, serial):
      assert serial == "test-panda"
      return device

  monkeypatch.setattr(utilities, "Panda", PandaFactory)
  monkeypatch.setattr(utilities, "Params", lambda: params)
  monkeypatch.setattr(utilities, "FW_PATH", str(tmp_path))
  monkeypatch.setattr(rivian_long_flasher, "is_rivian_vehicle", lambda: False)
  errors = []
  monkeypatch.setattr(utilities, "capture_exception", errors.append)
  removed = []
  utilities.flash_panda(SimpleNamespace(remove=removed.append))
  assert device.flashed == ([str(firmware)] if available else [])
  assert bool(errors) is (not available)
  if errors:
    assert isinstance(errors[0], FileNotFoundError)
  assert removed == ["FlashPanda"]


def test_other_variants_keep_existing_missing_image_fallback(monkeypatch, tmp_path):
  monkeypatch.setattr(pandad, "FW_PATH", str(tmp_path))
  assert pandad.get_expected_firmware_path(FirmwarePanda(), True, True, True) == str(tmp_path / "panda_h7.bin.signed")


@pytest.mark.parametrize("enabled", [False, True])
def test_main_skips_stock_cpp_signature_check_only_for_selected_variant(monkeypatch, enabled):
  device = FirmwarePanda()
  device.get_usb_serial = lambda: "test-panda"
  device.get_type = lambda: b"type"
  device.health = lambda: {"heartbeat_lost": False, "som_reset_triggered": False}
  device.reset = lambda **kwargs: None
  device.close = lambda: None
  params = VehicleParams(TeslaWakeOnCAN=enabled, CarParamsPersistent=car_params())
  params.remove = lambda key: params.values.pop(key, None)
  params.put = lambda key, value: params.values.update({key: value})
  monkeypatch.setattr(pandad, "Params", lambda: params)
  monkeypatch.setattr(pandad, "Panda", SimpleNamespace(list=lambda: ["test-panda"]))
  monkeypatch.setattr(pandad, "PandaDFU", SimpleNamespace(list=lambda: []))
  monkeypatch.setattr(pandad, "HARDWARE", SimpleNamespace(has_internal_panda=lambda: True))
  monkeypatch.setattr(pandad, "prepare_rivian_bridge", lambda serials: set())
  selections = []

  def flash(serial, gm, hkg, ignore, tesla):
    selections.append((serial, gm, hkg, ignore, tesla))
    return device

  monkeypatch.setattr(pandad, "flash_panda", flash)
  handlers = []
  monkeypatch.setattr(pandad.signal, "signal", lambda signum, handler: handlers.append(handler))
  environments = []

  def start_process(args, cwd):
    environments.append(pandad.os.environ.get("BOARDD_SKIP_FW_CHECK"))
    return SimpleNamespace(wait=lambda: handlers[0](2, None), send_signal=lambda signum: None)

  monkeypatch.setattr(pandad.subprocess, "Popen", start_process)
  monkeypatch.setenv("BOARDD_SKIP_FW_CHECK", "stale")
  pandad.main()
  assert selections == [("test-panda", False, False, False, enabled)]
  assert environments == (["1"] if enabled else [None])


@pytest.mark.parametrize("enabled,ignore", list(product([False, True], repeat=2)))
def test_ui_preflight_requires_both_board_images_without_writing(monkeypatch, tmp_path, enabled, ignore):
  from openpilot.selfdrive.pandad import panda_firmware as firmware
  monkeypatch.setattr(firmware, "FW_PATH", str(tmp_path), raising=False)
  params = VehicleParams(TeslaWakeOnCAN=not enabled, IgnoreIgnitionLine=ignore)
  before = dict(params.values)
  preflight = getattr(firmware, "validate_tesla_can_wake_firmware", None)
  assert callable(preflight), "firmware preflight must reject missing images before settings are saved"
  base = "tesla_wake" if enabled else ""
  suffix = "_".join(part for part in (base, "can_ignition_only" if ignore else "") if part)
  suffix = "_" + suffix if suffix else ""
  names = [f"panda{suffix}.bin.signed", f"panda_h7{suffix}.bin.signed"]
  for index, name in enumerate(names):
    with pytest.raises(RuntimeError, match="missing"):
      preflight(params, enabled)
    (tmp_path / name).write_bytes(b"firmware")
  preflight(params, enabled)
  assert params.values == before
