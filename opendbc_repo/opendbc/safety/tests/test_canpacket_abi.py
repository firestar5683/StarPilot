import gc
import subprocess
import tempfile
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

from opendbc.safety.tests.libsafety import libsafety_py


class TestCanPacketNativeAllocation(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.directory = tempfile.TemporaryDirectory()
    cls.addClassCleanup(cls.directory.cleanup)
    directory = Path(cls.directory.name)
    source = directory / "probe.c"
    source.write_text('''#include <stddef.h>
#include <string.h>
#include "can.h"
size_t packet_size(void) { return sizeof(CANPacket_t); }
size_t packet_alignment(void) { return _Alignof(CANPacket_t); }
size_t packet_data_offset(void) { return offsetof(CANPacket_t, data); }
void packet_copy(const CANPacket_t *src, CANPacket_t *out) { *out = *src; }
void packet_fill(CANPacket_t *out) {
  memset(out, 0x92, sizeof(*out));
  out->addr = 0x123; out->bus = 2; out->data_len_code = 15;
  for (unsigned int i = 0; i < 64; ++i) out->data[i] = (unsigned char)i;
}
''')
    library = directory / "probe.so"
    subprocess.run(["cc", "-shared", "-fPIC", "-std=gnu11", "-O0", "-Wall", "-Wextra", "-Werror",
                    "-I", str(libsafety_py.safety_dir), str(source), "-o", str(library)], check=True)
    cls.ffi = libsafety_py.ffi
    cls.ffi.cdef('''size_t packet_size(void); size_t packet_alignment(void); size_t packet_data_offset(void);
void packet_copy(const CANPacket_t *src, CANPacket_t *out); void packet_fill(CANPacket_t *out);''')
    cls.native = cls.ffi.dlopen(str(library))

  def guarded_packet(self):
    original_new = self.ffi.new
    buffers = []
    native_size = self.native.packet_size()

    def allocate(cdecl, words):
      self.assertEqual(cdecl, "unsigned int[]")
      self.assertEqual(words * self.ffi.sizeof("unsigned int"), native_size)
      storage = original_new(cdecl, words + 4)
      self.ffi.buffer(storage)[native_size:] = b"\xa5" * 16
      buffers.append(storage)
      return storage

    with patch.object(self.ffi, "new", side_effect=allocate):
      packet = libsafety_py.new_CANPacket()
    return packet, buffers[0]

  def test_allocation_matches_native_size_alignment_and_packed_data_offset(self):
    packet, storage = self.guarded_packet()
    self.assertEqual(self.ffi.sizeof(storage) - 16, self.native.packet_size())
    self.assertEqual(libsafety_py.CAN_PACKET_ALIGNMENT, self.native.packet_alignment())
    self.assertEqual(int(self.ffi.cast("uintptr_t", packet)) % self.native.packet_alignment(), 0)
    self.assertEqual(self.ffi.offsetof("CANPacket_t", "data"), self.native.packet_data_offset())

  def test_native_whole_struct_roundtrip_preserves_output_canary_and_payload(self):
    source, source_storage = self.guarded_packet()
    output, output_storage = self.guarded_packet()
    self.native.packet_fill(source)
    self.native.packet_copy(source, output)
    self.assertEqual((output.addr, output.bus, output.data_len_code), (0x123, 2, 15))
    self.assertEqual(bytes(self.ffi.buffer(output.data)), bytes(range(64)))
    size = self.native.packet_size()
    self.assertEqual(bytes(self.ffi.buffer(source_storage)[size:]), b"\xa5" * 16)
    self.assertEqual(bytes(self.ffi.buffer(output_storage)[size:]), b"\xa5" * 16)

  def test_allocator_keeps_backing_storage_until_packet_is_released(self):
    packet, storage = self.guarded_packet()
    reference = weakref.ref(storage)
    del storage
    gc.collect()
    self.assertIsNotNone(reference())
    self.native.packet_fill(packet)
    self.assertEqual(packet.data[63], 63)
    del packet
    gc.collect()
    self.assertIsNone(reference())

  def test_unrounded_packed_allocation_boundary_is_overwritten_by_native_copy(self):
    source = libsafety_py.new_CANPacket()
    self.native.packet_fill(source)
    packed_size = self.ffi.sizeof("CANPacket_t")
    self.assertLess(packed_size, self.native.packet_size())
    # Allocate enough physical storage: the historical logical boundary is the canary.
    storage = self.ffi.new("unsigned int[]", (self.native.packet_size() + 16) // 4)
    self.ffi.buffer(storage)[packed_size:] = b"\xa5" * (self.ffi.sizeof(storage) - packed_size)
    output = self.ffi.cast("CANPacket_t *", storage)
    self.native.packet_copy(source, output)
    self.assertNotEqual(bytes(self.ffi.buffer(storage)[packed_size:self.native.packet_size()]),
                        b"\xa5" * (self.native.packet_size() - packed_size))
    self.assertEqual(bytes(self.ffi.buffer(storage)[self.native.packet_size():]), b"\xa5" * 16)
