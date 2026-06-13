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

  def test_gas_regen_command_matches_opgm_plain_volt_layout(self):
    packer = CANPacker("gm_global_a_powertrain_generated")
    addr, dat, bus = gmcan.create_gas_regen_command(packer, 0, 5000, 1, True, False, use_generated_layout=True)

    assert addr == 0x2CB
    assert bus == 0
    assert dat.hex() == "41435c7000bca38f"
