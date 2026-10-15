import math

from opendbc.car.carlog import carlog
from opendbc.can.dbc import DBC, Signal, SignalType


class CANPacker:
  def __init__(self, dbc_name: str):
    self.dbc = DBC(dbc_name)
    self.counters: dict[int, int] = {}

  def pack(self, address: int, values: dict[str, float]) -> bytearray:
    msg = self.dbc.addr_to_msg.get(address)
    if msg is None:
      carlog.error(f"msg not found for {address=}")
      return bytearray()
    dat = bytearray(msg.size)
    counter_set = False
    for name, value in values.items():
      sig = msg.sigs.get(name)
      if sig is None:
        carlog.error(f"unknown signal {name=} in {msg.name}")
        continue
      ival = int(math.floor((value - sig.offset) / sig.factor + 0.5))
      if ival < 0:
        ival = (1 << sig.size) + ival
      set_value(dat, sig, ival)
      if sig.type == SignalType.COUNTER or sig.name == "COUNTER":
        self.counters[address] = int(value)
        counter_set = True
    sig_counter = next((s for s in msg.sigs.values() if s.type == SignalType.COUNTER or s.name == "COUNTER"), None)
    if sig_counter and not counter_set:
      if address not in self.counters:
        self.counters[address] = 0
      set_value(dat, sig_counter, self.counters[address])
      self.counters[address] = (self.counters[address] + 1) % (1 << sig_counter.size)
    sig_checksum = next((s for s in msg.sigs.values() if s.type > SignalType.COUNTER), None)
    if sig_checksum and sig_checksum.calc_checksum:
      checksum = sig_checksum.calc_checksum(address, sig_checksum, dat)
      set_value(dat, sig_checksum, checksum)
    return dat

  def make_can_msg(self, name_or_addr, bus: int, values: dict[str, float]):
    if isinstance(name_or_addr, int):
      addr = name_or_addr
    else:
      msg = self.dbc.name_to_msg.get(name_or_addr)
      if msg is None:
        carlog.error(f"msg not found for {name_or_addr=}")
        return 0, b'', bus
      addr = msg.address
    dat = self.pack(addr, values)
    if len(dat) == 0:
      return 0, b'', bus
    return addr, bytes(dat), bus


def set_value(msg: bytearray, sig: Signal, ival: int) -> None:
  if type(msg) is bytearray and type(sig) is Signal and type(ival) is int:
    lsb = getattr(sig, 'lsb', None)
    size = getattr(sig, 'size', None)
    little_endian = getattr(sig, 'is_little_endian', None)
    if type(lsb) is int and type(size) is int and type(little_endian) is bool:
      i, shift = lsb // 8, lsb % 8
      if 0 < size <= 8 - shift and 0 <= i < len(msg):
        field_mask = (1 << size) - 1
        mask = field_mask << shift
        msg[i] = (msg[i] & ~mask) | ((ival & field_mask) << shift)
        return

  i = sig.lsb // 8
  bits = sig.size
  if sig.size < 64:
    ival &= (1 << sig.size) - 1
  while 0 <= i < len(msg) and bits > 0:
    shift = sig.lsb % 8 if (sig.lsb // 8) == i else 0
    size = min(bits, 8 - shift)
    mask = ((1 << size) - 1) << shift
    msg[i] &= ~mask
    msg[i] |= (ival & ((1 << size) - 1)) << shift
    bits -= size
    ival >>= size
    i = i + 1 if sig.is_little_endian else i - 1
