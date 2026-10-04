"""Conventional GM pedal startup and next-drive speed-control settings."""

import os
import unittest
from unittest.mock import Mock, patch

from opendbc.car import gen_empty_fingerprint
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.radar_interface import RadarInterface
from opendbc.car.gm.values import ORDINARY_CC_CAR, is_conventional_cc_pedal_profile
from opendbc.car.gm.feature_capabilities import longitudinal_supported
from opendbc.car.gm.lateral import lane_centering_supported
from opendbc.car.gm.aol import qualified_gm
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.starpilot.longitudinal.vehicle_policy import policy_for as longitudinal_policy_for
from openpilot.starpilot.lateral.controller_selection import policy_for as lateral_policy_for
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences


def configured(identity, *, removed=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0x201: 6, 0xF1: 6, 0xBE: 6, 0xC9: 8, 0x1C4: 8, 0x1E1: 7,
                         0x3D1: 8, 0x1F5: 8, 0x184: 8, 0x34A: 5})
  if not removed:
    fingerprint[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  return CarInterface.get_params(identity, fingerprint, [], False, False, False)


class TestGmConventionalPedalStartup(unittest.TestCase):
  def test_actual_card_saved_disable_retains_lateral_and_native_ownership(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        for disabled in (False, True):
          with self.subTest(identity=identity, removed=removed, disabled=disabled), OpenpilotPrefix(), \
              patch.dict(os.environ, {'SIMULATION': '1'}):
            params = Params()
            params.put_bool('OpenpilotEnabledToggle', True, block=True)
            params.put_bool('GMPedalLongitudinal', True, block=True)
            params.put_bool('DisableOpenpilotLongitudinal', disabled, block=True)
            cp = configured(identity, removed=removed)
            self.assertTrue(is_conventional_cc_pedal_profile(cp))
            word, flags = cp.safetyConfigs[0].safetyParam, cp.flags
            card = Car(CI=CarInterface(cp), RI=RadarInterface(cp))
            self.assertEqual(card.CP.openpilotLongitudinalControl, not disabled)
            self.assertFalse(card.CP.pcmCruise)
            self.assertEqual((card.CP.safetyConfigs[0].safetyParam, card.CP.flags),
                             ((0xC186 + int(removed)) if disabled else word, flags))
            self.assertTrue(is_conventional_cc_pedal_profile(card.CP))
            self.assertTrue(lane_centering_supported(card.CP))
            self.assertTrue(qualified_gm(card.CP))
            self.assertEqual(longitudinal_supported(card.CP), not disabled)
            self.assertEqual(longitudinal_policy_for(card.CP) is not None, not disabled)
            assert lateral_policy_for(card.CP) is not None

  def test_ui_disable_and_recovery_apply_only_to_next_startup(self):
    for identity in ORDINARY_CC_CAR:
      with self.subTest(identity=identity), OpenpilotPrefix():
        params = Params()
        params.put_bool('GMPedalLongitudinal', True, block=True)
        cp = configured(identity)
        owner = FeatureSettingsOwner(params, lambda group: True,
                                     vehicle_fingerprint=lambda cp=cp: cp.carFingerprint, vehicle_params=lambda cp=cp: cp)
        view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
        self.assertTrue(row.available)
        capability = owner._bolt_disable_capability()
        request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', None, 'On', confirmation=True,
                                         vehicle_fingerprint=cp.carFingerprint, capability=capability)
        self.assertTrue(owner.apply(request))
        self.assertTrue(cp.openpilotLongitudinalControl)
        VehicleStartupPreferences.read(params, enabled=True).prepare(cp)
        self.assertFalse(cp.openpilotLongitudinalControl)
        request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', b'1', 'Off', confirmation=True,
                                         vehicle_fingerprint=cp.carFingerprint, capability=owner._bolt_disable_capability())
        self.assertTrue(owner.apply(request))
        self.assertFalse(cp.openpilotLongitudinalControl)
        next_cp = configured(identity)
        VehicleStartupPreferences.read(params, enabled=True).prepare(next_cp)
        self.assertTrue(next_cp.openpilotLongitudinalControl)

  def test_pedal_hardware_is_automatic_and_old_toggle_cannot_disable_it(self):
    from opendbc.car.gm.tests.test_conventional_pedal import params as configured_with_sensor
    with OpenpilotPrefix():
      params = Params()
      cp = configured_with_sensor(next(iter(ORDINARY_CC_CAR)), enabled=False)
      owner = FeatureSettingsOwner(params, lambda _group: True,
                                   vehicle_fingerprint=lambda: cp.carFingerprint, vehicle_params=lambda: cp)
      row = next(r for r in owner.snapshot('vehicle', parked=True, system_long=True,
                  lateral_context=True, metric=False).rows if r.key == 'GMPedalLongitudinal')
      self.assertEqual(row.value, 'Automatic')
      self.assertFalse(row.available)
      self.assertTrue(is_conventional_cc_pedal_profile(cp))
      for saved in (False, True):
        params.put_bool('GMPedalLongitudinal', saved, block=True)
        self.assertTrue(is_conventional_cc_pedal_profile(configured_with_sensor(cp.carFingerprint, enabled=saved)))
      self.assertFalse(is_conventional_cc_pedal_profile(configured_with_sensor(cp.carFingerprint, sensor=False)))

  def test_actual_native_vehicle_buttons_confirm_cancel_and_revoke(self):
    from openpilot.starpilot.ui import feature_settings_compact as compact
    from openpilot.starpilot.ui import runtime_app as large
    from openpilot.starpilot.ui.feature_settings_state import FeaturePage, FeatureRow, FeatureSettingsState
    from openpilot.system.ui.widgets import DialogResult
    class Button:
      def __init__(self, *_args): self.click = None
      def set_click_callback(self, callback): self.click = callback
    class Dialog:
      def __init__(self, _question, *_args, callback=None, **_kwargs): self.callback = callback
    for key in ('GMPedalLongitudinal', 'DisableOpenpilotLongitudinal', 'LongPitch'):
      row = FeatureRow(key, key, 'Off', source=None, available=True, choices=('Off', 'On'))
      sent, dialogs = [], []
      session = large.StarShellSession.__new__(large.StarShellSession)
      session._mode = large.ShellMode.SETTINGS
      session.selected = large.Destination.DRIVING_CONTROLS
      session.feature_page = FeaturePage.VEHICLE
      session._lane_change_request_epoch = 1
      vars(session)['feature_snapshot'] = lambda row=row: FeatureSettingsState(page=FeaturePage.VEHICLE, rows=(row,))
      vars(session)['feature_request'] = lambda request, sent=sent: sent.append(request)
      action = large.FeatureUiAction(kind='change', row=row, direction=1)
      with patch('openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog', Dialog), \
           patch.object(large.gui_app, 'push_widget', dialogs.append):
        session._feature_ui(action)
        self.assertFalse(sent)
        dialogs.pop().callback(DialogResult.CANCEL)
        self.assertFalse(sent)
        session._feature_ui(action)
        session._lane_change_request_epoch += 1
        dialogs.pop().callback(DialogResult.CONFIRM)
        self.assertFalse(sent)
        session._feature_ui(action)
        dialogs.pop().callback(DialogResult.CONFIRM)
        self.assertTrue(sent.pop().confirmation)
      page = Mock(spec=compact.NavScroller)
      adapter = compact.FeatureSettingsCompact(Mock(feature_request=lambda request, sent=sent: sent.append(request) or True))
      with patch.object(compact, 'BigButton', Button), patch.object(compact, 'ConfirmDialog', Dialog), \
           patch.object(compact.gui_app, 'get_active_widget', return_value=page), \
           patch.object(compact.gui_app, 'push_widget', dialogs.append):
        button = adapter._editable(row, lambda: None, page)[0]
        button.click()
        self.assertFalse(sent)
        dialogs.pop().callback(DialogResult.CANCEL)
        self.assertFalse(sent)
        button.click()
        dialogs.pop().callback(DialogResult.CONFIRM)
        self.assertTrue(sent.pop().confirmation)
