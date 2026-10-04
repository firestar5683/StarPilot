"""Large vehicle-selection presentation over the shared saved-choice owner."""

from collections import Counter

from openpilot.starpilot.ui.feature_settings_state import FeaturePage, FeatureRow
from openpilot.starpilot.ui.settings_state import Destination
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.vehicle_selection import VehicleSelectionOwner

SELECTION_PAGE = "vehicle:selection"


class VehicleLarge:
  def __init__(self, session):
    self.session = session
    self.owner = VehicleSelectionOwner(session.adapter.ui_state.params, session.confirmed_offroad)
    self.catalog = self.owner.choices()
    self.labels = {choice.platform: choice.label for choice in self.catalog}

  def rows(self) -> tuple[FeatureRow, ...]:
    saved = self.owner.snapshot()
    cp = self.session.adapter.ui_state.CP
    reported = self.labels.get(getattr(cp, "carFingerprint", None), "Not detected") if not getattr(cp, "notCar", False) else "Not detected"
    selected = (self.labels.get(saved.platform, "Auto detection") if saved.valid else
                "Needs review" if saved.readable else "Unavailable")
    return (FeatureRow("", "Reported vehicle", reported),
            FeatureRow("", "Vehicle selection", selected, source=saved.raw, page=SELECTION_PAGE, available=saved.readable,
                       reason="Applies at next startup" if self.owner.parked() else "Parked state required to save"))

  def open(self, expected: bytes | None) -> None:
    from openpilot.system.ui.lib.application import gui_app
    from openpilot.system.ui.widgets import DialogResult
    from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

    saved = self.owner.snapshot()
    if not saved.readable or saved.raw != expected:
      self.session._unavailable("Vehicle selection changed; reopen settings")
      return
    epoch = self.session._lane_change_request_epoch

    def active():
      return (self.session._mode == ShellMode.SETTINGS and self.session.selected == Destination.DRIVING_CONTROLS and
              self.session.feature_page == FeaturePage.VEHICLE and self.session._lane_change_request_epoch == epoch)

    def save(platform):
      if not active():
        return
      owner = VehicleSelectionOwner(self.owner.params, lambda: active() and self.owner.parked())
      result = owner.choose(expected, platform)
      self.session._snapshot_cache = None
      if not result.verified:
        self.session._unavailable("Vehicle selection not verified; park and reopen settings")

    def models(make):
      choices = [choice for choice in self.catalog if choice.make == make]
      counts = Counter(choice.label for choice in choices)
      options = {choice.label if counts[choice.label] == 1 else f"{choice.label} ({choice.platform})": choice.platform
                 for choice in choices}
      current = next((label for label, platform in options.items() if platform == saved.platform), "")
      def selected(result):
        if result == DialogResult.CONFIRM and picker.selection in options:
          save(options[picker.selection])
      picker = MultiOptionDialog(f"Select {make} model", list(options), current, callback=selected)
      gui_app.push_widget(picker)

    makes = sorted({choice.make for choice in self.catalog})
    def selected(result):
      if result != DialogResult.CONFIRM or not active():
        return
      if picker.selection == "Auto detection":
        save(None)
      elif picker.selection in makes:
        models(picker.selection)
    picker = MultiOptionDialog("Vehicle selection", ["Auto detection", *makes], callback=selected)
    gui_app.push_widget(picker)
