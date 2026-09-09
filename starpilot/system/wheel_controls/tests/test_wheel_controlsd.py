import os

from openpilot.starpilot.system.wheel_controls import wheel_controlsd


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})

  def get(self, key, encoding=None, default=None, block=False):
    del encoding, block
    return self.values.get(key, default)

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get_int(self, key, default=0):
    return int(self.values.get(key, default))

  def put(self, key, value):
    self.values[key] = value

  def put_int(self, key, value):
    self.values[key] = int(value)

  def put_bool(self, key, value):
    self.values[key] = bool(value)

  def get_float(self, key, default=0.0):
    return float(self.values.get(key, default))

  def put_float(self, key, value):
    self.values[key] = float(value)

  def remove(self, key):
    self.values.pop(key, None)


def source(name="Macro Pad"):
  return wheel_controlsd.InputSource("/dev/input/event9", "stable-device", name, 3, 0x1234, 0x5678)


def test_mapping_round_trip_and_reassignment():
  params = FakeParams()

  first = wheel_controlsd.upsert_mapping(source(), 30, 0, params)
  second = wheel_controlsd.upsert_mapping(source(), 30, 2, params)

  assert first["id"] == second["id"]
  assert params.get_bool(wheel_controlsd.ENABLED_PARAM)
  assert wheel_controlsd.load_mappings(params) == [second]
  assert wheel_controlsd.delete_mapping(second["id"], params)
  assert wheel_controlsd.load_mappings(params) == []
  assert not params.get_bool(wheel_controlsd.ENABLED_PARAM)


def test_controller_only_mapping_slots_extend_beyond_three_favorites():
  params = FakeParams()

  mapping = wheel_controlsd.upsert_mapping(source(), 30, 12, params)

  assert mapping["slot"] == 12
  assert wheel_controlsd.load_mappings(params) == [mapping]
  assert wheel_controlsd.normalize_mappings([{**mapping, "slot": 13}]) == []


def test_controller_action_slots_are_separate_and_fixed_at_ten():
  params = FakeParams()

  slots = wheel_controlsd.set_controller_action_slot(
    9, "RedneckCruise", "Redneck Cruise", params, eligible_keys={"RedneckCruise"},
  )

  assert len(slots) == 10
  assert slots[9] == {"enabled": True, "key": "RedneckCruise", "label": "Redneck Cruise", "value": None}
  assert wheel_controlsd.load_controller_action_slots(params, {"RedneckCruise"}) == slots
  assert wheel_controlsd.CONTROLLER_ACTIONS_PARAM != "StarPilotFavoriteSlots"


def test_controller_action_options_include_vehicle_controls():
  options = {option["key"]: option for option in wheel_controlsd.CONTROLLER_ACTION_OPTIONS}

  assert options[wheel_controlsd.CONTROLLER_ACTION_BOOKMARK]["label"] == "Bookmark"
  assert options[wheel_controlsd.CONTROLLER_ACTION_PULSE_AND_GLIDE]["label"] == "Pulse and Glide"
  assert options[wheel_controlsd.CONTROLLER_ACTION_FORCE_COAST]["label"] == "Force Coasting"
  assert options[wheel_controlsd.CONTROLLER_ACTION_TOGGLE_AOL]["label"] == "Toggle AOL"
  assert options[wheel_controlsd.CONTROLLER_ACTION_ENGAGE]["label"] == "Engage Openpilot"
  assert options[wheel_controlsd.CONTROLLER_ACTION_DISENGAGE]["label"] == "Disengage Openpilot"


def test_joystick_selection_is_explicit_and_exclusive():
  params = FakeParams()

  assert wheel_controlsd.selected_joystick_device(params) == ""
  assert wheel_controlsd.set_joystick_device("bluetooth-pad", True, params) == "bluetooth-pad"
  assert wheel_controlsd.selected_joystick_device(params) == "bluetooth-pad"
  assert params.get_bool(wheel_controlsd.ENABLED_PARAM)
  assert wheel_controlsd.set_joystick_device("usb-pad", True, params) == "usb-pad"
  assert wheel_controlsd.selected_joystick_device(params) == "usb-pad"
  assert wheel_controlsd.load_mappings(params) == []
  assert wheel_controlsd.set_joystick_device("usb-pad", False, params) == ""
  assert wheel_controlsd.selected_joystick_device(params) == ""
  assert not params.get_bool(wheel_controlsd.ENABLED_PARAM)


