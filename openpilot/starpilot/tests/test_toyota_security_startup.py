"""Malformed saved SecOC credentials never terminate actual Card startup."""

import os
import builtins
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from opendbc.car import gen_empty_fingerprint
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car


@pytest.mark.parametrize('key', ['invalid hexadecimal', 'a' * 31, 'ab' * 16])
def test_actual_card_key_loading_is_bounded_and_malformed_safe(key):
  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
    params = Params()
    params.put_bool('OpenpilotEnabledToggle', True, block=True)
    params.put('SecOCKey', key, block=True)
    cp = CarInterface.get_params(CAR.TOYOTA_RAV4_PRIME, gen_empty_fingerprint(), [], True, False, False)
    assert cp.secOcRequired
    def discover(*args, pre_create_hook, **kwargs):
      return CarInterface(pre_create_hook(cp.as_reader().as_builder(), cp.carFingerprint, {}, []))
    original_open = builtins.open
    def without_key_cache(path, *args, **kwargs):
      if str(path) == '/cache/params/SecOCKey':
        raise FileNotFoundError
      return original_open(path, *args, **kwargs)
    with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
         patch('openpilot.selfdrive.car.card.get_car', side_effect=discover), \
         patch('builtins.open', side_effect=without_key_cache):
      selected = Car()
    assert selected.CP.secOcKeyAvailable == (key == 'ab' * 16)
    if selected.CP.secOcKeyAvailable:
      assert selected.CI.CS.secoc_key == bytes([171] * 16)
      if selected.CI.CC is not None:
        assert selected.CI.CC.secoc_key == bytes([171] * 16)
