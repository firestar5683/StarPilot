"""Device management stays usable onroad; radio service restart stays parked."""
import tempfile
from pathlib import Path
from unittest.mock import Mock
import pytest
from openpilot.starpilot.bluetooth.owner import BluetoothOwner, BluetoothRejected
from openpilot.starpilot.bluetooth.radio_preference import RadioPreference
from openpilot.starpilot.bluetooth.tests.test_owner import FakeBlueZ, FakeTimer


def test_actual_owner_runtime_operations_and_restart_gate():
  with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    helper = root / 'bluetooth-radio'
    helper.write_bytes(b'helper')
    FakeBlueZ.devices = [{'address': 'AA:BB:CC:DD:EE:FF', 'name': 'car', 'paired': True,
                         'connected': False, 'trusted': True}]
    FakeBlueZ.operations = []
    owner = BluetoothOwner(lambda: False, bluez_factory=FakeBlueZ, radio_helper=helper,
                           systemctl=Mock(), radio_preference=RadioPreference(root / 'BluetoothEnabled'),
                           timer_factory=FakeTimer, admission_lock=root / 'adapter.lock')
    try:
      assert owner.snapshot()['parked'] is False
      owner.request('scan')
      assert owner.scan_deadline > 0
      owner.request('stop_scan')
      owner.request('connect', address='AA:BB:CC:DD:EE:FF')
      assert owner.snapshot()['devices'][0]['connected'] is True
      owner.request('disconnect', address='AA:BB:CC:DD:EE:FF')
      assert owner.snapshot()['devices'][0]['connected'] is False
      with pytest.raises(BluetoothRejected, match='radio restart requires Park'):
        owner.request('power', enabled=False)
      owner.request('forget', address='AA:BB:CC:DD:EE:FF')
      assert owner.snapshot()['devices'] == []
    finally:
      owner.close()