def test_favorite_mappings_keep_controller_daemon_enabled_when_joystick_is_disabled():
  params = FakeParams()
  wheel_controlsd.upsert_mapping(source("Bluetooth Controller"), 304, 0, params)

  wheel_controlsd.set_joystick_device("stable-device", True, params)
  wheel_controlsd.set_joystick_device("stable-device", False, params)

  assert params.get_bool(wheel_controlsd.ENABLED_PARAM)
  assert len(wheel_controlsd.load_mappings(params)) == 1


def test_learning_captures_next_key_without_triggering_old_mapping(monkeypatch):
  params = FakeParams({"IsOffroad": True})
  memory = FakeParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda *args: triggered.append(args[0]) or True)

  wheel_controlsd.start_learning(1, memory, params)
  daemon._update_learning(10.0)
  daemon._handle_key(source("Game Controller"), 304)

  assert triggered == []
  assert memory.get_int(wheel_controlsd.LEARN_SLOT_PARAM) == 0
  assert wheel_controlsd.load_mappings(params)[0] == {
    "id": wheel_controlsd.mapping_id("stable-device", 304),
    "device_id": "stable-device",
    "device_name": "Game Controller",
    "event_code": 304,
    "event_name": "BTN_SOUTH",
    "slot": 1,
  }
  daemon.close()


def test_mapped_key_triggers_once(monkeypatch):
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams()
  wheel_controlsd.upsert_mapping(source(), 30, 2, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda slot, *_args: triggered.append(slot) or True)

  daemon._handle_key(source(), 30)
  daemon._handle_key(source(), 31)

  assert triggered == [2]
  daemon.close()


def test_mapped_controller_action_dispatches_without_using_a_favorite_slot(monkeypatch):
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams()
  wheel_controlsd.upsert_mapping(source(), 30, 3, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  favorite_triggered = []
  controller_triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda slot, *_args: favorite_triggered.append(slot) or True)
  monkeypatch.setattr(wheel_controlsd, "execute_controller_action", lambda slot, *_args: controller_triggered.append(slot) or True)

  daemon._handle_key(source(), 30)

  assert favorite_triggered == []
  assert controller_triggered == [0]
  daemon.close()


def test_controller_set_speed_uses_current_display_units_and_requires_engagement():
  memory = FakeParams()
  params = FakeParams({"IsOnroad": True, "IsEngaged": True, "IsMetric": False})

  assert wheel_controlsd.set_controller_cruise_speed(60, params, memory)
  assert memory.get_float("SLCForceCruiseSpeed") == 60 * wheel_controlsd.CV.MPH_TO_MS

  params.values["IsMetric"] = True
  assert wheel_controlsd.set_controller_cruise_speed(30, params, memory)
  assert memory.get_float("SLCForceCruiseSpeed") == 30 * wheel_controlsd.CV.KPH_TO_MS

  params.values["IsEngaged"] = False
  memory.remove("SLCForceCruiseSpeed")
  assert not wheel_controlsd.set_controller_cruise_speed(60, params, memory)
  assert "SLCForceCruiseSpeed" not in memory.values


def test_controller_custom_actions_dispatch_their_own_payload(monkeypatch):
  params = FakeParams({
    wheel_controlsd.CONTROLLER_ACTIONS_PARAM: [
      {
        "enabled": True,
        "key": wheel_controlsd.CONTROLLER_ACTION_SET_SPEED,
        "label": "Set Speed To",
        "value": 60,
      },
      {
        "enabled": True,
        "key": wheel_controlsd.CONTROLLER_ACTION_SELFIE,
        "label": "Take Comma Selfie",
      },
    ],
  })
  memory = FakeParams()
  speeds = []
  selfies = []
  monkeypatch.setattr(wheel_controlsd, "set_controller_cruise_speed", lambda value, *_args: speeds.append(value) or True)
  monkeypatch.setattr(wheel_controlsd, "request_comma_selfie", lambda: selfies.append(True) or True)

  assert wheel_controlsd.execute_controller_action(0, params, memory)
  assert wheel_controlsd.execute_controller_action(1, params, memory)
  assert speeds == [60]
  assert selfies == [True]


