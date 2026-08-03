from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, DBC


class TestGMCan:
  def setup_method(self):
    self.packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_ACC_2022_2023]["pt"])

  def test_gas_regen_command_matches_starpilot_bolt_acc(self):
    addr, dat, bus = gmcan.create_gas_regen_command(self.packer, 0, 5000, 1, True, False)

    assert addr == 0x2CB
    assert bus == 0
    assert dat.hex() == "41429c4000bd63bf"

  def test_gas_regen_command_preserves_always_one3_layout(self):
    _, dat, _ = gmcan.create_gas_regen_command(self.packer, 0, 0, 1, True, False, include_always_one3=True)

    assert dat.hex() == "4142800000bd7fff"

  def test_gas_regen_command_encodes_high_bit_above_8191(self):
    _, dat, _ = gmcan.create_gas_regen_command(self.packer, 0, 8848, 1, True, False)
    decoded = ((dat[1] & 0x1) << 13) | (dat[2] << 5) | ((dat[3] & 0xF8) >> 3)

    assert dat[1] & 0x1
    assert decoded == 8848

  def test_acc_2cd_command_matches_stock_camera_counter_layout(self):
    assert [gmcan.create_acc_2cd_command(0, idx)[1].hex() for idx in range(4)] == [
      "002c03d3fd",
      "402c03d3fc",
      "802c03d3fb",
      "c02c03d3fa",
    ]

  def test_prndl2_command_matches_bolt_gen2_regen_paddle_spoof(self):
    CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)

    addr, dat, bus = gmcan.create_prndl2_command(self.packer, 0, False, CP)
    assert addr == 0x1F5
    assert bus == 0
    assert dat.hex() == "0c0c000600000100"

    addr, dat, bus = gmcan.create_prndl2_command(self.packer, 0, True, CP)
    assert addr == 0x1F5
    assert bus == 0
    assert dat.hex() == "0c0c000500020100"

  def test_prndl2_command_matches_bolt_gen1_regen_paddle_spoof(self):
    CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021)

    addr, dat, bus = gmcan.create_prndl2_command(self.packer, 0, True, CP)

    assert addr == 0x1F5
    assert bus == 0
    assert dat.hex() == "0c0c000700020100"

  def test_regen_paddle_command_matches_bolt_spoof(self):
    addr, dat, bus = gmcan.create_regen_paddle_command(self.packer, 0, False)
    assert addr == 0xBD
    assert bus == 0
    assert dat.hex() == "00000000000000"

    addr, dat, bus = gmcan.create_regen_paddle_command(self.packer, 0, True)
    assert addr == 0xBD
    assert bus == 0
    assert dat.hex() == "20000000000000"

  def test_gas_regen_command_matches_starpilot_volt_2019(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_2019]["pt"])
    addr, dat, bus = gmcan.create_gas_regen_command(packer, 0, 5000, 1, True, False, include_always_one3=True, use_volt_layout=True)

    assert addr == 0x2CB
    assert bus == 0
    assert dat.hex() == "41429c4000bd63bf"

  def test_gas_regen_command_matches_starpilot_volt_ascm(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_ASCM]["pt"])
    addr, dat, bus = gmcan.create_gas_regen_command(packer, 0, 5000, 1, True, False, include_always_one3=True, use_volt_layout=True)

    assert addr == 0x2CB
    assert bus == 0
    assert dat.hex() == "41429c4000bd63bf"
