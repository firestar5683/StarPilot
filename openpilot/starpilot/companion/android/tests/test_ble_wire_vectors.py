"""The Android app and the phone bridge must agree on the encrypted BLE wire format."""
import json
from pathlib import Path
import sys

import pytest

ANDROID = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANDROID.parents[1] / 'galaxy_bluetooth/bridge'))
import protocol


def test_android_wire_vectors():
  # These fixtures are also consumed by BleWireTest on the JVM.
  root = ANDROID / 'app/src/test/resources/ble'
  key = bytes(range(32))
  for name in ('plain', 'compressed', 'compact'):
    frame = bytes.fromhex((root / f'{name}.hex').read_text())
    expected = json.loads((root / f'{name}.json').read_text())
    assert protocol.open_message(frame[4:], key, 'response') == expected
  frame = bytes.fromhex((root / 'request.hex').read_text())
  assert protocol.open_message(frame[4:], key, 'request') == {'method': 'GET', 'path': '/api/companion/status'}
  with pytest.raises(ValueError):
    protocol.open_message(frame[4:], key, 'response')