def test_controller_actions_trigger_runtime_counters():
  params = FakeParams({
    wheel_controlsd.CONTROLLER_ACTIONS_PARAM: [
      {"enabled": True, "key": wheel_controlsd.CONTROLLER_ACTION_BOOKMARK, "label": "Bookmark"},
      {"enabled": True, "key": wheel_controlsd.CONTROLLER_ACTION_PULSE_AND_GLIDE, "label": "Pulse and Glide"},
      {"enabled": True, "key": wheel_controlsd.CONTROLLER_ACTION_FORCE_COAST, "label": "Force Coasting"},
      {"enabled": True, "key": wheel_controlsd.CONTROLLER_ACTION_TOGGLE_AOL, "label": "Toggle AOL"},
    ],
  })
  memory = FakeParams()

  for index in range(4):
    assert wheel_controlsd.execute_controller_action(index, params, memory)

  assert memory.values == {
    "WheelButtonBookmarkCounter": 1,
    "WheelControlPulseGlideCounter": 1,
    "WheelControlForceCoastCounter": 1,
    "WheelControlAOLCounter": 1,
  }


def test_controller_openpilot_actions_require_onroad_and_use_independent_counters():
  params = FakeParams({
    wheel_controlsd.CONTROLLER_ACTIONS_PARAM: [
      {"enabled": True, "key": wheel_controlsd.CONTROLLER_ACTION_ENGAGE, "label": "Engage Openpilot"},
      {"enabled": True, "key": wheel_controlsd.CONTROLLER_ACTION_DISENGAGE, "label": "Disengage Openpilot"},
    ],
  })
  memory = FakeParams()

  assert not wheel_controlsd.execute_controller_action(0, params, memory)
  assert memory.values == {}

  params.values["IsOnroad"] = True
  assert wheel_controlsd.execute_controller_action(0, params, memory)
  assert wheel_controlsd.execute_controller_action(1, params, memory)
  assert memory.values == {
    "WheelControlEngageCounter": 1,
    "WheelControlDisengageCounter": 1,
  }


def test_learning_accepts_the_tenth_controller_action():
  params = FakeParams({"IsOffroad": True})
  memory = FakeParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)

  wheel_controlsd.start_learning(12, memory, params)
  daemon._update_learning(10.0)

  assert daemon.learning_slot == 12
  assert memory.get_int(wheel_controlsd.LEARN_SLOT_PARAM) == 13
  daemon.close()


def test_selected_joystick_controller_does_not_trigger_favorites(monkeypatch):
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams()
  wheel_controlsd.upsert_mapping(source("Game Controller"), 304, 0, params)
  wheel_controlsd.set_joystick_device("stable-device", True, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda slot, *_args: triggered.append(slot) or True)

  daemon._handle_key(source("Game Controller"), 304)
  assert triggered == []

  wheel_controlsd.set_joystick_device("stable-device", False, params)
  daemon._handle_key(source("Game Controller"), 304)
  assert triggered == [0]
  daemon.close()


def test_only_key_down_is_dispatched(monkeypatch):
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams()
  wheel_controlsd.upsert_mapping(source(), 30, 0, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda slot, *_args: triggered.append(slot) or True)
  read_fd, write_fd = os.pipe()
  os.set_blocking(read_fd, False)
  daemon.sources[read_fd] = source()
  daemon.buffers[read_fd] = bytearray()

  for value in (1, 2, 0):
    os.write(write_fd, wheel_controlsd.INPUT_EVENT.pack(0, 0, wheel_controlsd.EV_KEY, 30, value))
  daemon._read_events(read_fd)

  assert triggered == [0]
  os.close(write_fd)
  daemon.close()


def test_stale_selector_event_after_controller_disconnect_is_ignored():
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  read_fd, write_fd = os.pipe()
  os.set_blocking(read_fd, False)
  os.write(write_fd, wheel_controlsd.INPUT_EVENT.pack(0, 0, wheel_controlsd.EV_KEY, 30, 1))

  daemon._read_events(read_fd)

  assert read_fd not in daemon.sources
  assert read_fd not in daemon.buffers
  os.close(write_fd)
  daemon.close()


def test_learning_is_cancelled_onroad():
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams({wheel_controlsd.LEARN_SLOT_PARAM: 1})
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)

  daemon._update_learning(10.0)

  assert daemon.learning_slot is None
  assert memory.get_int(wheel_controlsd.LEARN_SLOT_PARAM) == 0
  daemon.close()


