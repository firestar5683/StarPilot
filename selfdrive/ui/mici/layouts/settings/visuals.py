from openpilot.common.params import Params
from openpilot.selfdrive.ui.lib.starpilot_visuals import lead_indicator_enabled
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigParamControl, BigToggle
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigMultiOptionDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller

CAMERA_VIEW_LABELS = ["Auto", "Driver", "Standard", "Wide", "None"]


class CameraViewBigButton(BigButton):
  def __init__(self):
    super().__init__("camera view", "", gui_app.texture("icons_mici/onroad/eye_fill.png", 64, 64))
    self._params = Params()
    self.set_click_callback(self._show_selector)
    self.refresh()

  def refresh(self):
    current_idx = self._params.get_int("CameraView", return_default=True, default=2)
    current_idx = max(0, min(current_idx, len(CAMERA_VIEW_LABELS) - 1))
    self.set_value(CAMERA_VIEW_LABELS[current_idx].lower())

  def _show_selector(self):
    current_idx = self._params.get_int("CameraView", return_default=True, default=2)
    current_idx = max(0, min(current_idx, len(CAMERA_VIEW_LABELS) - 1))
    dialog_holder: dict[str, BigMultiOptionDialog] = {}

    def on_confirm():
      try:
        idx = CAMERA_VIEW_LABELS.index(dialog_holder["dialog"].get_selected_option())
      except ValueError:
        gui_app.push_widget(BigDialog("", "Invalid camera view"))
        return
      self._params.put_int("CameraView", idx)
      self.refresh()

    dialog = BigMultiOptionDialog(options=CAMERA_VIEW_LABELS, default=CAMERA_VIEW_LABELS[current_idx], right_btn_callback=on_confirm)
    dialog_holder["dialog"] = dialog
    gui_app.push_widget(dialog)


class LeadIndicatorBigButton(BigToggle):
  def __init__(self):
    super().__init__("lead indicator")
    self.params = Params()
    self.refresh()

  def _handle_mouse_release(self, mouse_pos):
    super()._handle_mouse_release(mouse_pos)
    self.params.put_bool("HideLeadMarker", not self._checked)

  def refresh(self):
    self.set_checked(lead_indicator_enabled(self.params, hide_by_default=True))


class VisualsLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._camera_view_btn = CameraViewBigButton()
    self._driver_camera_btn = BigParamControl("driver camera on reverse", "DriverCamera")
    self._stopped_timer_btn = BigParamControl("stopped timer", "StoppedTimer")
    self._stock_confidence_ball_btn = BigParamControl("stock confidence ball", "StockConfidenceBallWidget")
    self._torque_bar_btn = BigParamControl("torque bar", "EnableTorqueBarWidget")
    self._rainbow_path_btn = BigParamControl("rainbow road", "RainbowPath")
    self._lead_indicator_btn = LeadIndicatorBigButton()
    self._lead_info_btn = BigParamControl("show lead speed", "LeadInfo")
    self._speed_limit_signs_btn = BigParamControl("show speed limits", "ShowSpeedLimits")
    self._slc_confirmation_btn = BigParamControl("confirm new speed limits", "SLCConfirmation")
    self._slc_confirmation_lower_btn = BigParamControl("confirm lower limits", "SLCConfirmationLower")
    self._slc_confirmation_higher_btn = BigParamControl("confirm higher limits", "SLCConfirmationHigher")

    self._scroller.add_widgets([
      self._camera_view_btn,
      self._driver_camera_btn,
      self._stopped_timer_btn,
      self._stock_confidence_ball_btn,
      self._torque_bar_btn,
      self._rainbow_path_btn,
      self._lead_indicator_btn,
      self._lead_info_btn,
      self._speed_limit_signs_btn,
      self._slc_confirmation_btn,
      self._slc_confirmation_lower_btn,
      self._slc_confirmation_higher_btn,
    ])

  def show_event(self):
    super().show_event()
    self._refresh()

  def _update_state(self):
    super()._update_state()
    self._refresh()

  def _refresh(self):
    self._camera_view_btn.refresh()
    self._lead_indicator_btn.refresh()
    self._lead_info_btn.set_enabled(lead_indicator_enabled(self._lead_info_btn.params, hide_by_default=True))
    confirmation_enabled = self._slc_confirmation_btn.params.get_bool("SLCConfirmation")
    self._slc_confirmation_lower_btn.set_visible(confirmation_enabled)
    self._slc_confirmation_higher_btn.set_visible(confirmation_enabled)
