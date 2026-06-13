from cereal import log

from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigParamControl, BigMultiParamToggle
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.ui.layouts.settings.common import restart_needed_callback
from openpilot.selfdrive.ui.ui_state import ui_state

PERSONALITY_TO_INT = log.LongitudinalPersonality.schema.enumerants


class TogglesLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._sync_rhd_toggle()

    def rhd_toggle_callback(checked: bool):
      ui_state.params.put_bool("IsRHD", checked)
      ui_state.params.put_bool("IsRHDOverride", True)

    self._personality_toggle = BigMultiParamToggle("driving personality", "LongitudinalPersonality", ["aggressive", "standard", "relaxed"])
    self._safe_mode_btn = BigParamControl("safe mode", "SafeMode", toggle_callback=restart_needed_callback)
    self._experimental_btn = BigParamControl("experimental mode", "ExperimentalMode")
    is_metric_toggle = BigParamControl("use metric units", "IsMetric")
    ldw_toggle = BigParamControl("lane departure warnings", "IsLdwEnabled")
    always_on_dm_toggle = BigParamControl("always-on driver monitor", "AlwaysOnDM")
    rhd_toggle = BigParamControl("right hand driving", "IsRHD", toggle_callback=rhd_toggle_callback)
    record_front = BigParamControl("record & upload driver camera", "RecordFront", toggle_callback=restart_needed_callback)
    record_mic = BigParamControl("record & upload mic audio", "RecordAudio", toggle_callback=restart_needed_callback)
    enable_openpilot = BigParamControl("enable openpilot", "OpenpilotEnabledToggle", toggle_callback=restart_needed_callback)

    self._scroller.add_widgets([
      self._personality_toggle,
      self._safe_mode_btn,
      self._experimental_btn,
      is_metric_toggle,
      ldw_toggle,
      always_on_dm_toggle,
      rhd_toggle,
      record_front,
      record_mic,
      enable_openpilot,
    ])

    # Toggle lists
    self._refresh_toggles = (
      ("ExperimentalMode", self._experimental_btn),
      ("SafeMode", self._safe_mode_btn),
      ("IsMetric", is_metric_toggle),
      ("IsLdwEnabled", ldw_toggle),
      ("AlwaysOnDM", always_on_dm_toggle),
      ("IsRHD", rhd_toggle),
      ("RecordFront", record_front),
      ("RecordAudio", record_mic),
      ("OpenpilotEnabledToggle", enable_openpilot),
    )

    enable_openpilot.set_enabled(lambda: not ui_state.engaged)
    record_front.set_enabled(False if ui_state.params.get_bool("RecordFrontLock") else (lambda: not ui_state.engaged))
    record_mic.set_enabled(lambda: not ui_state.engaged)

    if ui_state.params.get_bool("ShowDebugInfo"):
      gui_app.set_show_touches(True)
      gui_app.set_show_fps(True)

    ui_state.add_engaged_transition_callback(self._update_toggles)

  def _update_state(self):
    super()._update_state()

    if ui_state.sm.updated["selfdriveState"]:
      personality = PERSONALITY_TO_INT[ui_state.sm["selfdriveState"].personality]
      if personality != ui_state.personality and ui_state.started:
        self._personality_toggle.set_value(self._personality_toggle._options[personality])
      ui_state.personality = personality

  def show_event(self):
    super().show_event()
    self._update_toggles()

  def _update_toggles(self):
    ui_state.update_params()
    self._sync_rhd_toggle()
    safe_mode = ui_state.params.get_bool("SafeMode")
    self._experimental_btn.set_enabled(not safe_mode)
    self._personality_toggle.set_enabled(not safe_mode)
    if safe_mode:
      if ui_state.params.get_bool("ExperimentalMode"):
        ui_state.params.put_bool("ExperimentalMode", False)
      if ui_state.params.get("LongitudinalPersonality", return_default=True) != int(log.LongitudinalPersonality.relaxed):
        ui_state.params.put_int("LongitudinalPersonality", int(log.LongitudinalPersonality.relaxed))
      self._experimental_btn.set_checked(False)
      self._personality_toggle.set_value("relaxed")

    # CP gating for experimental mode
    if ui_state.CP is not None:
      if ui_state.has_longitudinal_control:
        self._experimental_btn.set_visible(True)
        self._personality_toggle.set_visible(True)
      else:
        # no long for now
        self._experimental_btn.set_visible(False)
        self._experimental_btn.set_checked(False)
        self._personality_toggle.set_visible(False)
        self._experimental_btn.set_enabled(False)
        self._personality_toggle.set_enabled(False)
        ui_state.params.remove("ExperimentalMode")

    # Refresh toggles from params to mirror external changes
    for key, item in self._refresh_toggles:
      item.set_checked(ui_state.params.get_bool(key))

  def _sync_rhd_toggle(self):
    if not ui_state.params.get_bool("IsRHDOverride"):
      ui_state.params.put_bool("IsRHD", ui_state.params.get_bool("IsRhdDetected"))
