import unittest

from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum


def reference_checksum(address, data):
  crc = 0
  for byte in (*data[2:], address & 0xFF, (address >> 8) & 0xFF):
    for bit in range(7, -1, -1):
      feedback = (crc >> 15) ^ ((byte >> bit) & 1)
      crc = (crc << 1) & 0xFFFF
      if feedback:
        crc ^= 0x1021
  return crc ^ {8: 0x5F29, 16: 0x041D, 24: 0x819D, 32: 0x9F5B}.get(len(data), 0)


class TestCanfdChecksum(unittest.TestCase):
  def test_matches_bitwise_reference_and_preserves_input(self):
    addresses = (0, 1, 0x1234, 0x7FE, 0x7FF, 0x800, 0x801,
                 0xFFFE, 0xFFFF, 0x10000, 0x10001,
                 0x1FFFFFFE, 0x1FFFFFFF, 0x20000000,
                 -1, -0x10001, (1 << 160) | 0x1234)
    for length in range(65):
      payloads = (bytes(length), b"\xff" * length,
                  bytes((i * 37 + length * 13) & 0xFF for i in range(length)))
      for pattern, payload in enumerate(payloads):
        for address in addresses:
          expected = reference_checksum(address, payload)
          for container in (bytes, bytearray):
            with self.subTest(length=length, pattern=pattern, address=address, container=container.__name__):
              data = container(payload)
              self.assertEqual(hkg_can_fd_checksum(address, None, data), expected)
              self.assertEqual(data, payload)

  def test_first_two_bytes_are_ignored(self):
    for length in range(65):
      payload = bytes((i * 29 + 17) & 0xFF for i in range(length))
      expected = reference_checksum(0x1234, payload)
      for prefix in (b"\x00\x00", b"\xff\xff", b"\x5a\xa5"):
        for container in (bytes, bytearray):
          with self.subTest(length=length, prefix=prefix, container=container.__name__):
            data = container(prefix[:min(2, length)] + payload[2:])
            self.assertEqual(hkg_can_fd_checksum(0x1234, None, data), expected)

  def test_only_low_sixteen_address_bits_are_used(self):
    for length in range(65):
      payload = bytes((i * 19 + 3) & 0xFF for i in range(length))
      for low_address in (0, 0x7FF, 0x800, 0x1234, 0xFFFF):
        expected = reference_checksum(low_address, payload)
        for address in (low_address - (1 << 80), low_address | (1 << 160)):
          for container in (bytes, bytearray):
            with self.subTest(length=length, address=address, container=container.__name__):
              self.assertEqual(hkg_can_fd_checksum(address, None, container(payload)), expected)

  def test_zero_payload_length_adjustments(self):
    for length, expected in ((0, 0), (1, 0), (2, 0), (8, 0x5F29),
                             (16, 0x041D), (24, 0x819D), (32, 0x9F5B), (64, 0)):
      with self.subTest(length=length):
        self.assertEqual(hkg_can_fd_checksum(0, None, bytes(length)), expected)


if __name__ == "__main__":
  unittest.main()
