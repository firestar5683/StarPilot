import struct
import unittest

from tools.laptop_device_build.runtime_paths import runtime_library_path
from tools.laptop_device_build.validate_artifacts import require_aarch64_elf


def linked_elf(runpath: str) -> bytes:
  strings = b"\0" + runpath.encode() + b"\0"
  data = bytearray(256 + len(strings))
  data[:6] = b"\x7fELF\x02\x01"
  struct.pack_into("<HHI", data, 16, 3, 183, 1)
  struct.pack_into("<Q", data, 32, 64)
  struct.pack_into("<HHH", data, 52, 64, 56, 2)
  struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0x1000, 0x1000, len(data), len(data), 4096)
  struct.pack_into("<IIQQQQQQ", data, 120, 2, 4, 192, 0x10c0, 0x10c0, 64, 64, 8)
  for i, entry in enumerate(((5, 0x1100), (10, len(strings)), (29, 1), (0, 0))):
    struct.pack_into("<qQ", data, 192 + 16 * i, *entry)
  data[256:] = strings
  return bytes(data)


class RuntimeLibraryPathsTest(unittest.TestCase):
  def test_cross_build_maps_package_to_target_venv(self):
    source = "/work/.venv-linux-arm64/lib/python3.12/site-packages/ffmpeg/install/lib"
    with self.assertRaisesRegex(ValueError, "build-host runtime search path"):
      require_aarch64_elf(linked_elf(source), "encoderd")
    target = runtime_library_path(source, "/work/.venv-linux-arm64", "/usr/local/venv")
    self.assertEqual(target, "/usr/local/venv/lib/python3.12/site-packages/ffmpeg/install/lib")
    require_aarch64_elf(linked_elf(target), "encoderd")

  def test_local_and_native_build_keep_installed_package_path(self):
    for path in ("/Users/dev/.venv/lib/ffmpeg", "/usr/local/venv/lib/ffmpeg"):
      self.assertEqual(runtime_library_path(path, "/unused"), path)

  def test_cross_build_rejects_package_outside_environment(self):
    for path in ("/elsewhere/lib", "lib/ffmpeg", "/work/../lib"):
      with self.subTest(path=path), self.assertRaises(ValueError):
        runtime_library_path(path, "/work/.venv-linux-arm64", "/usr/local/venv")

  def test_all_runtime_path_entries_checked(self):
    for path in ("/usr/local/lib:/work/dependency/lib", "/opt/tici-sysroot/usr/lib", "/Users/dev/lib"):
      with self.subTest(path=path), self.assertRaisesRegex(ValueError, "build-host runtime search path"):
        require_aarch64_elf(linked_elf(path), "loggerd")

  def test_truncated_dynamic_table_rejected(self):
    data = bytearray(linked_elf("/usr/local/lib"))
    struct.pack_into("<Q", data, 120 + 32, 4096)
    with self.assertRaisesRegex(ValueError, "malformed dynamic table"):
      require_aarch64_elf(data, "loggerd")
