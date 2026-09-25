"""GM distance Traffic assignments and stock Ioniq Switchback stay independent."""
from types import SimpleNamespace as NS
from pathlib import Path
from openpilot.common.params import Params
from opendbc.car.gm.tests.test_bolt_pedal import params as gm_params
from opendbc.car.gm.values import CAR as GM
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
from openpilot.starpilot.conditional_mode.button_actions import BUTTON_PREFIX


def test_gm_distance_and_stock_ioniq_switchback_are_separate_source_bound_requests(tmp_path):
  params = Params(str(tmp_path))
  current = NS(cp=gm_params(GM.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, setting=True, pedal=True))
  owner = FeatureSettingsOwner(params, lambda group: group in ('conditional_wheel', 'switchback_wheel', 'preferences'),
                              vehicle_fingerprint=lambda: current.cp.carFingerprint,
                              vehicle_params=lambda: current.cp)
  def request(row, choice):
    return FeatureSettingsRequest(row.key, row.source, choice, vehicle_fingerprint=row.vehicle_fingerprint,
                                  capability=row.capability, dependencies=row.dependencies)
  rows = owner.conditional.wheel_rows()
  distance = next(row for row in rows if row.key == BUTTON_PREFIX+'DistanceButtonControl')
  assert distance.choices == ('Off', 'Toggle traffic mode') and distance.available
  captured_gm = request(distance, 'Toggle traffic mode')
  assert owner.apply(captured_gm)
  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  cp.flags = int(cp.flags | HyundaiFlags.CANFD_LKA_STEER_MSG)
  cp.openpilotLongitudinalControl = False
  current.cp = cp
  assert not owner.apply(captured_gm)
  rows = owner.conditional.wheel_rows()
  assert not any(row.key == BUTTON_PREFIX+'DistanceButtonControl' for row in rows)
  mode = next(row for row in rows if row.key == BUTTON_PREFIX+'ModeButtonControl')
  assert mode.choices == ('Off', 'Switchback Mode') and mode.available
  assert owner.apply(request(mode, 'Switchback Mode'))
  assert Path(params.get_param_path('ModeButtonControl')).read_bytes() == b'7'
  assert Path(params.get_param_path('DistanceButtonControl')).read_bytes() == b'6'
  other = next(row for row in owner.conditional.wheel_rows() if row.key == BUTTON_PREFIX+'LongModeButtonControl')
  captured_media = request(other, 'Switchback Mode')
  cp.flags = int(cp.flags & ~HyundaiFlags.CANFD_LKA_STEER_MSG)
  assert not owner.apply(captured_media)
  assert not Path(params.get_param_path('LongModeButtonControl')).exists()