def test_only_usb_and_bluetooth_input_buses_are_accepted(monkeypatch):
  values = {
    "modalias": "input:b0003v1234p5678e0001-e0,1,k110,",
    "name": "USB Macro Pad",
    "phys": "usb-1/input0",
    "uniq": "",
  }
  monkeypatch.setattr(wheel_controlsd, "_read_text", lambda path: values.get(path.name, ""))

  external = wheel_controlsd.inspect_input_source("/dev/input/event9")
  assert external is not None
  assert external.name == "USB Macro Pad"

  values["modalias"] = "input:b0018v0000p0000e0000-e0,1,k74,"
  assert wheel_controlsd.inspect_input_source("/dev/input/event2") is None


def test_media_and_gamepad_button_names_are_supported():
  assert wheel_controlsd.event_name(115) == "KEY_VOLUMEUP"
  assert wheel_controlsd.event_name(164) == "KEY_PLAYPAUSE"
  assert wheel_controlsd.event_name(304) == "BTN_SOUTH"
  assert wheel_controlsd.event_name(wheel_controlsd.hat_event_code(wheel_controlsd.ABS_HAT0X, -1)) == "DPAD_LEFT"
  assert wheel_controlsd.event_name(wheel_controlsd.hat_event_code(wheel_controlsd.ABS_HAT0X, 1)) == "DPAD_RIGHT"
  assert wheel_controlsd.event_name(wheel_controlsd.hat_event_code(wheel_controlsd.ABS_HAT0X + 1, -1)) == "DPAD_UP"
  assert wheel_controlsd.event_name(wheel_controlsd.hat_event_code(wheel_controlsd.ABS_HAT0X + 1, 1)) == "DPAD_DOWN"


def test_dpad_hat_axes_are_dispatched_once_per_press(monkeypatch):
  params = FakeParams({"IsOffroad": False})
  memory = FakeParams()
  left = wheel_controlsd.hat_event_code(wheel_controlsd.ABS_HAT0X, -1)
  wheel_controlsd.upsert_mapping(source("Game Controller"), left, 1, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda slot, *_args: triggered.append(slot) or True)
  read_fd, write_fd = os.pipe()
  os.set_blocking(read_fd, False)
  daemon.sources[read_fd] = source("Game Controller")
  daemon.buffers[read_fd] = bytearray()

  for value in (-1, -1, 0, -1):
    os.write(write_fd, wheel_controlsd.INPUT_EVENT.pack(0, 0, wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, value))
  daemon._read_events(read_fd)

  assert triggered == [1, 1]
  os.close(write_fd)
  daemon.close()


def test_button_test_mode_eats_mapped_and_unmapped_inputs(monkeypatch):
  params = FakeParams({"IsOffroad": True})
  memory = FakeParams()
  wheel_controlsd.upsert_mapping(source(), 164, 0, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  # Isolate HID routing here; real receipt dispatch is covered by test_action_feedback.
  monkeypatch.setattr(daemon.feedback, "execute", lambda slot, _: wheel_controlsd.execute_mapping_slot(slot, params, memory))
  triggered = []
  monkeypatch.setattr(wheel_controlsd, "execute_favorite_slot", lambda slot, *_args: triggered.append(slot) or True)

  wheel_controlsd.start_testing(memory, params)
  daemon._update_testing()
  daemon._handle_key(source(), 164)
  assert triggered == []
  assert daemon.last_tested == {
    "mapped": True,
    "device_name": "Macro Pad",
    "event_code": 164,
    "event_name": "KEY_PLAYPAUSE",
    "slot": 0,
  }

  daemon._handle_key(source(), 165)
  assert triggered == []
  assert daemon.last_tested["mapped"] is False

  wheel_controlsd.stop_testing(memory)
  daemon._update_testing()
  daemon._handle_key(source(), 164)
  assert triggered == [0]
  daemon.close()


def test_button_test_mode_stops_onroad():
  params = FakeParams({"IsOffroad": True})
  memory = FakeParams()
  wheel_controlsd.upsert_mapping(source(), 30, 0, params)
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  wheel_controlsd.start_testing(memory, params)
  daemon._update_testing()
  assert daemon.testing

  params.values["IsOffroad"] = False
  daemon._update_testing()
  assert not daemon.testing
  assert not memory.get_bool(wheel_controlsd.TEST_ACTIVE_PARAM)
  daemon.close()
