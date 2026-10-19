"""Global feature availability never validates a malformed native CarParams."""
import pytest

from opendbc.car.gm.tests.test_silverado_cc_pedal import params as silverado_params
from opendbc.car.gm.values import CAR
from openpilot.common.params import Params
from openpilot.starpilot.feature_capabilities import display_supported, longitudinal_supported
from openpilot.starpilot.feature_runtime import enabled, slc_runtime_settings, slc_transport_capable, vision_control_enabled
from openpilot.starpilot.speed_limits.vision_gate import diagnostic_choice_enabled


@pytest.mark.parametrize('removed', [False, True])
@pytest.mark.parametrize('disabled', [False, True])
def test_native_silverado_configuration_is_required_for_global_features(tmp_path, removed, disabled):
  params = Params(str(tmp_path))
  params.put_bool('CurveSpeedController', True, block=True)
  params.put_bool('SpeedLimitController', True, block=True)
  cp = silverado_params(removed=removed, disabled=disabled)
  assert display_supported(cp)
  assert longitudinal_supported(cp) is not disabled
  for feature in ('conditional', 'curve', 'profile'):
    assert enabled(params, cp, feature, {}) is not disabled
  for feature in ('slc', 'vision'):
    assert enabled(params, cp, feature, {})
  settings = slc_runtime_settings(params, cp, {})
  assert settings.enabled is not disabled
  assert vision_control_enabled(params, cp) is not disabled
  if disabled:
    assert settings.display and settings.acceptance.display_only
  for mutation in ('word', 'identity', 'dashcam', 'flags'):
    bad = cp.as_reader().as_builder()
    if mutation == 'word':
      bad.safetyConfigs[0].safetyParam ^= 8
    elif mutation == 'identity':
      bad.carFingerprint = CAR.CADILLAC_CT6_CC
    elif mutation == 'dashcam':
      bad.dashcamOnly = True
    else:
      bad.flags |= 1 << 30
    assert not display_supported(bad), mutation
    assert not longitudinal_supported(bad), mutation
    for feature in ('conditional', 'curve', 'profile', 'slc', 'vision'):
      assert not enabled(params, bad, feature, {}), (mutation, feature)
    assert not slc_transport_capable(bad, {}), mutation
    assert not diagnostic_choice_enabled({}, bad), mutation
    assert not vision_control_enabled(params, bad), mutation
    assert not slc_runtime_settings(params, bad, {}).enabled, mutation
