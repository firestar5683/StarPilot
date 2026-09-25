"""Developer-only, offroad selection of the next-boot cloud provider."""

from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigConfirmationCircleButton
from openpilot.selfdrive.ui.mici.widgets.qr import QR
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.starpilot.connect.provider import PROVIDERS, active_provider, select_provider, status


class CloudProviderConfirmation(NavScroller):
  def __init__(self, name, revision, completed):
    super().__init__()
    def confirm():
      try:
        select_provider(name, revision, ui_state.is_offroad)
      except (OSError, ValueError, TypeError):
        gui_app.push_widget(BigDialog('', 'Cloud selection changed or the vehicle is on. Refresh and try again.'))
        return
      self.dismiss(completed)
    accept = BigConfirmationCircleButton('use after\nnext reboot', gui_app.texture('icons_mici/setup/driver_monitoring/dm_check.png', 64, 64), confirm)
    accept.set_enabled(ui_state.is_offroad)
    self._scroller.add_widgets([
      GreyBigButton('Cloud Provider', f'Use {PROVIDERS[name].label} after the next device reboot. No automatic reboot.'),
      GreyBigButton('', 'Cloud accounts stay separate. Returning to comma restores its saved identity.'),
      accept,
    ])


class CloudProviderPage(NavScroller):
  def __init__(self):
    super().__init__()
    try:
      current = status()
    except (OSError, ValueError, TypeError):
      self._scroller.add_widgets([GreyBigButton('Cloud Unavailable', 'Repair the saved provider configuration before choosing a cloud.')])
      return
    active = active_provider()
    self._scroller.add_widgets([
      GreyBigButton('Developer: Cloud Provider', f'Active: {active.label}. Next boot: {PROVIDERS[current["selected"]].label}.'),
      GreyBigButton('', 'Changes apply after a device reboot. Turn off the vehicle first.'),
      QR(active.web),
    ])
    for provider in PROVIDERS.values():
      button = BigButton(f'Use {provider.label}', 'Next boot only')
      button.set_enabled(lambda name=provider.name: ui_state.is_offroad() and name != current['selected'])
      button.set_click_callback(lambda name=provider.name: gui_app.push_widget(
        CloudProviderConfirmation(name, current['revision'], lambda: self.dismiss(lambda: gui_app.push_widget(CloudProviderPage())))))
      self._scroller.add_widgets([button])
