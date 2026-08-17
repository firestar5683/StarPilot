import importlib.util
import json
import math
import sys
import time

from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "flm_workspace.py"


def _simple_module(name, **attrs):
  module = ModuleType(name)
  for attr, value in attrs.items():
    setattr(module, attr, value)
  return module


def _install_flm_import_stubs(tmp_path):
  class FakeParams:
    _store = {}
    _memory_store = {}

    def __init__(self, return_defaults=False, memory=False):
      self.return_defaults = return_defaults
      self.memory = memory

    @property
    def _values(self):
      return type(self)._memory_store if self.memory else type(self)._store

    def get(self, key, block=False, return_default=False, encoding=None, default=None):
      del block, return_default
      value = self._values.get(key, default)
      if encoding and isinstance(value, bytes):
        return value.decode(encoding, errors="replace")
      return value

    def get_bool(self, key, default=False):
      value = self._values.get(key, default)
      if isinstance(value, bool):
        return value
      return str(value).strip().lower() in ("1", "true", "yes", "on")

    def get_float(self, key, block=False, return_default=False, default=0.0):
      del block, return_default
      value = self._values.get(key, default)
      try:
        return float(value)
      except Exception:
        return default

    def put(self, key, value):
      self._values[key] = value

    def put_bool(self, key, value):
      self._values[key] = bool(value)

    def put_float(self, key, value):
      self._values[key] = float(value)

    def remove(self, key):
      self._values.pop(key, None)

  FakeParams._store = {}
  FakeParams._memory_store = {}

  class FakeHyundaiFlags:
    CANFD = 1

  class FakeSteerControlType:
    torque = 0
    angle = 1

  fake_car_params = SimpleNamespace(SteerControlType=FakeSteerControlType)
  cereal_car = _simple_module("cereal.car", CarParams=fake_car_params)
  cereal = _simple_module("cereal", car=cereal_car)
  sys.modules["cereal"] = cereal
  sys.modules["cereal.car"] = cereal_car

  sys.modules["opendbc.car.hyundai.values"] = _simple_module("opendbc.car.hyundai.values", HyundaiFlags=FakeHyundaiFlags)
  sys.modules["openpilot.common.params"] = _simple_module("openpilot.common.params", Params=FakeParams)
  sys.modules["openpilot.selfdrive.controls.lib.latcontrol_torque"] = _simple_module(
    "openpilot.selfdrive.controls.lib.latcontrol_torque",
    KP=1.0,
  )

  def normalize_flm_overrides(payload):
    if isinstance(payload, str):
      payload = json.loads(payload)
    payload = payload or {}
    normalized = {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {},
    }
    for family, family_payload in payload.get("baseFrictionThresholds", {}).items():
      values = family_payload.get("values", [])
      if len(values) == 5:
        normalized["baseFrictionThresholds"][family] = {
          "speedKnots": [0.0, 5.0, 10.0, 15.0, 25.0],
          "values": [float(value) for value in values],
        }
    for key, value in payload.get("vehicleKnobs", {}).items():
      normalized["vehicleKnobs"][key] = float(value)
    if not normalized["baseFrictionThresholds"] and not normalized["vehicleKnobs"]:
      return {}
    return normalized

  sys.modules["openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes"] = _simple_module(
    "openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes",
    FLM_FRICTION_SPEED_KNOTS=[0.0, 5.0, 10.0, 15.0, 25.0],
    get_flm_capabilities=lambda *args, **kwargs: {"richProfileKey": "hyundai_ioniq_6", "frictionFamily": "hkg_canfd"},
    get_flm_rich_profile_key=lambda *args, **kwargs: "hyundai_ioniq_6",
    get_flm_supported_vehicle_knobs=lambda: {
      "hyundai_ioniq_6.ff_gain_left": {"min": 0.0, "max": 0.6, "precision": 0.001, "defaultValue": 0.1, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.ff_gain_right": {"min": 0.0, "max": 0.6, "precision": 0.001, "defaultValue": 0.12, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.turn_in_boost_left": {"min": 0.4, "max": 2.8, "precision": 0.001, "defaultValue": 1.64, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.unwind_taper_left": {"min": 0.0, "max": 1.2, "precision": 0.001, "defaultValue": 0.4, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.low_speed_angle_assist_max_torque": {"min": 0.0, "max": 0.8, "precision": 0.001, "defaultValue": 0.46, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.crawl_turn_in_ff_boost_left": {"min": 0.0, "max": 0.5, "precision": 0.001, "defaultValue": 0.18, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.curvy_turn_in_trim_left": {"min": 0.0, "max": 0.2, "precision": 0.001, "defaultValue": 0.06, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.curvy_unwind_extra_reduction_left": {"min": 0.0, "max": 0.45, "precision": 0.001, "defaultValue": 0.18, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.center_deadband_low_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.center_deadband_mid_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.center_deadband_fast_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "hyundai_ioniq_6"},
      "hyundai_ioniq_6.center_deadband_highway_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "hyundai_ioniq_6"},
      "torque_universal.ff_gain_left": {"min": -0.4, "max": 0.6, "precision": 0.001, "defaultValue": 0.0, "profile": "torque_universal"},
      "torque_universal.ff_gain_right": {"min": -0.4, "max": 0.6, "precision": 0.001, "defaultValue": 0.0, "profile": "torque_universal"},
      "torque_universal.center_deadband_low_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "torque_universal"},
      "torque_universal.center_deadband_mid_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "torque_universal"},
      "torque_universal.center_deadband_fast_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "torque_universal"},
      "torque_universal.center_deadband_highway_deg": {"min": 0.0, "max": 0.3, "precision": 0.005, "defaultValue": 0.0, "profile": "torque_universal"},
    },
    get_gm_base_friction_threshold=lambda v_ego: 0.20 + (0.001 * float(v_ego)),
    get_hkg_canfd_base_friction_threshold=lambda v_ego: 0.39 + (0.001 * float(v_ego)),
    get_standard_friction_threshold=lambda v_ego: 0.30 + (0.001 * float(v_ego)),
    normalize_flm_overrides=normalize_flm_overrides,
  )
  sys.modules["openpilot.system.hardware"] = _simple_module("openpilot.system.hardware", PC=True)
  sys.modules["openpilot.system.hardware.hw"] = _simple_module(
    "openpilot.system.hardware.hw",
    Paths=SimpleNamespace(comma_home=lambda: str(tmp_path), log_root=lambda **kwargs: str(tmp_path / "logs")),
  )
  sys.modules["openpilot.tools.lib.logreader"] = _simple_module("openpilot.tools.lib.logreader", LogReader=lambda *args, **kwargs: [])
  sys.modules["openpilot.starpilot.common.lateral_delay"] = _simple_module(
    "openpilot.starpilot.common.lateral_delay",
    full_lateral_delay=lambda value: float(value) + 0.2,
  )
  galaxy_utilities = _simple_module(
    "openpilot.starpilot.system.the_galaxy.utilities",
    get_segments_in_route=lambda route, footage_path: [],
  )
  galaxy_package = _simple_module(
    "openpilot.starpilot.system.the_galaxy",
    utilities=galaxy_utilities,
  )
  galaxy_package.__path__ = []
  sys.modules["openpilot.starpilot.system.the_galaxy"] = galaxy_package
  sys.modules["openpilot.starpilot.system.the_galaxy.utilities"] = galaxy_utilities

  return FakeParams


def _load_flm_workspace_module(tmp_path):
  fake_params_cls = _install_flm_import_stubs(tmp_path)
  module_name = f"test_flm_workspace_{hash(tmp_path)}"
  spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
  module = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  sys.modules[module_name] = module
  spec.loader.exec_module(module)
  return module, fake_params_cls


def _sample(module, **kwargs):
  base = dict(
    route="route",
    segment=0,
    t=0.0,
    v_ego=28.0,
    lat_active=True,
    steering_pressed=False,
    saturated=False,
    actual_la=0.0,
    desired_la=0.0,
    desired_jerk=0.0,
    error=0.0,
    error_rate=0.0,
    p=0.0,
    i=0.0,
    d=0.0,
    f=0.0,
    output=0.0,
    steering_angle_deg=0.0,
    steering_torque=0.0,
    cmd_torque=0.0,
    out_torque=0.0,
    roll_deg=0.0,
  )
  base.update(kwargs)
  return module.FLMSample(**base)


def _write_custom_trial_report(module, report_id="report-custom"):
  workspace = module.ensure_flm_workspace()
  supported = {
    symbol: metadata
    for symbol, metadata in module.get_flm_supported_vehicle_knobs().items()
    if metadata["profile"] == "hyundai_ioniq_6"
  }
  stock_knobs = {symbol: metadata["defaultValue"] for symbol, metadata in supported.items()}
  first_symbol = next(iter(stock_knobs))
  recommended_value = min(float(supported[first_symbol]["max"]), float(stock_knobs[first_symbol]) + 0.02)
  profile = {
    "id": f"{report_id}:cleanup_pass:recommended",
    "reportId": report_id,
    "label": "Recommended",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 1.8},
    "flmOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {first_symbol: recommended_value},
    },
  }
  suggestion = {
    "currentVsSuggested": {
      "type": "vehicle_knob",
      "symbol": first_symbol,
      "current": stock_knobs[first_symbol],
      "suggested": recommended_value,
    },
    "observedBehavior": "The analyzed route entered left curves late.",
    "likelyInterpretation": "The left-side feedforward layer needs more authority.",
    "primaryAdjustment": f"Move {first_symbol} to {recommended_value}.",
    "whyThisKnob": "This corrects the affected side without moving global authority.",
    "logSupport": "Matched in three events.",
  }
  report = {
    "reportId": report_id,
    "createdAt": 1.0,
    "routeNames": ["route"],
    "car": {"carFingerprint": "TEST_CAR", "brand": "hyundai", "controlPath": "torque"},
    "capabilities": {
      "frictionFamily": "hkg_canfd",
      "richProfileKey": "hyundai_ioniq_6",
      "richProfileLabel": "Ioniq 6",
    },
    "stockParams": {
      "UseAutoSteerDelay": True,
      "SteerDelay": 0.25,
      "SteerFriction": 0.1,
      "SteerKP": 1.0,
      "SteerLatAccel": 1.5,
      "SteerRatio": 15.0,
      "FLMBaseFrictionThresholds": {
        "hkg_canfd": {
          "speedKnots": [0.0, 5.0, 10.0, 15.0, 25.0],
          "values": [0.39, 0.395, 0.4, 0.405, 0.415],
        },
      },
      "FLMVehicleKnobs": stock_knobs,
    },
    "currentParams": {
      "AdvancedLateralTune": False,
      "ForceAutoTune": True,
      "ForceAutoTuneOff": False,
      "UseAutoSteerDelay": True,
      "SteerDelay": 0.25,
      "SteerFriction": 0.1,
      "SteerKP": 1.0,
      "SteerLatAccel": 1.5,
      "SteerRatio": 15.0,
      "FLMActiveProfileId": "",
      "FLMActiveOverrides": {},
      "FLMTrialApplied": False,
    },
    "primaryPathKey": "cleanup_pass",
    "selectedPathKey": "cleanup_pass",
    "paths": [{
      "key": "cleanup_pass",
      "title": "Cleanup Pass",
      "isPrimary": True,
      "profiles": [profile],
      "suggestions": [suggestion],
    }],
    "profiles": [profile],
  }
  (workspace["reports"] / f"{report_id}.json").write_text(json.dumps(report), encoding="utf-8")
  (workspace["profiles"] / f"{report_id}.json").write_text(json.dumps([profile]), encoding="utf-8")
  module.Params().put_bool(module.FLM_CUSTOM_VALUES_PARAM, True)
  return report, supported, first_symbol, recommended_value


def test_effective_control_path_prefers_logged_controller_state(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  pid_cp = SimpleNamespace(
    steerControlType=module.car.CarParams.SteerControlType.torque,
    lateralTuning=SimpleNamespace(which=lambda: "pid"),
  )

  assert module._effective_control_path(pid_cp, {"torqueState": 1200}) == ("torque", "controlsState")
  assert module._effective_control_path(pid_cp, {"pidState": 1200}) == ("pid", "controlsState")
  assert module._effective_control_path(pid_cp, {}) == ("pid", "carParams")


def test_effective_control_path_keeps_true_angle_and_mixed_routes_diagnostic(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  angle_cp = SimpleNamespace(
    steerControlType=module.car.CarParams.SteerControlType.angle,
    lateralTuning=SimpleNamespace(which=lambda: "torque"),
  )

  assert module._effective_control_path(angle_cp, {}) == ("angle", "carParams")
  assert module._effective_control_path(angle_cp, {"angleState": 900}) == ("angle", "controlsState")
  assert module._effective_control_path(angle_cp, {"angleState": 900, "torqueState": 900}) == ("mixed", "controlsState")


def test_segment_ranges_limit_resolved_route_sources(tmp_path, monkeypatch):
  module, _ = _load_flm_workspace_module(tmp_path)
  route = "00000001--abcdef1234"
  segment_names = [f"{route}--{segment}" for segment in range(12)]
  for segment_name in segment_names:
    segment_path = tmp_path / segment_name
    segment_path.mkdir()
    (segment_path / "rlog.zst").write_bytes(b"log")

  monkeypatch.setattr(module.utilities, "get_segments_in_route", lambda *_args: segment_names)
  sources, warnings = module.resolve_route_sources(
    [route],
    [str(tmp_path)],
    {route: {"start": 4, "end": 9}},
  )

  assert [source.segment_num for source in sources] == [4, 5, 6, 7, 8, 9]
  assert warnings == []


def test_segment_range_rejects_reversed_bounds(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  with pytest.raises(ValueError, match="first segment"):
    module.normalize_segment_ranges(["route"], {"route": {"start": 9, "end": 4}})


def test_segment_reader_timeout_interrupts_stalled_log(tmp_path, monkeypatch):
  module, _ = _load_flm_workspace_module(tmp_path)
  source = module.RouteSource(
    route="route",
    footage_path=str(tmp_path),
    segment="route--41",
    segment_num=41,
    log_path=str(tmp_path / "route--41" / "rlog.zst"),
    used_qlog=False,
  )
  monkeypatch.setattr(module, "_segment_samples", lambda *_args, **_kwargs: time.sleep(0.2))

  with pytest.raises(module.FLMSegmentTimeout, match="segment 41"):
    module._segment_samples_with_timeout(source, module.Params(), timeout_seconds=0.02)

  assert module.FLM_SEGMENT_TIMEOUT_SECONDS == 60.0


def test_analysis_is_rejected_while_onroad(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  fake_params_cls._store = {"IsOnroad": True}

  with pytest.raises(module.FLMAnalysisCancelled, match="went onroad"):
    module._require_flm_offroad()
  assert module.start_flm_background_analysis(["route"], [str(tmp_path)]) is False


def test_segment_analysis_stops_on_mid_run_onroad_transition(tmp_path, monkeypatch):
  module, _ = _load_flm_workspace_module(tmp_path)

  class TransitionParams:
    calls = 0

    def get_bool(self, key):
      assert key == "IsOnroad"
      self.calls += 1
      return self.calls >= 2

  monkeypatch.setattr(module, "LogReader", lambda *args, **kwargs: iter([SimpleNamespace()]))
  source = SimpleNamespace(log_path=tmp_path / "rlog")

  with pytest.raises(module.FLMAnalysisCancelled, match="went onroad"):
    module._segment_samples(source, params=TransitionParams())


def test_onroad_stop_terminates_process_group_and_preserves_reason(tmp_path, monkeypatch):
  module, _ = _load_flm_workspace_module(tmp_path)
  module.FLM_STATUS_PATH = tmp_path / "flm_status.json"
  module._write_flm_status({"pid": 4321, "startedAt": 1.0, "running": True, "state": "analyzing"})
  signals = []

  class FakeProcess:
    pid = 4321

    @staticmethod
    def poll():
      return None

    @staticmethod
    def wait(timeout):
      del timeout
      return 0

  monkeypatch.setattr(module.os, "getpgid", lambda pid: pid)
  monkeypatch.setattr(module.os, "killpg", lambda pgid, sig: signals.append((pgid, sig)))
  module.FLM_ANALYZER_PROCESS = FakeProcess()

  assert module.stop_flm_background_analysis(reason="onroad") is True
  assert signals == [(4321, module.signal.SIGTERM)]
  assert module.FLM_ANALYZER_PROCESS is None
  assert module.read_flm_status()["state"] == "cancelled_onroad"
  assert "went onroad" in module.read_flm_status()["error"]


def test_worker_watchdog_exits_immediately_when_vehicle_goes_onroad(tmp_path, monkeypatch):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  module.FLM_STATUS_PATH = tmp_path / "flm_status.json"
  fake_params_cls._store = {"IsOnroad": True}
  module._write_flm_status({"pid": 4321, "startedAt": 1.0, "running": True, "state": "analyzing"})

  def fake_exit(code):
    raise SystemExit(code)

  signals = []
  monkeypatch.setattr(module.os, "getpid", lambda: 4321)
  monkeypatch.setattr(module.os, "getpgrp", lambda: 4321)
  monkeypatch.setattr(module.os, "killpg", lambda pgid, sig: signals.append((pgid, sig)))
  monkeypatch.setattr(module.os, "_exit", fake_exit)
  with pytest.raises(SystemExit) as exc:
    module._watch_flm_worker_for_onroad()

  assert exc.value.code == 0
  assert signals == [(4321, module.signal.SIGTERM)]
  assert module.read_flm_status()["state"] == "cancelled_onroad"


def test_legacy_workspace_is_migrated_to_flm(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  legacy_name = "".join(("f", "t", "m"))
  legacy_root = tmp_path / "starpilot" / "data" / "galaxy" / legacy_name
  legacy_report = legacy_root / "reports" / "legacy.json"
  legacy_report.parent.mkdir(parents=True)
  legacy_report.write_text(json.dumps({
    "reportId": "legacy",
    f"{legacy_name}Overrides": {"vehicleKnobs": {"generic.ff_gain_left": 0.1}},
    "profileLabel": legacy_name.upper(),
  }), encoding="utf-8")

  workspace = module.ensure_flm_workspace()
  migrated = json.loads((workspace["reports"] / "legacy.json").read_text(encoding="utf-8"))

  assert not legacy_root.exists()
  assert migrated["flmOverrides"]["vehicleKnobs"]["generic.ff_gain_left"] == pytest.approx(0.1)
  assert migrated["profileLabel"] == "FLM"


def test_classify_torque_samples_detects_center_chatter(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = []
  for idx in range(60):
    angle = 0.75 * math.sin(idx * 0.9)
    samples.append(_sample(
      module,
      t=idx * 0.1,
      desired_la=0.04 * math.sin(idx * 0.1),
      actual_la=0.03 * math.sin(idx * 0.1),
      steering_angle_deg=angle,
      output=0.02 * math.sin(idx * 0.9),
    ))

  summaries, stats = module.classify_torque_samples(samples)
  assert stats["sampleCount"] == len(samples) - 2  # Segment edges are event boundaries, not analysis samples.
  chatter = next(summary for summary in summaries if summary["bucket"] == "center_chatter")
  assert chatter["plotData"]["driverOverrideFree"] is True
  assert len(chatter["plotData"]["times"]) == len(chatter["plotData"]["desired"])
  assert len(chatter["plotData"]["times"]) == len(chatter["plotData"]["actual"])


def test_classify_torque_samples_detects_mid_speed_center_chatter(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = []
  for idx in range(80):
    samples.append(_sample(
      module,
      t=idx * 0.1,
      v_ego=10.0,
      desired_la=0.025 * math.sin(idx * 0.08),
      actual_la=0.09 * math.sin(idx * 0.85),
      steering_angle_deg=0.65 * math.sin(idx * 0.85),
      output=0.035 * math.sin(idx * 0.85),
    ))

  summaries, _ = module.classify_torque_samples(samples)
  chatter = next(summary for summary in summaries if summary["bucket"] == "center_chatter")
  assert chatter["speedBand"] == "mid"
  assert chatter["evidence"]["chatterMetrics"]["steeringReversals"] >= 3


def test_classify_torque_samples_detects_low_speed_center_chatter(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = []
  for idx in range(80):
    samples.append(_sample(
      module,
      t=idx * 0.1,
      v_ego=4.0,
      desired_la=0.018 * math.sin(idx * 0.07),
      actual_la=0.14 * math.sin(idx * 0.78),
      steering_angle_deg=1.05 * math.sin(idx * 0.78),
      output=0.065 * math.sin(idx * 0.78),
    ))

  summaries, _ = module.classify_torque_samples(samples)
  chatter = next(summary for summary in summaries if summary["bucket"] == "center_chatter")
  assert chatter["speedBand"] == "low"
  assert chatter["evidence"]["chatterMetrics"]["outputReversals"] >= 3


def test_classify_torque_samples_rejects_model_driven_center_motion(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = []
  for idx in range(80):
    desired = 0.14 * math.sin(idx * 0.85)
    samples.append(_sample(
      module,
      t=idx * 0.1,
      v_ego=24.0,
      desired_la=desired,
      actual_la=desired * 0.95,
      steering_angle_deg=0.55 * math.sin(idx * 0.85),
      output=0.04 * math.sin(idx * 0.85),
    ))

  summaries, _ = module.classify_torque_samples(samples)
  assert not any(summary["bucket"] == "center_chatter" for summary in summaries)


def test_plot_context_stops_at_ineligible_samples(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = [_sample(module, t=idx * 0.1, desired_la=idx * 0.01, actual_la=idx * 0.009) for idx in range(20)]
  eligibility = [True] * len(samples)
  eligibility[5] = False
  eligibility[14] = False
  event = {
    "startIdx": 8,
    "endIdx": 10,
    "direction": "left",
    "speedBand": "mid",
  }

  plot = module._build_plot_data(samples, event, eligibility)
  assert plot["driverOverrideFree"] is True
  assert plot["times"] == pytest.approx([idx * 0.1 for idx in range(8)])
  assert plot["eventStartSec"] == pytest.approx(0.2)
  assert plot["eventEndSec"] == pytest.approx(0.4)
  assert plot["segmentLabel"] == "route/0"


def test_analysis_eligibility_masks_driver_override_with_settle_buffer(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = [
    _sample(module, t=idx * 0.1, steering_pressed=(idx == 20))
    for idx in range(50)
  ]

  eligible = module._analysis_eligibility_mask(samples)
  assert eligible[16] is True
  assert eligible[17] is False
  assert eligible[20] is False
  assert eligible[30] is False
  assert eligible[31] is True


def test_stock_param_state_captures_generic_and_rich_defaults(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  torque_tune = SimpleNamespace(friction=0.09, latAccelFactor=3.0)
  lateral_tuning = SimpleNamespace(which=lambda: "torque", torque=torque_tune)
  CP = SimpleNamespace(lateralTuning=lateral_tuning, steerActuatorDelay=0.1, steerRatio=14.26)
  capabilities = {"frictionFamily": "hkg_canfd", "richProfileKey": "hyundai_ioniq_6"}

  stock = module._stock_param_state(CP, capabilities)
  assert stock["SteerLatAccel"] == pytest.approx(3.0)
  assert stock["SteerFriction"] == pytest.approx(0.09)
  assert stock["UseAutoSteerDelay"] is True
  assert stock["SteerDelay"] == pytest.approx(0.3)
  assert stock["SteerRatio"] == pytest.approx(14.26)
  assert len(stock["FLMBaseFrictionThresholds"]["hkg_canfd"]["values"]) == 5
  assert stock["FLMVehicleKnobs"]["hyundai_ioniq_6.turn_in_boost_left"] == pytest.approx(1.64)


def test_classify_torque_samples_does_not_bridge_driver_override(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  samples = []
  for idx in range(80):
    samples.append(_sample(
      module,
      t=idx * 0.1,
      desired_la=-0.5,
      actual_la=-0.1,
      desired_jerk=-0.5,
      steering_pressed=30 <= idx <= 40,
    ))

  summaries, stats = module.classify_torque_samples(samples)
  late_events = [event for summary in summaries if summary["bucket"] == "late_turn_in" for event in summary["events"]]
  assert stats["excludedDriverOverrideSamples"] > 11
  assert all(event["endIdx"] < 27 or event["startIdx"] > 50 for event in late_events)


def test_build_suggestions_prefers_rich_low_speed_turn_in_knob(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "low_speed_unwillingness",
    "dimensionId": "low_speed_unwillingness:left:low",
    "direction": "left",
    "speedBand": "low",
    "severity": 0.9,
    "evidence": {"speedBand": "low", "directionBias": "left", "eventCount": 3, "segments": [{"label": "route/2"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "hyundai_ioniq_6", "frictionFamily": "hkg_canfd"}
  current = {"SteerLatAccel": 1.8, "SteerFriction": 0.2}

  suggestions = module.build_suggestions([summary], capabilities, current)
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "vehicle_knob"
  assert adjustment["symbol"] == "hyundai_ioniq_6.low_speed_angle_assist_max_torque"


def test_build_suggestions_baseline_prefers_generic_lat_accel_for_understeer(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "understeer",
    "dimensionId": "understeer:left:mid",
    "direction": "left",
    "speedBand": "mid",
    "severity": 1.0,
    "evidence": {"speedBand": "mid", "directionBias": "left", "eventCount": 3, "segments": [{"label": "route/2"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "hyundai_ioniq_6", "frictionFamily": "hkg_canfd"}
  current = {"SteerLatAccel": 1.8, "SteerFriction": 0.2}

  suggestions = module.build_suggestions([summary], capabilities, current, strategy="baseline")
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "generic_param"
  assert adjustment["paramKey"] == "SteerLatAccel"
  assert adjustment["suggested"] > adjustment["current"]


def test_build_suggestions_baseline_respects_asymmetric_nonlinear_map(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "understeer",
    "dimensionId": "understeer:right:mid",
    "direction": "right",
    "speedBand": "mid",
    "severity": 1.0,
    "evidence": {"speedBand": "mid", "directionBias": "right", "eventCount": 3, "segments": [{"label": "route/2"}]},
    "plotSvg": "",
  }
  capabilities = {
    "richProfileKey": "hyundai_ioniq_6",
    "frictionFamily": "gm",
    "nonlinearTorqueMap": {
      "type": "siglin",
      "left": [2.6, 1.1, 0.19, 0.0],
      "right": [2.7, 1.0, 0.15, 0.0],
      "asymmetric": True,
    },
  }
  current = {"SteerLatAccel": 1.8, "SteerFriction": 0.2}

  suggestions = module.build_suggestions([summary], capabilities, current, strategy="baseline")
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "vehicle_knob"
  assert adjustment["symbol"] == "hyundai_ioniq_6.ff_gain_right"
  assert adjustment["suggested"] > adjustment["current"]


def test_nonlinear_torque_map_resolves_gm_integration_alias(tmp_path, monkeypatch):
  module, _ = _load_flm_workspace_module(tmp_path)
  volt_map = {
    "left": [1.525, 1.05, 0.155, 0.0],
    "right": [1.525, 0.95, 0.150, 0.0],
  }
  monkeypatch.setitem(sys.modules, "opendbc.car.gm.interface", _simple_module(
    "opendbc.car.gm.interface",
    NON_LINEAR_TORQUE_PARAM_ALIASES={"CHEVROLET_VOLT_ASCM": "CHEVROLET_VOLT"},
    get_nonlinear_torque_params=lambda candidate: volt_map if candidate == "CHEVROLET_VOLT_ASCM" else None,
  ))
  cp = SimpleNamespace(brand="gm", carFingerprint="CHEVROLET_VOLT_ASCM")

  nonlinear_map = module._nonlinear_torque_map(cp)

  assert nonlinear_map["type"] == "siglin"
  assert nonlinear_map["asymmetric"] is True
  assert nonlinear_map["sourceFingerprint"] == "CHEVROLET_VOLT"
  assert nonlinear_map["left"] == volt_map["left"]
  assert nonlinear_map["right"] == volt_map["right"]

  summary = {
    "bucket": "understeer",
    "dimensionId": "understeer:right:mid",
    "direction": "right",
    "speedBand": "mid",
    "severity": 1.0,
    "evidence": {"speedBand": "mid", "directionBias": "right", "eventCount": 3, "segments": [{"label": "route/2"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "torque_universal", "frictionFamily": "gm", "nonlinearTorqueMap": nonlinear_map}
  current = {"SteerLatAccel": 1.8, "SteerFriction": 0.2}
  adjustment = module.build_suggestions([summary], capabilities, current, strategy="cleanup")[0]["primaryAdjustmentRaw"]

  assert adjustment["type"] == "vehicle_knob"
  assert adjustment["symbol"] == "torque_universal.ff_gain_right"
  assert adjustment["suggested"] > adjustment["current"]

  summary["bucket"] = "oversteer"
  summary["dimensionId"] = "oversteer:right:mid"
  adjustment = module.build_suggestions([summary], capabilities, current, strategy="cleanup")[0]["primaryAdjustmentRaw"]
  assert adjustment["symbol"] == "torque_universal.ff_gain_right"
  assert adjustment["suggested"] < adjustment["current"]


def test_build_suggestions_rebases_rich_knob_against_active_override(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "low_speed_unwillingness",
    "dimensionId": "low_speed_unwillingness:left:low",
    "direction": "left",
    "speedBand": "low",
    "severity": 1.0,
    "evidence": {"speedBand": "low", "directionBias": "left", "eventCount": 3, "segments": [{"label": "route/2"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "hyundai_ioniq_6", "frictionFamily": "hkg_canfd"}
  current = {
    "SteerLatAccel": 1.8,
    "SteerFriction": 0.2,
    "FLMActiveOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {
        "hyundai_ioniq_6.low_speed_angle_assist_max_torque": 0.62,
      },
    },
  }

  suggestions = module.build_suggestions([summary], capabilities, current)
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "vehicle_knob"
  assert adjustment["symbol"] == "hyundai_ioniq_6.low_speed_angle_assist_max_torque"
  assert adjustment["current"] == pytest.approx(0.62)
  assert adjustment["suggested"] > adjustment["current"]


def test_build_suggestions_prefers_ioniq_6_curvy_trim_for_mid_speed_turn_in(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "oversteer",
    "dimensionId": "oversteer:left:fast",
    "direction": "left",
    "speedBand": "fast",
    "severity": 1.0,
    "evidence": {"speedBand": "fast", "directionBias": "left", "eventCount": 2, "segments": [{"label": "route/4"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "hyundai_ioniq_6", "frictionFamily": "hkg_canfd"}
  current = {"SteerLatAccel": 1.8, "SteerFriction": 0.2}

  suggestions = module.build_suggestions([summary], capabilities, current)
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "vehicle_knob"
  assert adjustment["symbol"] == "hyundai_ioniq_6.curvy_turn_in_trim_left"
  assert adjustment["suggested"] > adjustment["current"]


def test_build_suggestions_rebases_friction_curve_against_active_override(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "center_chatter",
    "dimensionId": "center_chatter:center:highway",
    "direction": "center",
    "speedBand": "highway",
    "severity": 1.0,
    "evidence": {"speedBand": "highway", "directionBias": "center", "eventCount": 4, "segments": [{"label": "route/5"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "torque_universal", "frictionFamily": "standard"}
  current_curve = [0.34, 0.35, 0.36, 0.32, 0.33]
  current = {
    "SteerLatAccel": 1.8,
    "SteerFriction": 0.2,
    "FLMActiveOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {
        "standard": {
          "speedKnots": [0.0, 5.0, 10.0, 15.0, 25.0],
          "values": current_curve,
        },
      },
      "vehicleKnobs": {},
    },
  }

  suggestions = module.build_suggestions([summary], capabilities, current)
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "friction_curve"
  assert adjustment["family"] == "standard"
  assert adjustment["current"] == current_curve
  assert adjustment["suggested"][4] > current_curve[4]


def test_center_chatter_cleanup_moves_to_deadband_after_threshold_pass(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summary = {
    "bucket": "center_chatter",
    "dimensionId": "center_chatter:center:mid",
    "direction": "center",
    "speedBand": "mid",
    "severity": 0.9,
    "evidence": {"speedBand": "mid", "directionBias": "center", "eventCount": 3, "segments": [{"label": "route/2"}]},
    "plotSvg": "",
  }
  capabilities = {"richProfileKey": "torque_universal", "frictionFamily": "standard"}
  current = {
    "SteerLatAccel": 1.8,
    "SteerFriction": 0.2,
    "FLMActiveOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {
        "standard": {
          "speedKnots": [0.0, 5.0, 10.0, 15.0, 25.0],
          "values": [0.30, 0.32, 0.34, 0.33, 0.34],
        },
      },
      "vehicleKnobs": {},
    },
  }

  suggestions = module.build_suggestions([summary], capabilities, current, strategy="cleanup")
  adjustment = suggestions[0]["primaryAdjustmentRaw"]
  assert adjustment["type"] == "vehicle_knob"
  assert adjustment["symbol"] == "torque_universal.center_deadband_mid_deg"
  assert adjustment["stage"] == "center_deadband"
  assert adjustment["suggested"] > adjustment["current"]


def test_center_chatter_friction_merge_preserves_each_speed_band(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  current_curve = [0.30, 0.30, 0.30, 0.30, 0.30]
  suggestions = []
  for speed_band in ("low", "highway"):
    adjustment = module._center_chatter_friction_adjustment("standard", speed_band, 1.0, {
      "FLMActiveOverrides": {
        "baseFrictionThresholds": {
          "standard": {"speedKnots": [0.0, 5.0, 10.0, 15.0, 25.0], "values": current_curve},
        },
      },
    })
    suggestions.append({"severity": 1.0, "primaryAdjustmentRaw": adjustment})

  _, overrides, _ = module._merge_primary_adjustments(suggestions, 1.0)
  merged = overrides["baseFrictionThresholds"]["standard"]["values"]
  assert merged[0] == pytest.approx(0.312)
  assert merged[1] == pytest.approx(0.320)
  assert merged[3] == pytest.approx(0.312)
  assert merged[4] == pytest.approx(0.325)


def test_select_primary_tuning_path_prefers_baseline_for_broad_mismatch(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summaries = [
    {"bucket": "understeer", "severity": 1.0},
    {"bucket": "center_chatter", "severity": 0.9},
    {"bucket": "unwind_too_slow", "severity": 0.85},
    {"bucket": "saturation_limited", "severity": 0.8},
  ]
  stats = {"meanErrorAbs": 0.16}

  decision = module.select_primary_tuning_path(summaries, stats)
  assert decision["primaryPathKey"] == "baseline_fix"
  assert decision["alternatePathKey"] == "cleanup_pass"


def test_select_primary_tuning_path_does_not_automatically_demote_cleanup_progress(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summaries = [
    {"bucket": "understeer", "severity": 1.0},
    {"bucket": "center_chatter", "severity": 0.9},
    {"bucket": "unwind_too_slow", "severity": 0.85},
    {"bucket": "saturation_limited", "severity": 0.8},
  ]

  decision = module.select_primary_tuning_path(summaries, {"meanErrorAbs": 0.16}, cleanup_progress_locked=True)

  assert decision["primaryPathKey"] == "cleanup_pass"
  assert decision["alternatePathKey"] == "baseline_fix"
  assert decision["rawPrimaryPathKey"] == "baseline_fix"
  assert decision["automaticBaselineDemotionBlocked"] is True


def test_cleanup_progress_bootstraps_from_existing_vehicle_report(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report = {
    "reportId": "existing-cleanup",
    "primaryPathKey": "cleanup_pass",
    "car": {"carFingerprint": "TEST_TRUCK", "controlPath": "torque"},
  }
  (workspace["reports"] / "existing-cleanup.json").write_text(json.dumps(report), encoding="utf-8")

  assert module._cleanup_progress_locked("TEST_TRUCK") is True
  progress = json.loads((workspace["root"] / module.FLM_PROGRESS_FILENAME).read_text(encoding="utf-8"))
  assert progress["vehicles"]["TEST_TRUCK"]["minimumPathKey"] == "cleanup_pass"


def test_select_primary_tuning_path_prefers_cleanup_for_localized_issue(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summaries = [
    {"bucket": "notchy_mid_curve", "severity": 0.7},
    {"bucket": "center_chatter", "severity": 0.55},
  ]
  stats = {"meanErrorAbs": 0.07}

  decision = module.select_primary_tuning_path(summaries, stats)
  assert decision["primaryPathKey"] == "cleanup_pass"
  assert decision["alternatePathKey"] == "baseline_fix"


def test_select_primary_tuning_path_vetoes_baseline_when_global_fit_is_strong(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summaries = [
    {
      "bucket": "late_turn_in",
      "severity": 1.05,
      "direction": "right",
      "speedBand": "mid",
      "evidence": {"segments": [{"label": "route/37"}]},
    },
    {"bucket": "center_chatter", "severity": 0.55, "direction": "center", "speedBand": "highway", "evidence": {"segments": []}},
    {"bucket": "unwind_too_slow", "severity": 0.6, "direction": "right", "speedBand": "mid", "evidence": {"segments": [{"label": "route/37"}]}},
  ]

  decision = module.select_primary_tuning_path(summaries, {"meanErrorAbs": 0.054})
  assert decision["primaryPathKey"] == "cleanup_pass"
  assert "already strong" in decision["reason"]


def test_conflicting_summary_resolution_keeps_dominant_direction(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  summaries = [
    {"bucket": "early_turn_in", "severity": 1.34, "evidence": {"directionBias": "right", "speedBand": "mid", "eventCount": 1}},
    {"bucket": "late_turn_in", "severity": 1.03, "evidence": {"directionBias": "right", "speedBand": "mid", "eventCount": 18}},
  ]

  resolved = module._resolve_conflicting_actionable_suggestions(summaries)
  assert [summary["bucket"] for summary in resolved] == ["late_turn_in"]


def test_build_trial_profiles_suppresses_ignored_dimensions(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  suggestions = [
    {
      "dimensionId": "center_chatter:center:highway",
      "primaryAdjustmentRaw": {
        "type": "friction_curve",
        "family": "standard",
        "current": [0.30, 0.31, 0.32, 0.33, 0.34],
        "suggested": [0.31, 0.32, 0.33, 0.34, 0.35],
        "delta": [0.01, 0.01, 0.01, 0.01, 0.01],
      },
    },
    {
      "dimensionId": "understeer:left:mid",
      "primaryAdjustmentRaw": {
        "type": "generic_param",
        "paramKey": "SteerLatAccel",
        "current": 1.6,
        "suggested": 1.7,
        "delta": 0.1,
      },
    },
  ]
  feedback = {"acceptedDimensions": ["understeer:left:mid"], "ignoredDimensions": ["center_chatter:center:highway"]}
  profiles = module.build_trial_profiles("report-1", suggestions, feedback, {"richProfileKey": None})

  assert profiles
  assert profiles[0]["genericParams"]["ForceAutoTuneOff"] is True
  assert profiles[0]["genericParams"]["SteerLatAccel"] > 1.6
  assert profiles[0]["flmOverrides"] == {}


def test_build_trial_profiles_returns_none_when_every_dimension_is_ignored(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  suggestion = {
    "dimensionId": "understeer:left:mid",
    "severity": 0.8,
    "primaryAdjustmentRaw": {
      "type": "generic_param",
      "paramKey": "SteerLatAccel",
      "current": 1.6,
      "suggested": 1.7,
      "delta": 0.1,
    },
  }

  profiles = module.build_trial_profiles(
    "report-all-ignored",
    [suggestion],
    {"acceptedDimensions": [], "ignoredDimensions": ["understeer:left:mid"]},
    {"richProfileKey": None},
  )
  assert profiles == []


def test_merge_primary_adjustments_averages_conflicting_deltas(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  suggestions = [
    {
      "severity": 1.0,
      "primaryAdjustmentRaw": {
        "type": "generic_param",
        "paramKey": "SteerLatAccel",
        "current": 1.6,
        "suggested": 1.7,
        "delta": 0.1,
      },
    },
    {
      "severity": 0.5,
      "primaryAdjustmentRaw": {
        "type": "generic_param",
        "paramKey": "SteerLatAccel",
        "current": 1.6,
        "suggested": 1.55,
        "delta": -0.05,
      },
    },
  ]

  params_delta, overrides, _ = module._merge_primary_adjustments(suggestions, 1.0)
  assert params_delta["SteerLatAccel"] == pytest.approx(1.65, abs=1e-4)
  assert overrides == {}


def test_merge_primary_adjustments_disables_auto_delay_for_manual_delay_trial(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  suggestions = [{
    "severity": 1.0,
    "primaryAdjustmentRaw": {
      "type": "generic_param",
      "paramKey": "SteerDelay",
      "current": 0.31,
      "suggested": 0.33,
      "delta": 0.02,
    },
  }]

  params_delta, overrides, _ = module._merge_primary_adjustments(suggestions, 1.0)

  assert params_delta["SteerDelay"] == pytest.approx(0.33)
  assert params_delta["UseAutoSteerDelay"] is False
  assert overrides == {}


def test_custom_values_toggle_migrates_existing_custom_state_without_deleting_it(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  report, _, _, _ = _write_custom_trial_report(module)
  workspace = module.ensure_flm_workspace()

  fake_params_cls._store[module.FLM_CUSTOM_VALUES_PARAM] = False
  with pytest.raises(RuntimeError, match="Galaxy Developer settings"):
    module.build_custom_trial_schema(report["reportId"])

  active_path = workspace["snapshots"] / "active.json"
  active_payload = {
    "reportId": report["reportId"],
    "profileId": f"{report['reportId']}:custom",
    "profileLabel": "Custom",
    "appliedVehicleKnobs": {"example": 0.1},
  }
  active_path.write_text(json.dumps(active_payload), encoding="utf-8")
  fake_params_cls._store.pop(module.FLM_CUSTOM_VALUES_PARAM)

  assert module.custom_values_enabled() is True
  assert fake_params_cls._store[module.FLM_CUSTOM_VALUES_PARAM] is True

  fake_params_cls._store[module.FLM_CUSTOM_VALUES_PARAM] = False
  assert module.list_workspace()["customValuesEnabled"] is False
  assert json.loads(active_path.read_text(encoding="utf-8")) == active_payload


def test_custom_trial_limits_stay_anchored_until_a_new_analysis(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  report, _, first_symbol, _ = _write_custom_trial_report(module)
  schema = module.build_custom_trial_schema(report["reportId"])
  first_control = next(control for control in schema["controls"]["vehicleKnobs"] if control["key"] == first_symbol)
  zero_control = next(
    control for control in schema["controls"]["vehicleKnobs"]
    if control["key"].endswith(".center_deadband_low_deg")
  )

  assert schema["changeLimitPercent"] == 20
  assert first_control["analysisBaseline"] == pytest.approx(0.1)
  assert first_control["min"] == pytest.approx(0.08)
  assert first_control["max"] == pytest.approx(0.12)
  assert zero_control["analysisBaseline"] == pytest.approx(0.0)
  assert zero_control["min"] == pytest.approx(0.0)
  assert zero_control["max"] == pytest.approx(zero_control["precision"])

  values = json.loads(json.dumps(schema["presets"]["current"]["values"]))
  values["flmOverrides"]["vehicleKnobs"][first_symbol] = first_control["max"]
  module.validate_custom_trial_values(report["reportId"], values)
  fake_params_cls._store["IsOnroad"] = False
  module.apply_custom_trial(report["reportId"], values)

  same_analysis = module.build_custom_trial_schema(report["reportId"])
  same_control = next(control for control in same_analysis["controls"]["vehicleKnobs"] if control["key"] == first_symbol)
  assert same_control["analysisBaseline"] == pytest.approx(0.1)
  assert same_control["max"] == pytest.approx(0.12)

  too_far = json.loads(json.dumps(same_analysis["presets"]["current"]["values"]))
  too_far["flmOverrides"]["vehicleKnobs"][first_symbol] = same_control["max"] + same_control["precision"]
  with pytest.raises(ValueError, match="must be between"):
    module.validate_custom_trial_values(report["reportId"], too_far)

  next_report, _, next_symbol, _ = _write_custom_trial_report(module, "report-next-analysis")
  next_report["currentParams"]["FLMActiveOverrides"] = {
    "schemaVersion": 1,
    "baseFrictionThresholds": {},
    "vehicleKnobs": {next_symbol: 0.12},
  }
  workspace = module.ensure_flm_workspace()
  (workspace["reports"] / f"{next_report['reportId']}.json").write_text(json.dumps(next_report), encoding="utf-8")
  next_schema = module.build_custom_trial_schema(next_report["reportId"])
  next_control = next(control for control in next_schema["controls"]["vehicleKnobs"] if control["key"] == next_symbol)
  assert next_control["analysisBaseline"] == pytest.approx(0.12)
  assert next_control["max"] == pytest.approx(0.144)


def test_custom_trial_fill_presets_are_clipped_to_analysis_limits(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  report, _, first_symbol, _ = _write_custom_trial_report(module)
  profile = report["paths"][0]["profiles"][0]
  profile["genericParams"]["SteerLatAccel"] = 3.0
  profile["flmOverrides"]["vehicleKnobs"][first_symbol] = 0.4
  workspace = module.ensure_flm_workspace()
  (workspace["reports"] / f"{report['reportId']}.json").write_text(json.dumps(report), encoding="utf-8")

  schema = module.build_custom_trial_schema(report["reportId"])
  preset = schema["presets"]["recommended"]
  first_control = next(control for control in schema["controls"]["vehicleKnobs"] if control["key"] == first_symbol)

  assert preset["clippedToAnalysisLimits"] is True
  assert preset["values"]["genericParams"]["SteerLatAccel"] == pytest.approx(1.8)
  assert preset["values"]["flmOverrides"]["vehicleKnobs"][first_symbol] == pytest.approx(first_control["max"])


def test_custom_trial_schema_exposes_every_supported_knob_and_analysis_seed(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  report, supported, first_symbol, recommended_value = _write_custom_trial_report(module)

  schema = module.build_custom_trial_schema(report["reportId"])
  recommended = schema["presets"]["recommended"]["values"]

  assert schema["vehicleKnobCount"] == len(supported)
  assert {control["key"] for control in schema["controls"]["vehicleKnobs"]} == set(supported)
  assert set(recommended["flmOverrides"]["vehicleKnobs"]) == set(supported)
  assert recommended["flmOverrides"]["vehicleKnobs"][first_symbol] == pytest.approx(recommended_value)
  assert recommended["genericParams"]["SteerLatAccel"] == pytest.approx(1.8)
  assert all(control["help"]["summary"] for control in schema["controls"]["genericParams"])
  assert all(control["help"]["summary"] for control in schema["controls"]["vehicleKnobs"])
  first_help = next(control["help"] for control in schema["controls"]["vehicleKnobs"] if control["key"] == first_symbol)
  assert first_help["analysis"][0]["whyThisKnob"] == "This corrects the affected side without moving global authority."
  assert schema["controls"]["frictionCurve"]["help"]["summary"]
  assert schema["forcedSettings"] == {
    "AdvancedLateralTune": True,
    "ForceAutoTune": False,
    "ForceAutoTuneOff": True,
  }


def test_custom_trial_schema_refills_from_active_saved_tune(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  report, supported, first_symbol, _ = _write_custom_trial_report(module)
  schema = module.build_custom_trial_schema(report["reportId"])
  values = json.loads(json.dumps(schema["presets"]["recommended"]["values"]))
  first_control = next(control for control in schema["controls"]["vehicleKnobs"] if control["key"] == first_symbol)
  values["genericParams"]["SteerLatAccel"] = 1.7
  values["flmOverrides"]["vehicleKnobs"][first_symbol] = max(
    float(first_control["min"]),
    float(values["flmOverrides"]["vehicleKnobs"][first_symbol]) - 0.005,
  )
  family = schema["controls"]["frictionCurve"]["family"]
  values["flmOverrides"]["baseFrictionThresholds"][family]["values"][2] = 0.433
  fake_params_cls._store = {
    module.FLM_CUSTOM_VALUES_PARAM: True,
    "IsOnroad": False,
    "AdvancedLateralTune": False,
    "ForceAutoTune": True,
    "ForceAutoTuneOff": False,
    "UseAutoSteerDelay": True,
    "SteerDelay": 0.25,
    "SteerFriction": 0.1,
    "SteerKP": 1.0,
    "SteerLatAccel": 1.5,
    "SteerRatio": 15.0,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }

  module.apply_custom_trial(report["reportId"], values)
  module.save_active_trial_as_tune("My road tune")
  reloaded_schema = module.build_custom_trial_schema(report["reportId"])
  current = reloaded_schema["presets"]["current"]

  assert reloaded_schema["currentPresetSource"] == "active_trial"
  assert reloaded_schema["currentTrialActive"] is True
  assert reloaded_schema["defaultPreset"] == "current"
  assert current["label"] == "Current (Active Tune)"
  assert current["values"]["genericParams"] == values["genericParams"]
  assert set(current["values"]["flmOverrides"]["vehicleKnobs"]) == set(supported)
  assert current["values"]["flmOverrides"]["vehicleKnobs"][first_symbol] == pytest.approx(
    values["flmOverrides"]["vehicleKnobs"][first_symbol]
  )
  assert current["values"]["flmOverrides"]["baseFrictionThresholds"][family]["values"][2] == pytest.approx(0.433)


def test_custom_trial_validation_requires_all_knobs_and_enforces_bounds(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  report, _, _, _ = _write_custom_trial_report(module)
  schema = module.build_custom_trial_schema(report["reportId"])
  values = json.loads(json.dumps(schema["presets"][schema["defaultPreset"]]["values"]))
  first_control = schema["controls"]["vehicleKnobs"][0]

  values["flmOverrides"]["vehicleKnobs"].pop(first_control["key"])
  with pytest.raises(ValueError, match="Missing custom vehicle knob"):
    module.validate_custom_trial_values(report["reportId"], values)

  values = json.loads(json.dumps(schema["presets"][schema["defaultPreset"]]["values"]))
  values["flmOverrides"]["vehicleKnobs"][first_control["key"]] = first_control["max"] + 1
  with pytest.raises(ValueError, match="must be between"):
    module.validate_custom_trial_values(report["reportId"], values)

  values = json.loads(json.dumps(schema["presets"][schema["defaultPreset"]]["values"]))
  family = schema["controls"]["frictionCurve"]["family"]
  values["flmOverrides"]["baseFrictionThresholds"][family]["speedKnots"][0] = 1.0
  with pytest.raises(ValueError, match="speed knots cannot be changed"):
    module.validate_custom_trial_values(report["reportId"], values)

  values = json.loads(json.dumps(schema["presets"][schema["defaultPreset"]]["values"]))
  values["flmOverrides"]["hiddenField"] = True
  with pytest.raises(ValueError, match="Unknown custom FLM override"):
    module.validate_custom_trial_values(report["reportId"], values)


def test_apply_custom_trial_uses_exact_full_set_and_reverts_original_baseline(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  report, supported, first_symbol, _ = _write_custom_trial_report(module)
  schema = module.build_custom_trial_schema(report["reportId"])
  values = json.loads(json.dumps(schema["presets"][schema["defaultPreset"]]["values"]))
  first_control = next(control for control in schema["controls"]["vehicleKnobs"] if control["key"] == first_symbol)
  custom_value = min(float(first_control["max"]), max(float(first_control["min"]), float(values["flmOverrides"]["vehicleKnobs"][first_symbol]) + 0.01))
  values["flmOverrides"]["vehicleKnobs"][first_symbol] = custom_value
  baseline_overrides = {"vehicleKnobs": {"legacy.extra": 0.4}}
  fake_params_cls._store = {
    module.FLM_CUSTOM_VALUES_PARAM: True,
    "IsOnroad": False,
    "AdvancedLateralTune": False,
    "ForceAutoTune": True,
    "ForceAutoTuneOff": False,
    "UseAutoSteerDelay": True,
    "SteerDelay": 0.25,
    "SteerFriction": 0.1,
    "SteerKP": 1.0,
    "SteerLatAccel": 1.5,
    "SteerRatio": 15.0,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": baseline_overrides,
    "FLMTrialApplied": False,
  }

  result = module.apply_custom_trial(report["reportId"], values)

  assert result["profile"]["label"] == "Custom"
  assert fake_params_cls._store["AdvancedLateralTune"] is True
  assert fake_params_cls._store["ForceAutoTune"] is False
  assert fake_params_cls._store["ForceAutoTuneOff"] is True
  assert fake_params_cls._store["FLMActiveProfileId"] == f"{report['reportId']}:custom"
  assert fake_params_cls._store["FLMTrialApplied"] is True
  assert set(fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]) == set(supported)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"][first_symbol] == pytest.approx(custom_value)
  assert "legacy.extra" not in fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]

  module.revert_trial_profile()
  assert fake_params_cls._store["AdvancedLateralTune"] is False
  assert fake_params_cls._store["ForceAutoTune"] is True
  assert fake_params_cls._store["ForceAutoTuneOff"] is False
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"] == {"legacy.extra": pytest.approx(0.4)}
  assert fake_params_cls._store["FLMTrialApplied"] is False


def test_apply_and_revert_trial_profile_round_trip(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-apply"
  profile_id = f"{report_id}:recommended"
  profile = {
    "id": profile_id,
    "reportId": report_id,
    "label": "Recommended",
    "description": "Recommended trial",
    "genericParams": {
      "AdvancedLateralTune": True,
      "SteerLatAccel": 1.9,
      "ForceAutoTuneOff": True,
      "ForceAutoTune": False,
    },
    "flmOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {
        "hyundai_ioniq_6.turn_in_boost_left": 0.08,
      },
    },
  }
  (workspace["profiles"] / f"{report_id}.json").write_text(json.dumps([profile]), encoding="utf-8")

  fake_params_cls._store = {
    "AdvancedLateralTune": False,
    "ForceAutoTune": True,
    "ForceAutoTuneOff": False,
    "SteerLatAccel": 1.5,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {"hyundai_ioniq_6.unwind_taper_left": 0.55},
    },
    "FLMTrialApplied": False,
  }

  result = module.apply_trial_profile(report_id, profile_id)
  assert result["profile"]["id"] == profile_id
  active_snapshot = json.loads((workspace["snapshots"] / "active.json").read_text(encoding="utf-8"))
  assert active_snapshot["profileLabel"] == "Recommended"
  assert active_snapshot["appliedGenericParams"]["SteerLatAccel"] == pytest.approx(1.9)
  assert active_snapshot["appliedGenericParams"]["ForceAutoTuneOff"] is True
  assert active_snapshot["appliedVehicleKnobs"]["hyundai_ioniq_6.turn_in_boost_left"] == pytest.approx(0.08)
  assert active_snapshot["params"]["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.9)
  assert fake_params_cls._store["FLMActiveProfileId"] == profile_id
  assert fake_params_cls._store["FLMTrialApplied"] is True
  assert fake_params_cls._store["FLMTrialBaseline"]["params"]["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]["hyundai_ioniq_6.turn_in_boost_left"] == pytest.approx(0.08)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]["hyundai_ioniq_6.unwind_taper_left"] == pytest.approx(0.55)
  assert fake_params_cls._memory_store["StarPilotTogglesUpdated"] is True

  fake_params_cls._memory_store["StarPilotTogglesUpdated"] = False
  revert_result = module.revert_trial_profile()
  assert revert_result["snapshot"]["profileId"] == profile_id
  assert fake_params_cls._store["AdvancedLateralTune"] is False
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMTrialApplied"] is False
  assert "FLMTrialBaseline" not in fake_params_cls._store
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]["hyundai_ioniq_6.unwind_taper_left"] == pytest.approx(0.55)
  assert fake_params_cls._memory_store["StarPilotTogglesUpdated"] is True


def test_repeated_trial_revisions_revert_to_original_baseline(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  first_report_id = "report-first"
  first_profile_id = f"{first_report_id}:cleanup_pass:recommended"
  second_report_id = "report-second"
  second_profile_id = f"{second_report_id}:cleanup_pass:recommended"
  first_profile = {
    "id": first_profile_id,
    "label": "Recommended",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 1.8},
    "flmOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {"hyundai_ioniq_6.turn_in_boost_left": 0.08},
    },
  }
  second_profile = {
    "id": second_profile_id,
    "label": "Recommended",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 1.9},
    "flmOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {"hyundai_ioniq_6.unwind_taper_left": 0.62},
    },
  }
  (workspace["profiles"] / f"{first_report_id}.json").write_text(json.dumps([first_profile]), encoding="utf-8")
  (workspace["profiles"] / f"{second_report_id}.json").write_text(json.dumps([second_profile]), encoding="utf-8")
  fake_params_cls._store = {
    "AdvancedLateralTune": False,
    "SteerLatAccel": 1.5,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }

  module.apply_trial_profile(first_report_id, first_profile_id)
  module.apply_trial_profile(second_report_id, second_profile_id)

  active_snapshot = json.loads((workspace["snapshots"] / "active.json").read_text(encoding="utf-8"))
  assert active_snapshot["revisionCount"] == 2
  assert active_snapshot["params"]["SteerLatAccel"] == pytest.approx(1.5)
  assert active_snapshot["params"]["FLMTrialApplied"] is False
  assert active_snapshot["appliedGenericParams"]["SteerLatAccel"] == pytest.approx(1.9)
  assert active_snapshot["appliedVehicleKnobs"]["hyundai_ioniq_6.turn_in_boost_left"] == pytest.approx(0.08)
  assert active_snapshot["appliedVehicleKnobs"]["hyundai_ioniq_6.unwind_taper_left"] == pytest.approx(0.62)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]["hyundai_ioniq_6.turn_in_boost_left"] == pytest.approx(0.08)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]["hyundai_ioniq_6.unwind_taper_left"] == pytest.approx(0.62)

  module.revert_trial_profile()
  assert fake_params_cls._store["AdvancedLateralTune"] is False
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMTrialApplied"] is False
  assert fake_params_cls._store["FLMActiveOverrides"] == {}


def test_saved_tunes_switch_cleanly_and_revert_to_original_baseline(tmp_path, monkeypatch):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  monkeypatch.setattr(module, "_current_car_identity", lambda _params: {"carFingerprint": "TEST_CAR", "brand": "test"})

  first_report_id = "report-save-first"
  first_profile_id = f"{first_report_id}:cleanup_pass:recommended"
  second_report_id = "report-save-second"
  second_profile_id = f"{second_report_id}:cleanup_pass:recommended"
  first_profile = {
    "id": first_profile_id,
    "label": "First Trial",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {
      "AdvancedLateralTune": True,
      "SteerFriction": 0.2,
      "SteerLatAccel": 1.9,
    },
    "flmOverrides": {
      "baseFrictionThresholds": {},
      "vehicleKnobs": {"hyundai_ioniq_6.turn_in_boost_left": 0.08},
    },
  }
  second_profile = {
    "id": second_profile_id,
    "label": "Second Trial",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {
      "AdvancedLateralTune": True,
      "SteerLatAccel": 2.0,
    },
    "flmOverrides": {
      "baseFrictionThresholds": {},
      "vehicleKnobs": {"hyundai_ioniq_6.unwind_taper_left": 0.62},
    },
  }
  for report_id, profile in ((first_report_id, first_profile), (second_report_id, second_profile)):
    (workspace["reports"] / f"{report_id}.json").write_text(json.dumps({
      "reportId": report_id,
      "car": {"carFingerprint": "TEST_CAR", "brand": "test"},
    }), encoding="utf-8")
    (workspace["profiles"] / f"{report_id}.json").write_text(json.dumps([profile]), encoding="utf-8")

  fake_params_cls._store = {
    "AdvancedLateralTune": False,
    "ForceAutoTune": False,
    "ForceAutoTuneOff": True,
    "UseAutoSteerDelay": False,
    "SteerDelay": 0.35,
    "SteerFriction": 0.1,
    "SteerKP": 1.0,
    "SteerLatAccel": 1.5,
    "SteerRatio": 15.0,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }

  module.apply_trial_profile(first_report_id, first_profile_id)
  first_tune = module.save_active_trial_as_tune("No Trailer")["tune"]
  assert fake_params_cls._store["FLMActiveProfileId"] == f"saved:{first_tune['tuneId']}"
  assert next(tune for tune in module.list_workspace()["savedTunes"] if tune["tuneId"] == first_tune["tuneId"])["active"] is True
  module.revert_trial_profile()
  module.apply_trial_profile(second_report_id, second_profile_id)
  second_tune = module.save_active_trial_as_tune("With Trailer")["tune"]

  module.apply_saved_tune(first_tune["tuneId"])
  assert fake_params_cls._store["SteerFriction"] == pytest.approx(0.2)
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.9)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"] == {
    "hyundai_ioniq_6.turn_in_boost_left": pytest.approx(0.08),
  }

  module.apply_saved_tune(second_tune["tuneId"])
  assert fake_params_cls._store["SteerFriction"] == pytest.approx(0.1)
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(2.0)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"] == {
    "hyundai_ioniq_6.unwind_taper_left": pytest.approx(0.62),
  }
  workspace_state = module.list_workspace()
  assert next(tune for tune in workspace_state["savedTunes"] if tune["tuneId"] == second_tune["tuneId"])["active"] is True

  module.revert_trial_profile()
  assert fake_params_cls._store["AdvancedLateralTune"] is False
  assert fake_params_cls._store["SteerFriction"] == pytest.approx(0.1)
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMActiveOverrides"] == {}
  assert fake_params_cls._store["FLMTrialApplied"] is False


def test_saved_tune_rename_delete_and_vehicle_guard(tmp_path, monkeypatch):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  tune_id = "tune-test"
  tune_path = workspace["savedTunes"] / f"{tune_id}.json"
  tune_path.write_text(json.dumps({
    "schemaVersion": 1,
    "tuneId": tune_id,
    "name": "Original",
    "createdAt": 1.0,
    "updatedAt": 1.0,
    "carFingerprint": "CAR_A",
    "genericParams": {"SteerLatAccel": 1.9},
    "flmOverrides": {},
  }), encoding="utf-8")
  fake_params_cls._store = {
    "SteerLatAccel": 1.5,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }

  monkeypatch.setattr(module, "_current_car_identity", lambda _params: {"carFingerprint": "CAR_B", "brand": "test"})
  with pytest.raises(RuntimeError, match="connected car is CAR_B"):
    module.apply_saved_tune(tune_id)

  monkeypatch.setattr(module, "_current_car_identity", lambda _params: {"carFingerprint": "CAR_A", "brand": "test"})
  rename_result = module.rename_saved_tune(tune_id, "  Tow   Setup  ")
  assert rename_result["tune"]["name"] == "Tow Setup"
  module.apply_saved_tune(tune_id)
  with pytest.raises(RuntimeError, match="Revert or switch"):
    module.delete_saved_tune(tune_id)
  module.revert_trial_profile()
  delete_result = module.delete_saved_tune(tune_id)
  assert "Deleted saved tune Tow Setup" in delete_result["message"]
  assert not tune_path.exists()


def test_submit_saved_tune_queues_credit_and_tune_only(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  tune_id = "tune-submit"
  (workspace["savedTunes"] / f"{tune_id}.json").write_text(json.dumps({
    "schemaVersion": 1,
    "tuneId": tune_id,
    "name": "Good Curve Tune",
    "createdAt": 1.0,
    "updatedAt": 1.0,
    "carFingerprint": "HYUNDAI_IONIQ_6",
    "brand": "hyundai",
    "sourceReportId": "report-private",
    "pathLabel": "Cleanup Pass",
    "baselineParams": {"SteerLatAccel": 2.1},
    "genericParams": {"SteerLatAccel": 2.3},
    "flmOverrides": {"vehicleKnobs": {"turn_in_boost": 0.1}},
    "routeNames": ["must-not-be-submitted"],
  }), encoding="utf-8")
  fake_params_cls._store = {"IsOnroad": False}
  fake_params_cls._memory_store = {}

  result = module.submit_saved_tune(tune_id, "@tuner")
  submission = fake_params_cls._memory_store["FLMSubmittedTune"]

  assert result["carName"] == "Hyundai Ioniq 6"
  assert submission["discordUsername"] == "@tuner"
  assert submission["carName"] == "Hyundai Ioniq 6"
  assert submission["tune"]["genericParams"] == {"SteerLatAccel": 2.3}
  assert "routeNames" not in submission["tune"]
  assert "routes" not in submission["tune"]
  assert "sourceReportId" not in submission["tune"]
  assert "pathLabel" not in submission["tune"]

  with pytest.raises(ValueError, match="Discord username"):
    module.submit_saved_tune(tune_id, "")

  fake_params_cls._store["IsOnroad"] = True
  with pytest.raises(module.FLMAnalysisCancelled, match="went onroad"):
    module.submit_saved_tune(tune_id, "@tuner")


def test_saved_tune_car_switch_uses_the_destination_car_baseline(tmp_path, monkeypatch):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  tune_id = "tune-car-b"
  (workspace["savedTunes"] / f"{tune_id}.json").write_text(json.dumps({
    "schemaVersion": 1,
    "tuneId": tune_id,
    "name": "Car B",
    "createdAt": 1.0,
    "updatedAt": 1.0,
    "carFingerprint": "CAR_B",
    "baselineParams": {
      "AdvancedLateralTune": False,
      "SteerFriction": 0.08,
      "SteerLatAccel": 1.3,
      "FLMActiveProfileId": "",
      "FLMActiveOverrides": {},
      "FLMTrialApplied": False,
    },
    "genericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 2.1},
    "flmOverrides": {},
  }), encoding="utf-8")
  car_a_baseline = {
    "AdvancedLateralTune": False,
    "SteerFriction": 0.12,
    "SteerLatAccel": 1.6,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }
  (workspace["snapshots"] / "active.json").write_text(json.dumps({
    "reportId": "",
    "profileId": "saved:tune-car-a",
    "profileLabel": "Car A",
    "savedTuneId": "tune-car-a",
    "carFingerprint": "CAR_A",
    "capturedAt": 1.0,
    "params": car_a_baseline,
    "appliedGenericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 1.9},
    "appliedFrictionThresholds": {},
    "appliedVehicleKnobs": {},
  }), encoding="utf-8")
  fake_params_cls._store = {
    "AdvancedLateralTune": True,
    "SteerFriction": 0.12,
    "SteerLatAccel": 1.9,
    "FLMActiveProfileId": "saved:tune-car-a",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": True,
    "FLMTrialBaseline": {"params": car_a_baseline},
  }
  monkeypatch.setattr(module, "_current_car_identity", lambda _params: {"carFingerprint": "CAR_B", "brand": "test"})

  module.apply_saved_tune(tune_id)
  assert fake_params_cls._store["SteerFriction"] == pytest.approx(0.08)
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(2.1)
  module.revert_trial_profile()
  assert fake_params_cls._store["AdvancedLateralTune"] is False
  assert fake_params_cls._store["SteerFriction"] == pytest.approx(0.08)
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.3)


def test_orphaned_previous_revision_can_recover_its_baseline(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-recovery"
  profile_id = f"{report_id}:cleanup_pass:recommended"
  profile = {
    "id": profile_id,
    "label": "Recommended",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 1.8},
    "flmOverrides": {},
  }
  (workspace["profiles"] / f"{report_id}.json").write_text(json.dumps([profile]), encoding="utf-8")
  fake_params_cls._store = {
    "AdvancedLateralTune": False,
    "SteerLatAccel": 1.5,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }
  module.apply_trial_profile(report_id, profile_id)
  (workspace["snapshots"] / "active.json").unlink()

  active_trial = module.list_workspace()["activeTrial"]
  assert active_trial["recoveryNeeded"] is True
  assert active_trial["params"]["SteerLatAccel"] == pytest.approx(1.5)

  module.revert_trial_profile()
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMTrialApplied"] is False


def test_persistent_baseline_recovers_when_snapshot_files_are_missing(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-persistent-recovery"
  profile_id = f"{report_id}:cleanup_pass:recommended"
  profile = {
    "id": profile_id,
    "label": "Recommended",
    "genericParams": {"AdvancedLateralTune": True, "SteerLatAccel": 1.8},
    "flmOverrides": {},
  }
  (workspace["profiles"] / f"{report_id}.json").write_text(json.dumps([profile]), encoding="utf-8")
  fake_params_cls._store = {
    "AdvancedLateralTune": False,
    "SteerLatAccel": 1.5,
    "FLMActiveProfileId": "",
    "FLMActiveOverrides": {},
    "FLMTrialApplied": False,
  }

  module.apply_trial_profile(report_id, profile_id)
  for path in workspace["snapshots"].glob("*.json"):
    path.unlink()

  active_trial = module.list_workspace()["activeTrial"]
  assert active_trial["rollbackAvailable"] is True
  assert active_trial["recoveryNeeded"] is True

  module.revert_trial_profile()
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMTrialApplied"] is False


def test_legacy_orphan_recovers_baseline_from_source_report(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-source-recovery"
  profile_id = f"{report_id}:baseline_fix:assertive"
  (workspace["reports"] / f"{report_id}.json").write_text(json.dumps({
    "reportId": report_id,
    "createdAt": 123.0,
    "currentParams": {
      "AdvancedLateralTune": False,
      "SteerLatAccel": 1.5,
      "FLMActiveProfileId": "",
      "FLMActiveOverrides": {},
      "FLMTrialApplied": False,
    },
  }), encoding="utf-8")
  fake_params_cls._store = {
    "AdvancedLateralTune": True,
    "SteerLatAccel": 1.9,
    "FLMActiveProfileId": profile_id,
    "FLMActiveOverrides": {},
    "FLMTrialApplied": True,
  }

  active_trial = module.list_workspace()["activeTrial"]
  assert active_trial["rollbackAvailable"] is True
  assert active_trial["recoveryNeeded"] is True

  module.revert_trial_profile()
  assert fake_params_cls._store["AdvancedLateralTune"] is False
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.5)
  assert fake_params_cls._store["FLMTrialApplied"] is False


def test_irrecoverable_trial_can_keep_current_values_as_new_baseline(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  module.ensure_flm_workspace()
  fake_params_cls._store = {
    "AdvancedLateralTune": True,
    "SteerLatAccel": 1.9,
    "FLMActiveProfileId": "missing-report:baseline_fix:assertive",
    "FLMActiveOverrides": {"vehicleKnobs": {"generic.turn_in_boost_left": 0.1}},
    "FLMTrialApplied": True,
  }

  active_trial = module.list_workspace()["activeTrial"]
  assert active_trial["rollbackAvailable"] is False

  module.accept_trial_as_baseline()
  assert fake_params_cls._store["SteerLatAccel"] == pytest.approx(1.9)
  assert fake_params_cls._store["FLMActiveOverrides"]["vehicleKnobs"]["generic.turn_in_boost_left"] == pytest.approx(0.1)
  assert fake_params_cls._store["FLMActiveProfileId"] == ""
  assert fake_params_cls._store["FLMTrialApplied"] is False
  assert fake_params_cls._memory_store["StarPilotTogglesUpdated"] is True


def test_workspace_hydrates_display_metadata_for_existing_active_trial(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-existing"
  profile_id = f"{report_id}:cleanup_pass:recommended"
  profile = {
    "id": profile_id,
    "label": "Recommended",
    "pathKey": "cleanup_pass",
    "pathLabel": "Cleanup Pass",
    "genericParams": {"AdvancedLateralTune": True, "SteerFriction": 0.25},
    "flmOverrides": {
      "schemaVersion": 1,
      "baseFrictionThresholds": {},
      "vehicleKnobs": {"hyundai_ioniq_6.ff_gain_left": 0.15},
    },
  }
  (workspace["profiles"] / f"{report_id}.json").write_text(json.dumps([profile]), encoding="utf-8")
  (workspace["snapshots"] / "active.json").write_text(json.dumps({
    "reportId": report_id,
    "profileId": profile_id,
    "capturedAt": 123.0,
    "params": {"SteerFriction": 0.1},
  }), encoding="utf-8")

  active_trial = module.list_workspace()["activeTrial"]
  assert active_trial["pathLabel"] == "Cleanup Pass"
  assert active_trial["appliedGenericParams"]["SteerFriction"] == pytest.approx(0.25)
  assert active_trial["appliedVehicleKnobs"]["hyundai_ioniq_6.ff_gain_left"] == pytest.approx(0.15)


def test_delete_report_removes_saved_artifacts(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-delete"
  for path in (
    workspace["reports"] / f"{report_id}.json",
    workspace["reports"] / f"{report_id}.html",
    workspace["profiles"] / f"{report_id}.json",
    workspace["feedback"] / f"{report_id}.json",
    workspace["snapshots"] / f"{report_id}-recommended.json",
  ):
    path.write_text("{}", encoding="utf-8")

  result = module.delete_report(report_id)
  assert "Deleted tuning report" in result["message"]
  assert not (workspace["reports"] / f"{report_id}.json").exists()
  assert not (workspace["reports"] / f"{report_id}.html").exists()
  assert not (workspace["profiles"] / f"{report_id}.json").exists()
  assert not (workspace["feedback"] / f"{report_id}.json").exists()
  assert not (workspace["snapshots"] / f"{report_id}-recommended.json").exists()


def test_delete_report_is_blocked_while_trial_is_active(tmp_path):
  module, fake_params_cls = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-active-delete"
  report_path = workspace["reports"] / f"{report_id}.json"
  report_path.write_text("{}", encoding="utf-8")
  fake_params_cls._store = {"FLMTrialApplied": True}

  with pytest.raises(RuntimeError, match="Revert or keep"):
    module.delete_report(report_id)
  assert report_path.exists()


def test_select_report_path_persists_manual_override(tmp_path):
  module, _ = _load_flm_workspace_module(tmp_path)
  workspace = module.ensure_flm_workspace()
  report_id = "report-path"
  suggestion_base = {
    "evidence": {"speedBand": "mixed", "directionBias": "center", "eventCount": 0, "segments": []},
    "currentVsSuggested": None,
    "observedBehavior": "test",
    "likelyInterpretation": "test",
    "primaryAdjustment": "test",
    "whatNotToTouchYet": "test",
    "ifThatWasWrong": "test",
    "plotSvg": "",
  }
  cleanup_suggestion = {**suggestion_base, "dimensionId": "cleanup", "bucket": "model_limited"}
  baseline_suggestion = {**suggestion_base, "dimensionId": "baseline", "bucket": "understeer"}
  report = {
    "reportId": report_id,
    "routeNames": ["route"],
    "car": {"carFingerprint": "TEST", "controlPath": "torque", "gitBranch": "", "gitCommit": ""},
    "capabilities": {"frictionFamily": "standard", "richProfileKey": "hyundai_ioniq_6", "nonlinearTorqueMap": {}},
    "primaryPathKey": "cleanup_pass",
    "selectedPathKey": "cleanup_pass",
    "pathSelectionSource": "auto",
    "paths": [
      {"key": "cleanup_pass", "title": "Cleanup Pass", "isPrimary": True, "suggestions": [cleanup_suggestion], "profiles": []},
      {"key": "baseline_fix", "title": "Baseline Fix", "isPrimary": False, "suggestions": [baseline_suggestion], "profiles": []},
    ],
    "suggestions": [cleanup_suggestion],
    "profiles": [],
    "addTheseParametersAndStartHere": [],
  }
  (workspace["reports"] / f"{report_id}.json").write_text(json.dumps(report), encoding="utf-8")

  result = module.select_report_path(report_id, "baseline_fix")
  selected = result["report"]
  assert selected["selectedPathKey"] == "baseline_fix"
  assert selected["pathSelectionSource"] == "manual"
  assert selected["primaryPathKey"] == "cleanup_pass"
  assert selected["suggestions"] == [baseline_suggestion]
